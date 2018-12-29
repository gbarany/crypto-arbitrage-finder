import asyncio
import math
import sys

import boto3
import json
import traceback
from typing import Dict, List, Any

import ccxt.async_support as ccxt
from ccxt import InvalidOrder, OrderNotFound
from ccxt.async_support.base.exchange import Exchange

from Exceptions import OrderCreationError, TradesShowstopper, OrderErrorByExchange
from OrderRequest import OrderRequest, OrderRequestStatus, OrderRequestType, OrderRequestList, \
    SegmentedOrderRequestList, CCXT_ORDER_STATUS_OPEN, CCXT_ORDER_STATUS_CANCELED
import time
import logging
from Notifications import sendNotification

logger = logging.getLogger('Trader')


class Trader:
    PHASE_CREATE_TIMEOUT = 5  # sec (Az összes create-nek létre kell jönnie ennyi idő után)
    PHASE_FETCH_TIMEOUT = 10  # sec (Az összes order-nek CLOSED-nak kell lennie ennyi idő után, ha ez nem igaz, akkor ABORT ALL)
    NOF_CCTX_RETRY = 4
    TTL_TRADEORDER_S = 60

    EFFICIENCY = 0.9  # Ezzel szorozzuk a beadott amout-okat, hogy elkerüljük a recegést a soros átváltások miatt

    @staticmethod
    def applyEfficiencyOnAmounts(segmentedOrderRequestList: SegmentedOrderRequestList) -> SegmentedOrderRequestList:
        for orl in segmentedOrderRequestList.getOrderRequestLists():
            for idx, orderRequest in enumerate(orl.getOrderRequests()):
                orderRequest.amount = orderRequest.amount * pow(Trader.EFFICIENCY, idx * 1)
        return segmentedOrderRequestList

    def __init__(self, is_sandbox_mode=True):
        self.__balances: Dict[str, Any] = {}
        self.__is_sandbox_mode: bool = is_sandbox_mode
        self.__exchanges: Dict[str, Exchange] = {}
        self.__isBusy = False
        logger.info(f'Trader.__init__(is_sandbox_mode={is_sandbox_mode})')

    def getBalances(self):
        return self.__balances

    async def initExchangesFromAWSParameterStore(self):
        logger.info(f'initExchangesFromAWSParameterStore')
        with open('./cred/aws-keys.json') as file:
            cred = json.load(file)
            ssm = boto3.client('ssm',
                               aws_access_key_id=cred['aws_access_key_id'],
                               aws_secret_access_key=cred['aws_secret_access_key'],
                               region_name=cred['region_name'])

            def getSSMParam(paramName):
                return ssm.get_parameter(Name=paramName, WithDecryption=True)['Parameter']['Value']

            enabledExchanges = getSSMParam('/prod/enabledExchanges').split(',')

            for exch in enabledExchanges:
                path = f'/prod/exchange/{exch}/'
                pars = ssm.get_parameters_by_path(
                    Path=path,
                    Recursive=True,
                    WithDecryption=True
                )
                exchangeCreds = {}
                for par in pars['Parameters']:
                    key = par['Name'].split('/')[-1]
                    value = par['Value']
                    exchangeCreds[key] = value
                await self.__init_exchange(exch, exchangeCreds)
        await self.fetch_balances()

    async def initExchangesFromCredFile(self, credfile):
        logger.info(f'initExchangesFromCredFile({credfile})')
        with open(credfile) as file:
            exchangeCreds = json.load(file)
            for exchangeName in exchangeCreds:
                await self.__init_exchange(exchangeName, exchangeCreds[exchangeName])
        await self.fetch_balances()

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
        logger.info(f'__cancelOrderRequest #{orderRequest.id} ({orderRequest.toString()})')
        waitingForCreatingStatusRetries = 0
        while orderRequest.getStatus() == OrderRequestStatus.CREATING and waitingForCreatingStatusRetries < 100:
            logger.debug(
                f"Canceling order request (#{orderRequest.id}) is waiting for status CREATING retrycnt={waitingForCreatingStatusRetries}")
            await asyncio.sleep(0.5)
            waitingForCreatingStatusRetries = waitingForCreatingStatusRetries + 1
        if orderRequest.id is None:
            logger.error(f"Canceling order request (#{orderRequest.id}) is not possible  id=None, state={orderRequest.getStatus().value}")
            return
        t1 = time.time()
        if orderRequest.id is not None:
            for retrycntr in range(Trader.NOF_CCTX_RETRY):
                try:
                    response = await self.__exchanges[
                        orderRequest.exchange_name_std].cancelOrder(orderRequest.id, orderRequest.market)
                    logger.debug(f'cancelOrder response={response}')
                    if 'error' in response:
                        raise ValueError('Error in exchange response:' +
                                         str(response['error']))
                    logger.info(f'Cancelled oder #{orderRequest.id} ({orderRequest})')
                    orderRequest.setCanceled()
                    exchange = self.__exchanges[orderRequest.exchange_name_std]
                    await asyncio.sleep(exchange.rateLimit / 1000)
                    return
                except OrderNotFound as onf:
                    logger.error(f'Cancel order request (#{orderRequest.id}) failed with OrderNotFound ({onf})')
                    break
                except Exception as e:
                    logger.debug(f'Cancel order request (#{orderRequest.id}) failed  with {e}, retrycntr={retrycntr}')
                    await asyncio.sleep(self.__exchanges[orderRequest.exchange_name_std].rateLimit / 1000)
        dt = (time.time() - t1) * 1000
        logger.info(f'Cancel order request (#{orderRequest.id}) ended in {dt} ms ({orderRequest.toString()})')

    async def cancelAllOrderRequests(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        tasks = []
        for orderRequest in segmentedOrderRequestList.getOrderRequests():
            if orderRequest.isPending() is True:
                tasks.append(
                    asyncio.ensure_future(self.__cancelOrderRequest(orderRequest)))
        await asyncio.gather(*tasks)
        logger.info("Cancellation of all order requests completed")

    async def abortSegmentedOrderRequestList(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        logger.debug(f'abortSegmentedOrderRequestList')
        try:
            await self.cancelAllOrderRequests(segmentedOrderRequestList)
        except Exception as e:
            logger.error(f'abortSegmentedOrderRequestList failed: {e}')

    async def __fetch_order_status(self, orderRequest: OrderRequest):
        logger.info(f'__fetch_order_status #{orderRequest.id} ({orderRequest.toString()})')
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                t1 = time.time()
                response = await self.__exchanges[orderRequest.exchange_name_std].fetchOrder(orderRequest.id)
                logger.debug(f'__fetch_order_status #{orderRequest.id} response: {response}')
                t2 = time.time()
                d = (t2 - t1) * 1000.0
                logger.info(f'Order status fetched #{orderRequest.id} from {orderRequest.exchange_name} in {d} ms')
                orderRequest.setOrder(response)
                if response['status'] == CCXT_ORDER_STATUS_CANCELED:
                    logger.info(f'Order status CANCELED #{orderRequest.id}')
                    raise OrderErrorByExchange(orderRequest)

                exchange = self.__exchanges[orderRequest.exchange_name_std]
                await asyncio.sleep(exchange.rateLimit / 1000)

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

    async def __fetch_order_status_until_closed_or_timeout(self, orderRequest: OrderRequest):
        retrycntr = 0
        while orderRequest.isPending() and retrycntr <= Trader.NOF_CCTX_RETRY:
            await self.__fetch_order_status(orderRequest)
            await asyncio.sleep(self.__exchanges[orderRequest.exchange_name_std].rateLimit / 1000)

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
                self.__balances[exchange.name.lower().replace(
                    " ", "")] = balance
                d_ms = (time.time() - t1) * 1000.0
                logger.info('Balance fetching completed from ' +
                            exchange.name + f" in {d_ms} ms")
                await asyncio.sleep(exchange.rateLimit / 1000)  # wait for rateLimit
                return
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                d_ms = (time.time() - t1) * 1000.0
                logger.error('Fetch balance failed from ' + exchange.name +
                             " " + type(error).__name__ + " " +
                             str(error.args) + " retrycntr:" + str(retrycntr) + f" in {d_ms} ms")
                await asyncio.sleep(exchange.rateLimit / 1000)
        logger.error(f'Error during fetch balance for {exchange}.')
        raise ValueError(f'Error during fetch balance for {exchange}.')

    async def fetch_balances(self):
        self.__balances = {}
        tasks = []
        for _, exchange in self.__exchanges.items():
            tasks.append(asyncio.ensure_future(self.fetch_balance(exchange)))
        await asyncio.gather(*tasks)

    def get_free_balance(self, exchangeName, symbol) -> float:
        try:
            return float(self.__balances[exchangeName][symbol]["free"])
        except Exception as e:
            # logger.warning()
            raise ValueError(
                f"No balance available from {exchangeName} {symbol} {self.__balances[exchangeName][symbol]['free']}")

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
        return market['limits']['amount']['min']

    def hasSufficientBalance(self, exchange_name: str, market_str: str, amount: float, type: OrderRequestType):
        try:
            exchange = self.get_exchange(exchange_name)
            market = self.get_market(exchange_name, market_str)
            if market['limits']['amount']['min']:
                if amount < exchange.markets[market_str]['limits']['amount']['min']:
                    raise ValueError(
                        'Amount too small, won'
                        't execute on ' + exchange.name + " " + market_str +
                        " Amount: " + str(amount) + " Min.amount:" +
                        str(exchange.markets[market_str]['limits']['amount']['min'])
                    )

            if market['limits']['amount']['max']:
                if amount > exchange.markets[market_str]['limits']['amount']['max']:
                    raise ValueError(
                        'Amount too big, won'
                        't execute on ' + exchange.name + " " + market_str +
                        " Amount: " + str(amount) + " Max.amount:" +
                        str(exchange.markets[market_str]['limits']['amount']['max'])
                    )

            if type == OrderRequestType.SELL:
                free_balance = self.get_free_balance(exchange_name, market_str.split('/')[0])
            else:
                free_balance = self.get_free_balance(exchange_name, market_str.split('/')[1])
            if free_balance < amount:
                raise ValueError(
                    'Insufficient stock on ' + exchange.name + " " + market_str +
                    " Amount available: " +
                    str(free_balance) +
                    " Amount required:" + str(amount))

            return True
        except Exception as e:
            raise ValueError(f"Error during transaction validation: {e}")

    def isOrderRequestValid(self, orderRequest: OrderRequest):
        exchange_name = orderRequest.exchange_name_std
        market_str = orderRequest.market
        amount = orderRequest.amount
        type = orderRequest.type
        try:
            exchange = self.get_exchange(exchange_name)
            market = self.get_market(exchange_name, market_str)
            if market['limits']['amount']['min']:
                if amount < exchange.markets[market_str]['limits']['amount']['min']:
                    raise ValueError(
                        'Amount too small, won'
                        't execute on ' + exchange.name + " " + market_str +
                        " Amount: " + str(amount) + " Min.amount:" +
                        str(exchange.markets[market_str]['limits']['amount']['min'])
                    )

            if market['limits']['amount']['max']:
                if amount > exchange.markets[market_str]['limits']['amount']['max']:
                    raise ValueError(
                        'Amount too big, won'
                        't execute on ' + exchange.name + " " + market_str +
                        " Amount: " + str(amount) + " Max.amount:" +
                        str(exchange.markets[market_str]['limits']['amount']['max'])
                    )

            return True
        except Exception as e:
            raise ValueError(f"Error during validating OrderRequest: {e}")

    def hasSufficientBalanceForOrderRequest(self, orderRequest: OrderRequest):
        exchange_name = orderRequest.exchange_name_std
        market_str = orderRequest.market
        amount = orderRequest.amount
        if orderRequest.type == OrderRequestType.SELL:
            free_balance = self.get_free_balance(exchange_name, market_str.split('/')[0])
        else:
            free_balance = self.get_free_balance(exchange_name, market_str.split('/')[1])
        if free_balance < amount:
            raise ValueError(
                f'Insufficient stock on {orderRequest.exchange_name_std} {orderRequest.market}.' +
                f' Amount available: {free_balance}' +
                f' Amount required: {amount}')

        return True

    def isOrderRequestListValid(self, orderRequestList: OrderRequestList):
        for orderRequest in orderRequestList.getOrderRequests():
            if self.isOrderRequestValid(orderRequest) is False:
                return False
        ors = orderRequestList.getOrderRequests()
        return self.hasSufficientBalanceForOrderRequest(ors[0])

    def isSegmentedOrderRequestListValid(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        ret: bool = True
        for orderRequestList in segmentedOrderRequestList.getOrderRequestLists():
            ret = ret & self.isOrderRequestListValid(orderRequestList)
        return ret

    async def __create_limit_order(self, orderRequest: OrderRequest):
        logger.info(f"__create_limit_order ({orderRequest.toString()})")
        if orderRequest.shouldAbort:
            logger.info(f"Create limit order is canceled, reason: shouldAbort is True ({orderRequest.toString()})")
            return
        exchange = self.__exchanges[orderRequest.exchange_name_std]
        symbol = orderRequest.market
        amount = orderRequest.amount
        price = orderRequest.price
        t1 = time.time()
        try:
            if self.__is_sandbox_mode is True:
                raise ValueError('Trader sandbox mode ON')

            if orderRequest.type == OrderRequestType.BUY:
                orderRequest.setStatus(OrderRequestStatus.CREATING)
                response = await exchange.createLimitBuyOrder(symbol, exchange.amountToPrecision(symbol, amount), exchange.priceToPrecision(symbol, price))
                logger.debug(f"{orderRequest.exchange_name_std}.createLimitBuyOrder ({orderRequest.toString()}) response: {response}")
            elif orderRequest.type == OrderRequestType.SELL:
                orderRequest.setStatus(OrderRequestStatus.CREATING)
                response = await exchange.createLimitSellOrder(symbol, exchange.amountToPrecision(symbol, amount), exchange.priceToPrecision(symbol, price))
                logger.debug(f"{orderRequest.exchange_name_std}.createLimitSellOrder ({orderRequest.toString()}) response: {response}")
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
            d_ms = (time.time() - t1) * 1000.0
            logger.info(f"Create limit order SUCCESS ({orderRequest.toString()}) in {d_ms} ms")

            await asyncio.sleep(exchange.rateLimit / 1000)

        except Exception as error:
            d_ms = (time.time() - t1) * 1000.0
            logger.error(f"Create limit order FAILED ({orderRequest.toString()}) in {d_ms} ms. Reason: {error}")
            orderRequest.setStatus(OrderRequestStatus.FAILED)
            raise error

    async def createLimitOrdersOnOrderRequestList(self, orderRequestList: OrderRequestList):
        '''
        Creates limit order and waits for the order status
        :param orderRequestList:
        :return:
        '''
        try:
            # Pre-check transactions
            if self.isOrderRequestListValid(orderRequestList) is False:
                logger.error(f'OrderRequestList is not valid: {orderRequestList} ')
                raise ValueError(f'OrderRequestList is not valid: {orderRequestList} ')

            # Fire real transactions
            for orderRequest in orderRequestList.getOrderRequests():
                if orderRequest.shouldAbort is False:
                    await self.__create_limit_order(orderRequest)
                    if orderRequest.shouldAbort is True:
                        await self.__cancelOrderRequest(orderRequest)
                    else:
                        await self.__fetch_order_status(orderRequest)

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
                    f"segmentedOrderRequestList is not valid: {segmentedOrderRequestList} ")

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
        if self.__isBusy:
            logger.info(f"Trader is busy, the execute() call is droped")
            return
        self.__isBusy = True

        try:
            logger.info(f'Start execute the orders:')
            logger.info(f'\n{segmentedOrderRequestList.sorlToString()}\n')
            isValid = self.isSegmentedOrderRequestListValid(segmentedOrderRequestList)
            logger.info(f'Validating result: {isValid}')

            if isValid is False:
                self.__isBusy = False
                return

            if self.__is_sandbox_mode:
                logger.info('Trader is in sandbox mode. Skiping the order requests.')
                self.__isBusy = False
                return

        except Exception as e:
            logger.error(f"execute failed during pre validation. Reason: {e}")
            self.__isBusy = False
            return

        # ret = self.input('Write <ok> to authorize the trade:')
        # if ret != "ok":
        #     logger.info(f'Trader is not authorized to execute the trade.')
        #     return
        # else:
        #     logger.info('Trader is authorized.')

        try:
            sendNotification("CryptoArb Trader is placing orders. Check the logs for details.")
            t1 = time.time()
            await self.createLimitOrdersOnSegmentedOrderRequestList(segmentedOrderRequestList)
            d_ms = time.time() - t1
            logger.debug(f"createLimitOrdersOnSegmentedOrderRequestList ended in {d_ms} ms")
            logger.info(f"Waiting for the order requests to complete for {Trader.TTL_TRADEORDER_S} s ")
            await asyncio.sleep(Trader.TTL_TRADEORDER_S)
            logger.info(f"Waiting for TTL_TRADEORDER_S is over. ({Trader.TTL_TRADEORDER_S} s) ")
            await self.fetch_order_statuses(segmentedOrderRequestList)
            logger.info(f"Canceling all requests")
            await self.cancelAllOrderRequests(segmentedOrderRequestList)
        except Exception as e:
            d_ms = time.time() - t1
            logger.error(f"execute failed in {d_ms} ms. Reason: {e}")
            for orderRequest in segmentedOrderRequestList.getOrderRequests():
                orderRequest.shouldAbort = True
            await self.abortSegmentedOrderRequestList(segmentedOrderRequestList)
        finally:
            logger.info('SORL after execution:')
            logger.info(f'\n{segmentedOrderRequestList.sorlToString()}\n')
            logger.info('History log after execution:')
            logger.info(f'\n{segmentedOrderRequestList.statusLogToString()}\n')
            await self.fetch_balances()
            self.__isBusy = False
            logger.info('Exit after execute()')
            sys.exit("Exit after execute()")

    def isSandboxMode(self):
        return self.__is_sandbox_mode

    def input(self, str):
        return input(str)
