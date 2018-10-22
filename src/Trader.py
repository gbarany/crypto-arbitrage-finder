import asyncio
import json
import traceback
from typing import Dict, List, Any

import ccxt.async_support as ccxt
from ccxt import InvalidOrder, OrderNotFound
from ccxt.async_support.base.exchange import Exchange

from Exceptions import OrderCreationError, TradesShowstopper, OrderErrorByExchange
from InitLogger import logger
from OrderRequest import OrderRequest, OrderRequestStatus, OrderRequestType, OrderRequestList, \
    SegmentedOrderRequestList, CCXT_ORDER_STATUS_OPEN, CCXT_ORDER_STATUS_CANCELED
import time


class Trader:
    PHASE_CREATE_TIMEOUT = 5  # sec (Az összes create-nek létre kell jönnie ennyi idő után)
    PHASE_FETCH_TIMEOUT = 10  # sec (Az összes order-nek CLOSED-nak kell lennie ennyi idő után, ha ez nem igaz, akkor ABORT ALL)
    NOF_CCTX_RETRY = 4
    TTL_TRADEORDER_S = 2

    def __init__(self,
                 credfile='./cred/api.json',
                 is_sandbox_mode=True):
        self.__credfile: str = credfile
        self.__balance: Dict[str, Any] = {}
        self.__is_sandbox_mode: bool = is_sandbox_mode
        self.__exchanges: Dict[str, Exchange] = {}

    async def initExchanges(self):
        with open(self.__credfile) as file:
            exchangeCreds = json.load(file)
            for exchangeName in exchangeCreds:
                await self.__init_exchange(exchangeName, exchangeCreds[exchangeName])

    async def __init_exchange(self, exchangeName: str, exchangeCreds):
        exchange = getattr(ccxt, exchangeName)(exchangeCreds)
        await exchange.load_markets()
        self.__exchanges[exchangeName.lower().replace(" ", "")] = exchange

    async def __close_exchange(self, exchange):
        await exchange.close()

    async def close_exchanges(self):
        tasks = []
        for _, exchange in self.__exchanges.items():
            tasks.append(asyncio.ensure_future(
                self.__close_exchange(exchange)))
        await asyncio.gather(*tasks)
        logger.info("Exchanges closed")

    async def __cancelOrderRequest(self, orderRequest: OrderRequest):
        logger.debug(f'Cancel order request ({orderRequest.as_string()})')
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                response = await self.__exchanges[
                    orderRequest.exchange_name_std].cancelOrder(orderRequest.id, orderRequest.market)
                logger.debug(f'cancelOrder response={response}')
                if response['error']:
                    raise ValueError('Error in exchange response:' +
                                     str(response['error']))
                logger.info('Cancelled oder ' + orderRequest.id + ' on ' +
                            orderRequest.exchange_name_std)
                orderRequest.setCanceled()
                return
            except OrderNotFound as onf:
                logger.error('OrderRequest cancellation failed with OrderNotFound for ' +
                             str(orderRequest.id) + " " + orderRequest.market + " " +
                             orderRequest.exchange_name + " " + str(onf.args))
                return
            except Exception as e:
                logger.error(f'OrderRequest cancellation failed for {orderRequest} with {e}, retrycntr={retrycntr}')
                await asyncio.sleep(
                    self.__exchanges[orderRequest.exchange_name_std].rateLimit / 1000)

    # async def cancelOpenOrderRequests(self, segmentedOrderRequestList: SegmentedOrderRequestList):
    #     tasks = []
    #     for orderRequest in segmentedOrderRequestList.getOrderRequests():
    #         if orderRequest.getStatus() == OrderRequestStatus.OPEN:
    #             tasks.append(
    #                 asyncio.ensure_future(self.__cancelOrderRequest(orderRequest)))
    #     await asyncio.gather(*tasks)
    #     logger.info("Cancellation of open order requests completed")

    async def cancelAllOrderRequests(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        tasks = []
        for orderRequest in segmentedOrderRequestList.getOrderRequests():
            if orderRequest.isAlive() is True:
                tasks.append(
                    asyncio.ensure_future(self.__cancelOrderRequest(orderRequest)))
        await asyncio.gather(*tasks)
        logger.info("Cancellation of all order requests completed")

    async def abortSegmentedOrderRequestList(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        try:
            await self.cancelAllOrderRequests(segmentedOrderRequestList)
        except Exception as e:
            logger.error(f'abortSegmentedOrderRequestList failed: {e}')

    async def __fetch_order_status(self, orderRequest: OrderRequest):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                t1 = time.time()
                response = await self.__exchanges[
                    orderRequest.exchange_name_std].fetchOrder(orderRequest.id)
                t2 = time.time()
                d = (t2 - t1) * 1000.0
                logger.info(
                    f'Order status fetched {orderRequest.id} from {orderRequest.exchange_name} in {d} ms')
                orderRequest.setOrder(response)
                if response['status'] == CCXT_ORDER_STATUS_CANCELED:
                    raise OrderErrorByExchange(orderRequest)
                return

            except OrderErrorByExchange as e:
                raise e
            except InvalidOrder as e:
                logger.error(
                    f'Order status fetching failed for {orderRequest.id}  {orderRequest.market} {orderRequest.exchange_name} {e.args} retrycntr: {retrycntr}')
                raise OrderErrorByExchange(orderRequest)
            except Exception as e:
                logger.error(f'Order status fetching failed for {orderRequest} with reason {e} retrycntr={retrycntr}')
                await asyncio.sleep(
                    self.__exchanges[orderRequest.exchange_name_std].rateLimit / 1000)

    async def fetch_order_statuses(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        tasks = []
        try:
            for orderRequest in segmentedOrderRequestList.getOrderRequests():
                tasks.append(asyncio.ensure_future(
                    self.__fetch_order_status(orderRequest)))
            await asyncio.gather(*tasks)
            logger.info("Order statuses fetching completed")
        except OrderErrorByExchange as e:
            logger.error(f"Order canceled by exchange: {e}")
            raise e

    async def fetch_balance(self, exchange):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            t1 = time.time()
            try:
                balance = await exchange.fetch_balance()
                self.__balance[exchange.name.lower().replace(
                    " ", "")] = balance
                d_ms = (time.time() - t1) * 1000.0
                logger.info('Balance fetching completed from ' +
                            exchange.name + f" in {d_ms} ms")
                return
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                d_ms = (time.time() - t1) * 1000.0
                logger.error('Fetch balance failed from ' + exchange.name +
                             " " + type(error).__name__ + " " +
                             str(error.args) + " retrycntr:" + str(retrycntr) + f" in {d_ms} ms")
                await asyncio.sleep(exchange.rateLimit / 1000)

    async def fetch_balances(self):
        self.__balance = {}
        tasks = []
        for _, exchange in self.__exchanges.items():
            tasks.append(asyncio.ensure_future(self.fetch_balance(exchange)))
        await asyncio.gather(*tasks)

    def get_free_balance(self, exchangeName, symbol) -> float:
        try:
            return float(self.__balance[exchangeName][symbol]["free"])
        except Exception as e:
            # logger.warning()
            raise ValueError(
                f"No balance available from {exchangeName} {symbol} {self.__balance[exchangeName][symbol]['free']}")

    def get_exchange(self, exchange_name: str) -> Exchange:
        if exchange_name not in self.__exchanges:
            raise ValueError(
                f'Exchange ({exchange_name}) does not exists in initialized exchanges'
            )
        return self.__exchanges[exchange_name]

    def get_market(self, exchange_name: str,
                   market_str: str) -> Dict[str, Any]:
        exchange = self.get_exchange(exchange_name)
        if market_str not in exchange.markets:
            raise ValueError(
                f'Symbol ({market_str}) does not exists in exchange ({exchange_name})'
            )
        return exchange.markets[market_str]

    def get_min_trade_amount(self, exchange_name: str, market_str: str):
        market = self.get_market(exchange_name, market_str)
        return market['limits']['price']['min']

    def is_transaction_valid(self, exchange_name: str, market_str: str,
                             amount: float):
        exchange = self.get_exchange(exchange_name)
        market = self.get_market(exchange_name, market_str)
        if market['limits']['price']['min']:
            if amount < exchange.markets[market_str]['limits']['price']['min']:
                raise ValueError(
                    'Amount too small, won'
                    't execute on ' + exchange.name + " " + market_str +
                    " Amount: " + str(amount) + " Min.amount:" +
                    str(exchange.markets[market_str]['limits']['price']['min'])
                )

        if market['limits']['price']['max']:
            if amount > exchange.markets[market_str]['limits']['price']['max']:
                raise ValueError(
                    'Amount too big, won'
                    't execute on ' + exchange.name + " " + market_str +
                    " Amount: " + str(amount) + " Max.amount:" +
                    str(exchange.markets[market_str]['limits']['price']['max'])
                )

        if self.get_free_balance(exchange_name,
                                 market_str.split('/')[0]) < amount:
            raise ValueError(
                'Insufficient stock on ' + exchange.name + " " + market_str +
                " Amount available: " +
                str(self.get_free_balance(exchange_name, market_str)) +
                " Amount required:" + str(amount))

        return True

    def isOrderRequestValid(self, orderRequest: OrderRequest):
        return self.is_transaction_valid(orderRequest.exchange_name_std, orderRequest.market,
                                         orderRequest.amount)

    def isOrderRequestListValid(self, orderRequestList: OrderRequestList):
        ret: bool = True
        for orderRequest in orderRequestList.getOrderRequests():
            ret = ret & self.isOrderRequestValid(orderRequest)
        return ret

    def isSegmentedOrderRequestListValid(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        ret: bool = True
        for orderRequest in segmentedOrderRequestList.getOrderRequests():
            ret = ret & self.isOrderRequestValid(orderRequest)
        return ret

    async def __create_limit_order(self, orderRequest: OrderRequest):
        logger.debug(f"create_limit_order({orderRequest.as_string()})")
        response = {}
        exchange = self.__exchanges[orderRequest.exchange_name_std]
        symbol = orderRequest.market
        amount = orderRequest.amount
        price = orderRequest.price
        t1 = time.time()
        try:
            if self.__is_sandbox_mode is True:
                raise ValueError('trader sandbox mode ON')

            if orderRequest.type == OrderRequestType.BUY:
                orderRequest.setStatus(OrderRequestStatus.CREATING)
                response = await exchange.createLimitBuyOrder(symbol, amount, price)
                logger.debug(f"createLimitBuyOrder response: {response}")
                d_ms = (time.time() - t1) * 1000.0
                logger.info(
                    f"{orderRequest.exchange_name_std}.createLimitBuyOrder {symbol} Amount: {amount} Price: {price} ID: {response['id']}  created successfully in {d_ms} ms")
            elif orderRequest.type == OrderRequestType.SELL:
                orderRequest.setStatus(OrderRequestStatus.CREATING)
                response = await exchange.createLimitSellOrder(symbol, amount, price)
                logger.debug(f"createLimitSellOrder response: {response}")
                d_ms = (time.time() - t1) * 1000.0
                logger.info(
                    f"{orderRequest.exchange_name_std}.createLimitSellOrder {symbol} Amount: {amount} Price: {price} ID: {response['id']}  created successfully in {d_ms} ms")
            else:
                raise ValueError('orderRequest.type has an invalid value')

            if 'id' not in response:
                raise OrderCreationError("Order creation failed: id is not present" +
                                         exchange.name + " " + symbol)
            orderRequest.id = response['id']
            orderRequest.setStatus(OrderRequestStatus.CREATED)
            if 'info' in response:
                if 'error' in response['info']:
                    orderRequest.errorlog = response['info']['error']

            if 'info' in response:
                if 'error' in response['info']:
                    if response['info']['error']:
                        raise ValueError('Error in exchange response:' +
                                         str(response['error']))

        except Exception as error:
            logger.error('create_limit_order failed from ' + exchange.name +
                         " " + symbol + ": " + type(error).__name__ + " " +
                         str(error.args))
            raise error

    async def createLimitOrdersOnOrderRequestList(self, orderRequestList: OrderRequestList):
        orders = []
        try:
            # Pre-check transactions
            if self.isOrderRequestListValid(orderRequestList) is False:
                raise ValueError(f'TradeList {orderRequestList} is not initialized')

            # Fire real transactions
            for orderRequest in orderRequestList.getOrderRequests():
                await self.__create_limit_order(orderRequest)

        except Exception as e:
            logger.error(f"OrderRequestList cannot be created: {e}")
            # traceback.print_exc()
            raise TradesShowstopper("TradeList showstopper")

    async def createLimitOrdersOnSegmentedOrderRequestList(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        orders = []
        try:
            # Pre-check transactions
            if self.isSegmentedOrderRequestListValid(segmentedOrderRequestList) is False:
                raise ValueError(
                    f"segmentedOrderRequestList {segmentedOrderRequestList} is not initalized")

            # Fire real transactions
            for orderRequestList in segmentedOrderRequestList.getOrderRequestLists():
                orders.append(
                    asyncio.ensure_future(self.createLimitOrdersOnOrderRequestList(orderRequestList)))

            await asyncio.gather(*orders)

        except ValueError as ve:
            logger.error("Arbitrage deal cannot be executed, " + str(ve.args))
            traceback.print_exc()
            raise TradesShowstopper("Trade showstopper")

    async def execute(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        t1 = time.time()
        try:
            await self.fetch_balances()

            await self.createLimitOrdersOnSegmentedOrderRequestList(segmentedOrderRequestList)
            d_ms = time.time() - t1
            logger.info(
                f"create_limit_orders_on_segmentedOrderRequestList run in {d_ms} ms")
            logger.info("Waiting for the order requests to complete for " +
                        str(Trader.TTL_TRADEORDER_S) + "s")
            await asyncio.sleep(Trader.TTL_TRADEORDER_S)
            await self.fetch_order_statuses(segmentedOrderRequestList)
            await self.cancelAllOrderRequests(segmentedOrderRequestList)
        except Exception as e:
            d_ms = time.time() - t1
            logger.info(
                f"execute failed in {d_ms} ms")
            logger.error(f"Trade stopped: {e}")
            await self.abortSegmentedOrderRequestList(segmentedOrderRequestList)
