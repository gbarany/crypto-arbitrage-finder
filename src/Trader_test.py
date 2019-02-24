import asyncio
import unittest

import pytest
from asynctest import CoroutineMock, patch, TestCase, Mock, logging
from ccxt import InsufficientFunds
from Trader import Trader
from OrderRequest import OrderRequest, OrderRequestStatus, OrderRequestType, OrderRequestList, \
    SegmentedOrderRequestList, CCXT_ORDER_STATUS_CANCELED, CCXT_ORDER_STATUS_CLOSED, CCXT_ORDER_STATUS_OPEN

POLONIEX = 'poloniex'
BINANCE = 'binance'
KRAKEN = 'kraken'
ETH_EUR = 'ETH/EUR'
ETH_BTC = 'ETH/BTC'
BTC_USD = 'ETH/BTC'

logging.getLogger('Trader').setLevel(logging.DEBUG)
rootLogger = logging.getLogger()
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]')
ch.setFormatter(formatter)
# add the handlers to the logger
rootLogger.addHandler(ch)


class TestClass(TestCase):

    def __mockExchange(self, exchange, exchangeName):
        to_be_mocked = exchange.return_value

        async def mockBalance():
            await asyncio.sleep(0.2)
            return {
                'USD': {'free': 50, 'used': 50, 'total': 100},
                'EUR': {'free': 50, 'used': 50, 'total': 100},
                'ETH': {'free': 50, 'used': 50, 'total': 100},
            }

        async def mockFunc0():
            await asyncio.sleep(0.2)
            return {'error': 'MOCKED ERROR'}

        async def mockFunc2(x, y):
            await asyncio.sleep(0.2)
            return {'error': 'MOCKED ERROR'}

        def mockAmountToPrecision(symbol, amount):
            return amount

        to_be_mocked.amountToPrecision = mockAmountToPrecision
        to_be_mocked.fetch_balance = CoroutineMock(side_effect=mockBalance)
        to_be_mocked.fetchOrder = CoroutineMock(side_effect=mockFunc0)
        to_be_mocked.createLimitSellOrder = CoroutineMock(side_effect=mockFunc0)
        to_be_mocked.createLimitBuyOrder = CoroutineMock(side_effect=mockFunc0)
        to_be_mocked.cancelOrder = CoroutineMock(side_effect=mockFunc2)
        to_be_mocked.load_markets = CoroutineMock(side_effect=mockFunc0)
        to_be_mocked.close = CoroutineMock(side_effect=mockFunc0)
        to_be_mocked.name = exchangeName
        to_be_mocked.rateLimit = 7
        to_be_mocked.markets = {
            ETH_EUR: {
                'limits': {
                    'amount': {'min': 0.02, 'max': 100000000.0},
                    'price': {'min': 0.01, 'max': None},
                    'cost': {'min': 0.1, 'max': None}
                }
                , 'id': ETH_EUR, 'symbol': 'ETH/EUR'
            },
            ETH_BTC: {
                'limits': {
                    'amount': {'min': 0.02, 'max': 100000000.0},
                    'price': {'min': 0.01, 'max': None},
                    'cost': {'min': 0.1, 'max': None}
                }
                , 'id': ETH_BTC, 'symbol': 'ETH/BTC'
            },
            BTC_USD: {
                'limits': {
                    'amount': {'min': 0.02, 'max': 100000000.0},
                    'price': {'min': 0.01, 'max': None},
                    'cost': {'min': 0.1, 'max': None}
                }
                , 'id': BTC_USD, 'symbol': 'BTC/USD'
            }
        }

    def __SORL_3(self):
        or_11 = OrderRequest(BINANCE, ETH_EUR, volumeBase=11, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or_12 = OrderRequest(BINANCE, ETH_EUR, volumeBase=12, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)
        or_13 = OrderRequest(BINANCE, ETH_EUR, volumeBase=13, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or_21 = OrderRequest(KRAKEN, ETH_EUR, volumeBase=21, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or_22 = OrderRequest(KRAKEN, ETH_EUR, volumeBase=22, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)
        or_23 = OrderRequest(KRAKEN, ETH_EUR, volumeBase=23, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or_31 = OrderRequest(POLONIEX, ETH_EUR, volumeBase=31, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or_32 = OrderRequest(POLONIEX, ETH_EUR, volumeBase=32, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)
        or_33 = OrderRequest(POLONIEX, ETH_EUR, volumeBase=33, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)

        orl_1 = OrderRequestList([or_11, or_12, or_13])
        orl_2 = OrderRequestList([or_21, or_22, or_23])
        orl_3 = OrderRequestList([or_31, or_32, or_33])
        sorl = SegmentedOrderRequestList('uuid', [orl_1, orl_2, orl_3])
        return sorl

    def __SORL_1(self, EXCHANGE):
        or_1 = OrderRequest(EXCHANGE, ETH_EUR, volumeBase=1, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or_2 = OrderRequest(EXCHANGE, ETH_EUR, volumeBase=2, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)
        or_3 = OrderRequest(EXCHANGE, ETH_EUR, volumeBase=3, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        orl_1 = OrderRequestList([or_1, or_2, or_3])
        sorl = SegmentedOrderRequestList('uuid', [orl_1])
        return sorl

    async def setUp(self):
        self.binance = patch('ccxt.async_support.binance').start()
        self.__mockExchange(self.binance, BINANCE)

        self.kraken = patch('ccxt.async_support.kraken').start()
        self.__mockExchange(self.kraken, KRAKEN)

        self.poloniex = patch('ccxt.async_support.poloniex').start()
        self.__mockExchange(self.poloniex, POLONIEX)

        self.trader = Trader(is_sandbox_mode=False)
        await self.trader.initExchangesFromCredFile(credfile='./cred/api_test.json')
        self.trader.input = lambda x: 'ok'
        Trader.TTL_TRADEORDER_S = 1

    async def tearDown(self):

        await self.trader.close_exchanges()
        self.kraken = None
        self.binance = None

    async def test_happy_path_1_order(self):
        exchangeMock = self.binance.return_value
        EXCHANGE = BINANCE

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=[{'id': '0'}])
        exchangeMock.fetchOrder = CoroutineMock(side_effect=[{'status': CCXT_ORDER_STATUS_CLOSED}])

        or_1 = OrderRequest(EXCHANGE, ETH_EUR, volumeBase=1, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)

        orl_1 = OrderRequestList([or_1])
        sorl = SegmentedOrderRequestList('uuid', [orl_1])
        await self.trader.execute(sorl)

        assert exchangeMock.createLimitSellOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 1
        assert exchangeMock.cancelOrder.await_count == 0
        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CLOSED

    async def test_balances_validation(self):
        sorl = self.__SORL_3()
        ors: [OrderRequest] = sorl.getOrderRequests()
        ors[0].type = OrderRequestType.SELL
        ors[1].volumeBase = 1000
        assert self.trader.isSegmentedOrderRequestListValid(sorl)
        ors[3].volumeBase = 1000
        with pytest.raises(ValueError):
            assert self.trader.isSegmentedOrderRequestListValid(sorl)
        ors[3].volumeBase = 10
        ors[4].volumeBase = 0
        with pytest.raises(ValueError):
            assert self.trader.isSegmentedOrderRequestListValid(sorl)
        ors[4].volumeBase = 10000000010
        with pytest.raises(ValueError):
            assert self.trader.isSegmentedOrderRequestListValid(sorl)



    async def test_creating_same_exchange_first_failed(self):
        """
            1 exchange, the first order request failed during creation
        """
        goid = 0  # Global Order ID: mocked unique order id
        exchangeMock = self.binance.return_value
        EXCHANGE = BINANCE

        async def mockCreateLimitSellOrder(symbol, amount, price):
            raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)

        sorl = self.__SORL_1(EXCHANGE)
        assert sorl.getOrderRequests()[0].volumeBase == 1
        assert sorl.getOrderRequests()[1].volumeBase == 2
        assert sorl.getOrderRequests()[2].volumeBase == 3

        await self.trader.execute(sorl)

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.FAILED
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.INITIAL
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

        assert exchangeMock.createLimitSellOrder.await_count == 0
        assert exchangeMock.createLimitBuyOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 0
        assert exchangeMock.cancelOrder.await_count == 0

    async def test_creating_same_exchange_second_failed(self):
        """
           1 exchange, the second order request failed during creation
        """
        goid = 0  # Global Order ID: mocked unique order id
        exchangeMock = self.binance.return_value
        EXCHANGE = BINANCE

        async def mockCreateLimitSellOrder(symbol, amount, price):
            raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            return {'id': amount}

        async def mockFetchOrder(id):
            return {'status': CCXT_ORDER_STATUS_OPEN}

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMock.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMock.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)

        sorl = self.__SORL_1(EXCHANGE)
        assert sorl.getOrderRequests()[0].volumeBase == 1
        assert sorl.getOrderRequests()[1].volumeBase == 2
        assert sorl.getOrderRequests()[2].volumeBase == 3

        await self.trader.execute(sorl)

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.FAILED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

        assert exchangeMock.createLimitSellOrder.await_count == 1
        assert exchangeMock.createLimitBuyOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 1
        assert exchangeMock.cancelOrder.await_count == Trader.NOF_CCTX_RETRY

    async def test_canceled_same_exchange_second_canceled(self):
        """
           1 exchange, the second order canceled by the exchange, should cancel all orders
        """
        goid = 0  # Global Order ID: mocked unique order id
        exchangeMock = self.binance.return_value
        EXCHANGE = BINANCE

        async def mockCreateLimitSellOrder(symbol, amount, price):
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            return {'id': amount}

        async def mockFetchOrder(id):
            if id == 2:
                return {'status': CCXT_ORDER_STATUS_CANCELED}
            else:
                return {'status': CCXT_ORDER_STATUS_OPEN}

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMock.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMock.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)

        sorl = self.__SORL_1(EXCHANGE)
        assert sorl.getOrderRequests()[0].volumeBase == 1
        assert sorl.getOrderRequests()[1].volumeBase == 2
        assert sorl.getOrderRequests()[2].volumeBase == 3

        await self.trader.execute(sorl)

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

        assert exchangeMock.createLimitSellOrder.await_count == 1
        assert exchangeMock.createLimitBuyOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 2
        assert exchangeMock.cancelOrder.await_count == Trader.NOF_CCTX_RETRY

    async def test_canceled_more_exchanges_middle_failed(self):
        """
           3 exchanges, the 5. order canceled by the exchange, should cancel all orders
        """

        exchangeMockBinance = self.binance.return_value
        exchangeMockKraken = self.kraken.return_value
        exchangeMockPloniex = self.poloniex.return_value

        async def mockCreateLimitSellOrder(symbol, amount, price):
            if amount == 22:
                raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            if amount == 22:
                raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")
            return {'id': amount}

        async def mockFetchOrder(id):
            return {'status': CCXT_ORDER_STATUS_CLOSED}

        async def mockCancelOrder(id, exc):
            # await asyncio.sleep(0.1)
            return {'id': id, 'status': CCXT_ORDER_STATUS_CANCELED}

        exchangeMockBinance.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockBinance.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockBinance.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockBinance.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)
        exchangeMockKraken.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockKraken.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockKraken.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockKraken.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)
        exchangeMockPloniex.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockPloniex.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockPloniex.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockPloniex.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)

        sorl = self.__SORL_3()
        assert sorl.getOrderRequests()[0].volumeBase == 11
        assert sorl.getOrderRequests()[3].volumeBase == 21
        assert sorl.getOrderRequests()[6].volumeBase == 31

        await self.trader.execute(sorl)

        print(sorl.logStatusLogs())
        # A tesztet úgy kell vizsgálni, hogy fixáljuk le az execute() eredményét, mert az függ a futási
        # logikától és a mock-ban használt sleep timeoktól

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CLOSED
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

        assert sorl.getOrderRequests()[3].getStatus() == OrderRequestStatus.CLOSED
        assert sorl.getOrderRequests()[4].getStatus() == OrderRequestStatus.FAILED  # Ez döglik meg
        assert sorl.getOrderRequests()[5].getStatus() == OrderRequestStatus.INITIAL

        assert sorl.getOrderRequests()[6].getStatus() == OrderRequestStatus.CLOSED
        # assert sorl.getOrderRequests()[7].getStatus() == OrderRequestStatus.CANCELED Nem determinisztikus az értéke
        assert sorl.getOrderRequests()[8].getStatus() == OrderRequestStatus.INITIAL

        # A fenti lefixált állapotokhoz tartozó hívások count-ja

        assert exchangeMockBinance.createLimitBuyOrder.await_count == 1
        assert exchangeMockBinance.createLimitSellOrder.await_count == 1
        assert exchangeMockBinance.fetchOrder.await_count == 1
        assert exchangeMockBinance.cancelOrder.await_count == 2  # Trader.NOF_CCTX_RETRY * 3

        assert exchangeMockKraken.createLimitSellOrder.await_count == 1
        assert exchangeMockKraken.createLimitBuyOrder.await_count == 1
        assert exchangeMockKraken.fetchOrder.await_count == 1
        assert exchangeMockKraken.cancelOrder.await_count == 0  # Trader.NOF_CCTX_RETRY * 2

        # assert exchangeMockPloniex.createLimitSellOrder.await_count == 1 Nem determinisztikus az értéke
        # assert exchangeMockPloniex.createLimitBuyOrder.await_count == 1 Nem determinisztikus az értéke
        assert exchangeMockPloniex.fetchOrder.await_count == 1
        assert exchangeMockPloniex.cancelOrder.await_count == 0

    async def test_canceled_more_exchanges_middle_canceled(self):
        """
           3 exchanges, the 5. order canceled by the exchange, should cancel all orders
        """

        exchangeMockBinance = self.binance.return_value
        exchangeMockKraken = self.kraken.return_value
        exchangeMockPloniex = self.poloniex.return_value

        async def mockCreateLimitSellOrder(symbol, amount, price):
            await asyncio.sleep(0.1)
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            await asyncio.sleep(0.1)
            return {'id': amount}

        async def mockFetchOrder(id):
            await asyncio.sleep(0.01)
            if id == 22:
                return {'status': CCXT_ORDER_STATUS_CANCELED}
            else:
                return {'status': CCXT_ORDER_STATUS_OPEN}

        async def mockCancelOrder(id, exc):
            await asyncio.sleep(0.1)
            return {'id': id, 'status': CCXT_ORDER_STATUS_CANCELED}

        exchangeMockBinance.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockBinance.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockBinance.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockBinance.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)
        exchangeMockKraken.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockKraken.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockKraken.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockKraken.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)
        exchangeMockPloniex.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockPloniex.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockPloniex.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockPloniex.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)

        # for exchangeMock in [exchangeMockPloniex, exchangeMockKraken, exchangeMockBinance]:
        #     exchangeMock.cancelOrder = CoroutineMock(return_value={'error': 'MOCKED ERROR'})

        sorl = self.__SORL_3()
        assert sorl.getOrderRequests()[0].volumeBase == 11
        assert sorl.getOrderRequests()[3].volumeBase == 21
        assert sorl.getOrderRequests()[6].volumeBase == 31

        await self.trader.execute(sorl)

        # A tesztet úgy kell vizsgálni, hogy fixáljuk le az execute() eredményét, mert az függ a futási
        # logikától és a mock-ban használt sleep timeoktól

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

        assert sorl.getOrderRequests()[3].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[4].getStatus() == OrderRequestStatus.CANCELED  # Ez döglik meg MAJD
        assert sorl.getOrderRequests()[5].getStatus() == OrderRequestStatus.INITIAL

        assert sorl.getOrderRequests()[6].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[7].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[8].getStatus() == OrderRequestStatus.INITIAL

        # A fenti lefixált állapotokhoz tartozó hívások count-ja

        assert exchangeMockBinance.createLimitSellOrder.await_count == 1
        assert exchangeMockBinance.createLimitBuyOrder.await_count == 1
        assert exchangeMockBinance.fetchOrder.await_count == 2
        assert exchangeMockBinance.cancelOrder.await_count == 2
        assert exchangeMockKraken.createLimitSellOrder.await_count == 1
        assert exchangeMockKraken.createLimitBuyOrder.await_count == 1
        assert exchangeMockKraken.fetchOrder.await_count == 2
        assert exchangeMockKraken.cancelOrder.await_count == 1
        assert exchangeMockPloniex.createLimitSellOrder.await_count == 1
        assert exchangeMockPloniex.createLimitBuyOrder.await_count == 1
        assert exchangeMockPloniex.fetchOrder.await_count == 2
        assert exchangeMockPloniex.cancelOrder.await_count == 2

        print(sorl.logStatusLogs())

    async def test_more_exchanges_with_bigtimeout_failed(self):
        """
           2 exchanges:
            1. exchanges: 2 orders, the first SUCCESS, the 2. failed on short time
            2. exchange: 1 order, the creation (SUCCESS) of this order is very slow, way more the other 2 orders

        """

        exchangeMockBinance = self.binance.return_value
        exchangeMockKraken = self.kraken.return_value
        exchangeMockPloniex = self.poloniex.return_value

        async def mockCreateLimitSellOrder(symbol, amount, price):
            await asyncio.sleep(0.1)
            if amount == 12:
                raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            await asyncio.sleep(1)
            return {'id': amount}

        async def mockFetchOrder(id):
            await asyncio.sleep(0.1)
            if id in [11, 12, 21]:
                return {'status': CCXT_ORDER_STATUS_CLOSED}

        async def mockCancelOrder(id, exc):
            await asyncio.sleep(0.1)
            return {'id': id, 'status': CCXT_ORDER_STATUS_CANCELED}

        exchangeMockBinance.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockBinance.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockBinance.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)
        exchangeMockKraken.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockKraken.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockKraken.cancelOrder = CoroutineMock(side_effect=mockCancelOrder)

        # to be SUCCESS
        or11 = OrderRequest(BINANCE, ETH_EUR, volumeBase=11, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)
        # to be FAILED
        or12 = OrderRequest(BINANCE, ETH_EUR, volumeBase=12, limitPrice=1, meanPrice=1, requestType=OrderRequestType.SELL)
        # to be SUCCESS but very slow
        or21 = OrderRequest(KRAKEN, ETH_EUR, volumeBase=21, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)
        or22 = OrderRequest(KRAKEN, ETH_EUR, volumeBase=22, limitPrice=1, meanPrice=1, requestType=OrderRequestType.BUY)

        sorl = SegmentedOrderRequestList('uuid', [
            OrderRequestList([or11, or12]),
            OrderRequestList([or21, or22])
        ])
        assert sorl.getOrderRequests()[0].volumeBase == 11
        assert sorl.getOrderRequests()[1].volumeBase == 12
        assert sorl.getOrderRequests()[2].volumeBase == 21

        await self.trader.execute(sorl)

        # A tesztet úgy kell vizsgálni, hogy fixáljuk le az execute() eredményét, mert az függ a futási
        # logikától és a mock-ban használt sleep timeoktól

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CLOSED
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.FAILED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[3].getStatus() == OrderRequestStatus.INITIAL

        # # A fenti lefixált állapotokhoz tartozó hívások count-ja

        assert exchangeMockBinance.createLimitBuyOrder.await_count == 0
        assert exchangeMockBinance.createLimitSellOrder.await_count == 2
        assert exchangeMockBinance.fetchOrder.await_count == 1
        assert exchangeMockBinance.cancelOrder.await_count == 0

        assert exchangeMockKraken.createLimitSellOrder.await_count == 0
        assert exchangeMockKraken.createLimitBuyOrder.await_count == 1
        assert exchangeMockKraken.fetchOrder.await_count == 0
        assert exchangeMockKraken.cancelOrder.await_count == 2
