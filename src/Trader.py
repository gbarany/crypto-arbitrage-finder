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

from Exceptions import OrderCreationError, OrderErrorByExchange
from OrderRequest import OrderRequest, OrderRequestStatus, OrderRequestType, OrderRequestList, \
    SegmentedOrderRequestList, CCXT_ORDER_STATUS_OPEN, CCXT_ORDER_STATUS_CANCELED
import time
import logging
from Notifications import sendNotification
from TraderHistory import TraderHistory
from Database import Database

logger = logging.getLogger('Trader')


class Trader:
    PHASE_CREATE_TIMEOUT = 5  # sec (Az összes create-nek létre kell jönnie ennyi idő után)
    PHASE_FETCH_TIMEOUT = 10  # sec (Az összes order-nek CLOSED-nak kell lennie ennyi idő után, ha ez nem igaz, akkor ABORT ALL)
    NOF_CCTX_RETRY = 4
    TTL_TRADEORDER_S = 60 * 5
    FETCH_ORDER_STATUS_TIMEOUT = 60 * 5

    # EFFICIENCY = 0.9  # Ezzel szorozzuk a beadott amout-okat, hogy elkerüljük a recegést a soros átváltások miatt
    #
    # @staticmethod
    # def applyEfficiencyOnAmounts(segmentedOrderRequestList: SegmentedOrderRequestList) -> SegmentedOrderRequestList:
    #     for orl in segmentedOrderRequestList.getOrderRequestLists():
    #         for idx, orderRequest in enumerate(orl.getOrderRequests()):
    #             orderRequest.amount = orderRequest.amount * pow(Trader.EFFICIENCY, idx * 1)
    #     return segmentedOrderRequestList

    def __init__(self, is_sandbox_mode=True):
        self.__balances: Dict[str, Any] = {}
        self.__is_sandbox_mode: bool = is_sandbox_mode
        self.__exchanges: Dict[str, Exchange] = {}
        self.__isBusy = False
        logger.debug(f'Trader.__init__(is_sandbox_mode={is_sandbox_mode})')

    def getBalances(self):
        return self.__balances

    def getFreeBalances(self):
        free = {}
        for name in self.__balances:
            exchange = self.__balances[name]
            try:
                for symbol in exchange['free']:
                    if exchange['free'][symbol] > 0.00001:
                        if name not in free:
                            free[name] = {}
                        free[name][symbol] = exchange['free'][symbol]
            except Exception as e:
                logger.error(e)
        return free

    @staticmethod
    def storeFreeBalances(uuid, timing, balances):
        db = Database.initDBFromAWSParameterStore()

        for exchange in balances:

            for symbol in balances[exchange]:

                query = "INSERT INTO `balance`" \
                        "(uuid, timing, exchange, symbol, balance)" \
                        "VALUES(%s,%s,%s,%s,%s)"
                args = (
                    uuid,
                    timing,
                    exchange,
                    symbol,
                    balances[exchange][symbol]
                )

                try:

                    cursor = db.cursor()
                    cursor.execute(query, args)

                    if cursor.lastrowid:
                        if cursor.lastrowid % 100 == 0:
                            print('last insert id', cursor.lastrowid)

                    db.commit()
                except Exception as e:
                    print(e)

        db.close()

    async def initExchangesFromAWSParameterStore(self):
        logger.debug(f'initExchangesFromAWSParameterStore')
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
        logger.debug(f'Free balances: \n{self.getFreeBalances()}')
        Trader.storeFreeBalances(None, None, self.getFreeBalances())

    async def initExchangesFromCredFile(self, credfile):
        logger.debug(f'initExchangesFromCredFile({credfile})')
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
        logger.debug("Exchanges closed")

    async def __cancelOrderRequest(self, orderRequest: OrderRequest):
        logger.debug(f'__cancelOrderRequest #{orderRequest.id} ({orderRequest.toString()})')
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
                    logger.debug(f'Cancelled oder #{orderRequest.id} ({orderRequest})')
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
        logger.debug(f'Cancel order request (#{orderRequest.id}) ended in {dt} ms ({orderRequest.toString()})')

    async def cancelAllOrderRequests(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        tasks = []
        for orderRequest in segmentedOrderRequestList.getOrderRequests():
            if orderRequest.isPending() is True:
                tasks.append(
                    asyncio.ensure_future(self.__cancelOrderRequest(orderRequest)))
        await asyncio.gather(*tasks)
        logger.debug("Cancellation of all order requests completed")

    async def abortSegmentedOrderRequestList(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        logger.debug(f'abortSegmentedOrderRequestList')
        try:
            await self.cancelAllOrderRequests(segmentedOrderRequestList)
        except Exception as e:
            logger.error(f'abortSegmentedOrderRequestList failed: {e}')

    async def __fetch_order_status(self, orderRequest: OrderRequest):
        logger.debug(f'__fetch_order_status #{orderRequest.id} ({orderRequest.toString()})')
        try:
            t1 = time.time()
            response = await self.__exchanges[orderRequest.exchange_name_std].fetchOrder(orderRequest.id)
            logger.debug(f'__fetch_order_status #{orderRequest.id} response: {response}')
            t2 = time.time()
            d = (t2 - t1) * 1000.0
            logger.debug(f'Order status fetched #{orderRequest.id} from {orderRequest.exchange_name} in {d} ms')
            orderRequest.updateOrderStatusFromCCXT(response)
            if response['status'] == CCXT_ORDER_STATUS_CANCELED:
                logger.debug(f'Order status CANCELED #{orderRequest.id}')
                raise OrderErrorByExchange(orderRequest)

            exchange = self.__exchanges[orderRequest.exchange_name_std]
            await asyncio.sleep(exchange.rateLimit / 1000)

            return

        except OrderErrorByExchange as e:
            raise e
        except InvalidOrder as e:
            logger.error(
                f'Order status fetching failed for {orderRequest.id}  {orderRequest.market} {orderRequest.exchange_name} {e.args}')
            raise OrderErrorByExchange(orderRequest)
        except Exception as e:
            logger.error(f'Order status fetching failed for {orderRequest} with reason {e}')
            await asyncio.sleep(
                self.__exchanges[orderRequest.exchange_name_std].rateLimit / 1000)

    async def __fetch_order_status_until_closed_or_timeout(self, orderRequest: OrderRequest):
        t_start = time.time()
        while (orderRequest.getStatus() != OrderRequestStatus.CLOSED) and (time.time() < t_start + Trader.FETCH_ORDER_STATUS_TIMEOUT):
            await self.__fetch_order_status(orderRequest)
            await asyncio.sleep(self.__exchanges[orderRequest.exchange_name_std].rateLimit / 1000)

    async def fetch_order_statuses(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        tasks = []
        try:
            for orderRequest in segmentedOrderRequestList.getOrderRequests():
                tasks.append(asyncio.ensure_future(
                    self.__fetch_order_status(orderRequest)))
            await asyncio.gather(*tasks)
            logger.debug("Order statuses fetching completed")
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
                logger.debug('Balance fetching completed from ' +
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

    def is_exchange_available(self, exchange_name: str) -> bool:
        return exchange_name in self.__exchanges

    def get_exchange(self, exchange_name: str) -> Exchange:
        if not self.is_exchange_available(exchange_name):
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

    def isOrderRequestValid(self, orderRequest: OrderRequest) -> bool:
        exchange_name = orderRequest.exchange_name_std
        market_str = orderRequest.market
        amount = orderRequest.volumeBase
        type = orderRequest.type
        try:
            if not self.is_exchange_available(exchange_name):
                raise ValueError(f'Exchange is not available: {exchange_name}')
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
        logger.debug(f'hasSufficientBalanceForOrderRequest({orderRequest})')
        exchange_name = orderRequest.exchange_name_std
        market_str = orderRequest.market
        volumeBase = orderRequest.volumeBase
        if orderRequest.type == OrderRequestType.SELL:
            base_symbol = market_str.split('/')[0]
            free_balance_base = self.get_free_balance(exchange_name, base_symbol)
            logger.debug(f'base_symbol={base_symbol}, free_balance_base={free_balance_base}, volumeBase={volumeBase}')
            if free_balance_base < volumeBase:
                raise ValueError(
                    f'Insufficient fund on {exchange_name} {orderRequest.market}.' +
                    f' free_balance_base: {free_balance_base}' +
                    f' volumeBase: {volumeBase}' +
                    f' type: {orderRequest.type}')
            else:
                logger.debug(f'Has sufficient fund on {orderRequest.exchange_name_std} {orderRequest.market}: balance={free_balance_base} needed={volumeBase}')
                return True

        elif orderRequest.type == OrderRequestType.BUY:
            quote_symbol = market_str.split('/')[1]
            free_balance_quote = self.get_free_balance(exchange_name, quote_symbol)
            logger.debug(f'quote_symbol={quote_symbol}, free_balance_quote={free_balance_quote}, volumeBase={volumeBase}, orderRequest.meanPrice={orderRequest.meanPrice}')
            needed_quote = volumeBase * orderRequest.meanPrice
            if free_balance_quote < needed_quote:
                raise ValueError(
                    f'Insufficient fund on {orderRequest.exchange_name_std} {orderRequest.market}.' +
                    f' free_balance_quote: {free_balance_quote}' +
                    f' volumeBase * orderRequest.meanPrice: {volumeBase * orderRequest.meanPrice}' +
                    f' type: {orderRequest.type}')
            else:
                logger.debug(f'Has sufficient fund on {orderRequest.exchange_name_std} {orderRequest.market}: balance={free_balance_quote} needed={needed_quote}')
                return True
        else:
            raise ValueError('Invalid orderRequest.type')

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
        logger.debug(f"__create_limit_order ({orderRequest.toString()})")
        if orderRequest.shouldAbort:
            logger.debug(f"Create limit order is canceled, reason: shouldAbort is True ({orderRequest.toString()})")
            return
        exchange = self.__exchanges[orderRequest.exchange_name_std]
        symbol = orderRequest.market
        amount = orderRequest.volumeBase
        price = orderRequest.limitPrice
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
            logger.debug(f"Create limit order SUCCESS ({orderRequest.toString()}) in {d_ms} ms")

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
                        await self.__fetch_order_status_until_closed_or_timeout(orderRequest)
                        if orderRequest.getStatus() != OrderRequestStatus.CLOSED:
                            raise ValueError(f'OrderRequestStatus is not CLOSED after timeout: {orderRequest.toString()}')

        except Exception as e:
            logger.error(f"OrderRequestList cannot be created: {e}")
            # traceback.print_exc()
            raise e

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
            raise ve

    def isSandboxMode(self):
        return self.__is_sandbox_mode

    def input(self, str):
        return input(str)

    def sendNotification(self, str_text):
        sendNotification(str_text)

    async def pollTrades(self):
        ''' TraderHistory-n keresztül menti a trade-ket '''
        traderHistory = await TraderHistory.getInstance()
        await traderHistory.pollTrades()
        await traderHistory.close()

    async def execute(self, segmentedOrderRequestList: SegmentedOrderRequestList):
        if self.__isBusy:
            # logger.debug(f"Trader is busy, the execute() call is droped")
            return
        self.__isBusy = True

        try:
            logger.debug(f'Start execute the orders:')
            logger.debug(f'\n{segmentedOrderRequestList.sorlToString()}\n')
            logger.debug(f'Free balances: \n{self.getFreeBalances()}')
            isValid = self.isSegmentedOrderRequestListValid(segmentedOrderRequestList)
            logger.debug(f'Validating result: {isValid}')

            if isValid is False:
                self.__isBusy = False
                return

            if self.__is_sandbox_mode:
                logger.debug('Trader is in sandbox mode. Skiping the order requests.')
                self.__isBusy = False
                return

        except ValueError as e:
            logger.error(f"execute failed during pre validation. Reason: {e}")
            self.__isBusy = False
            return
        except Exception as e:
            logger.error(f"execute failed during pre validation. Reason: {e}", exc_info=True)
            self.__isBusy = False
            return

        # ret = self.input('Write <ok> to authorize the trade:')
        # if ret != "ok":
        #     logger.debug(f'Trader is not authorized to execute the trade.')
        #     return
        # else:
        #     logger.debug('Trader is authorized.')

        try:
            # TODO: save SORL into db
            self.sendNotification(f"CryptoArb Trader is placing orders, uuid: {segmentedOrderRequestList.uuid}")
            t1 = time.time()
            Trader.storeFreeBalances(segmentedOrderRequestList.uuid, -1, self.getFreeBalances())
            await self.createLimitOrdersOnSegmentedOrderRequestList(segmentedOrderRequestList)
            d_ms = time.time() - t1
            logger.debug(f"createLimitOrdersOnSegmentedOrderRequestList ended in {d_ms} ms")
            logger.debug(f"Waiting for the order requests to complete for {Trader.TTL_TRADEORDER_S} s ")
            await asyncio.sleep(Trader.TTL_TRADEORDER_S)
            logger.debug(f"Waiting for TTL_TRADEORDER_S is over. ({Trader.TTL_TRADEORDER_S} s) ")
            await self.fetch_order_statuses(segmentedOrderRequestList)
            logger.debug(f"Canceling all requests")
            await self.cancelAllOrderRequests(segmentedOrderRequestList)
        except Exception as e:
            d_s = time.time() - t1
            logger.error(f"execute failed in {d_s} ms. Reason: {e}")
            for orderRequest in segmentedOrderRequestList.getOrderRequests():
                orderRequest.shouldAbort = True
            await self.abortSegmentedOrderRequestList(segmentedOrderRequestList)
            self.sendNotification(f"CryptoArb Trader failed. Reason: " + f"{e}"[:100])
        finally:
            logger.debug('SORL after execution:')
            logger.debug(f'\n{segmentedOrderRequestList.sorlToString()}\n')
            logger.debug('History log after execution:')
            logger.debug(f'\n{segmentedOrderRequestList.statusLogToString()}\n')
            await self.fetch_balances()
            logger.debug(f'Free Balances: {self.getFreeBalances()}')
            Trader.storeFreeBalances(segmentedOrderRequestList.uuid, 1, self.getFreeBalances())
            # Fetch trades into db
            await self.pollTrades()

            # TODO: fetch FIAT into db
            # TODO: fetchBalance into db
            self.__isBusy = False
            logger.debug('execute(): end.')
            # sys.exit("Exit after execute()")
