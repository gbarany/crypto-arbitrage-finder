import asyncio
import unittest
from asynctest import CoroutineMock, patch, TestCase, Mock
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


class TestClass(TestCase):

    def __mockExchange(self, exchange, exchangeName):
        to_be_mocked = exchange.return_value
        mockBalance = {
            'USD': {'free': 50, 'used': 50, 'total': 100},
            'EUR': {'free': 50, 'used': 50, 'total': 100},
            'ETH': {'free': 50, 'used': 50, 'total': 100},
        }
        to_be_mocked.fetch_balance = CoroutineMock(return_value=mockBalance)
        to_be_mocked.fetchOrder = CoroutineMock(return_value={'error': 'MOCKED ERROR'})
        to_be_mocked.createLimitSellOrder = CoroutineMock(return_value={'error': 'MOCKED ERROR'})
        to_be_mocked.createLimitBuyOrder = CoroutineMock(return_value={'error': 'MOCKED ERROR'})
        to_be_mocked.cancelOrder = CoroutineMock(return_value={'error': 'MOCKED ERROR'})
        to_be_mocked.load_markets = CoroutineMock()
        to_be_mocked.close = CoroutineMock()
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
        or_11 = OrderRequest(BINANCE, ETH_EUR, amount=11, price=1, requestType=OrderRequestType.BUY)
        or_12 = OrderRequest(BINANCE, ETH_EUR, amount=12, price=1, requestType=OrderRequestType.SELL)
        or_13 = OrderRequest(BINANCE, ETH_EUR, amount=13, price=1, requestType=OrderRequestType.BUY)
        or_21 = OrderRequest(KRAKEN, ETH_EUR, amount=21, price=1, requestType=OrderRequestType.BUY)
        or_22 = OrderRequest(KRAKEN, ETH_EUR, amount=22, price=1, requestType=OrderRequestType.SELL)
        or_23 = OrderRequest(KRAKEN, ETH_EUR, amount=23, price=1, requestType=OrderRequestType.BUY)
        or_31 = OrderRequest(POLONIEX, ETH_EUR, amount=31, price=1, requestType=OrderRequestType.BUY)
        or_32 = OrderRequest(POLONIEX, ETH_EUR, amount=32, price=1, requestType=OrderRequestType.SELL)
        or_33 = OrderRequest(POLONIEX, ETH_EUR, amount=33, price=1, requestType=OrderRequestType.BUY)

        orl_1 = OrderRequestList([or_11, or_12, or_13])
        orl_2 = OrderRequestList([or_21, or_22, or_23])
        orl_3 = OrderRequestList([or_31, or_32, or_33])
        sorl = SegmentedOrderRequestList([orl_1, orl_2, orl_3])
        return sorl

    def __SORL_1(self, EXCHANGE):
        or_1 = OrderRequest(EXCHANGE, ETH_EUR, amount=1, price=1, requestType=OrderRequestType.BUY)
        or_2 = OrderRequest(EXCHANGE, ETH_EUR, amount=2, price=1, requestType=OrderRequestType.SELL)
        or_3 = OrderRequest(EXCHANGE, ETH_EUR, amount=3, price=1, requestType=OrderRequestType.BUY)
        orl_1 = OrderRequestList([or_1, or_2, or_3])
        sorl = SegmentedOrderRequestList([orl_1])
        return sorl

    async def setUp(self):
        self.binance = patch('ccxt.async_support.binance').start()
        self.__mockExchange(self.binance, BINANCE)

        self.kraken = patch('ccxt.async_support.kraken').start()
        self.__mockExchange(self.kraken, KRAKEN)

        self.poloniex = patch('ccxt.async_support.poloniex').start()
        self.__mockExchange(self.poloniex, POLONIEX)

        self.trader = Trader(credfile='./cred/aoi_test.json', is_sandbox_mode=False)
        await self.trader.initExchanges()

    async def tearDown(self):

        await self.trader.close_exchanges()
        self.kraken = None
        self.binance = None

    async def test_happy_path_1_order(self):
        exchangeMock = self.binance.return_value
        EXCHANGE = BINANCE

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=[{'id': '0'}])
        exchangeMock.fetchOrder = CoroutineMock(side_effect=[{'status': CCXT_ORDER_STATUS_CLOSED}])

        or_1 = OrderRequest(EXCHANGE, ETH_EUR, amount=1, price=1, requestType=OrderRequestType.SELL)

        orl_1 = OrderRequestList([or_1])
        sorl = SegmentedOrderRequestList([orl_1])
        await self.trader.execute(sorl)

        assert exchangeMock.createLimitSellOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 1
        assert exchangeMock.cancelOrder.await_count == 0
        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CLOSED

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
        assert sorl.getOrderRequests()[0].amount == 1
        assert sorl.getOrderRequests()[1].amount == 2
        assert sorl.getOrderRequests()[2].amount == 3

        await self.trader.execute(sorl)

        assert exchangeMock.createLimitSellOrder.await_count == 0
        assert exchangeMock.createLimitBuyOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 0
        assert exchangeMock.cancelOrder.await_count == Trader.NOF_CCTX_RETRY
        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CREATING
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.INITIAL
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

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

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMock.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)

        sorl = self.__SORL_1(EXCHANGE)
        assert sorl.getOrderRequests()[0].amount == 1
        assert sorl.getOrderRequests()[1].amount == 2
        assert sorl.getOrderRequests()[2].amount == 3

        await self.trader.execute(sorl)

        assert exchangeMock.createLimitSellOrder.await_count == 1
        assert exchangeMock.createLimitBuyOrder.await_count == 1
        assert exchangeMock.fetchOrder.await_count == 0
        assert exchangeMock.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 2
        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CREATED
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.CREATING
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.INITIAL

    async def test_canceled_same_exchange_second_canceled(self):
        """
           1 exchange, the second order canceled by the exchange, should cancel all orders
        """
        goid = 0  # Global Order ID: mocked unique order id
        exchangeMock = self.binance.return_value
        EXCHANGE = BINANCE

        async def mockCreateLimitSellOrder(symbol, amount, price):
            await asyncio.sleep(1)
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            await asyncio.sleep(1)
            return {'id': amount}

        async def mockFetchOrder(id):
            await asyncio.sleep(1)
            if id == 2:
                return {'status': CCXT_ORDER_STATUS_CANCELED}
            else:
                return {'status': CCXT_ORDER_STATUS_OPEN}

        exchangeMock.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMock.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMock.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)

        sorl = self.__SORL_1(EXCHANGE)
        assert sorl.getOrderRequests()[0].amount == 1
        assert sorl.getOrderRequests()[1].amount == 2
        assert sorl.getOrderRequests()[2].amount == 3

        await self.trader.execute(sorl)

        assert exchangeMock.createLimitSellOrder.await_count == 1
        assert exchangeMock.createLimitBuyOrder.await_count == 2
        assert exchangeMock.fetchOrder.await_count == 3
        assert exchangeMock.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 3
        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.CANCELED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.OPEN

    async def test_canceled_more_exchanges_middle_failed(self):
        """
           3 exchanges, the 5. order canceled by the exchange, should cancel all orders
        """

        exchangeMockBinance = self.binance.return_value
        exchangeMockKraken = self.kraken.return_value
        exchangeMockPloniex = self.poloniex.return_value

        async def mockCreateLimitSellOrder(symbol, amount, price):
            await asyncio.sleep(1)
            if amount == 22:
                raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            await asyncio.sleep(1)
            if amount == 22:
                raise InsufficientFunds("NO FUNDS ON MOCKED EXCHANGE")
            return {'id': amount}

        async def mockFetchOrder(id):
            return {'status': CCXT_ORDER_STATUS_CLOSED}

        exchangeMockBinance.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockBinance.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockBinance.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockKraken.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockKraken.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockKraken.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockPloniex.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockPloniex.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockPloniex.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)

        sorl = self.__SORL_3()
        assert sorl.getOrderRequests()[0].amount == 11
        assert sorl.getOrderRequests()[3].amount == 21
        assert sorl.getOrderRequests()[6].amount == 31

        await self.trader.execute(sorl)

        # A tesztet úgy kell vizsgálni, hogy fixáljuk le az execute() eredményét, mert az függ a futási
        # logikától és a mock-ban használt sleep timeoktól

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.CREATED
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.CREATED
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.CREATING

        assert sorl.getOrderRequests()[3].getStatus() == OrderRequestStatus.CREATED
        assert sorl.getOrderRequests()[4].getStatus() == OrderRequestStatus.CREATING # Ez döglik meg
        assert sorl.getOrderRequests()[5].getStatus() == OrderRequestStatus.INITIAL

        assert sorl.getOrderRequests()[6].getStatus() == OrderRequestStatus.CREATED
        assert sorl.getOrderRequests()[7].getStatus() == OrderRequestStatus.CREATED
        assert sorl.getOrderRequests()[8].getStatus() == OrderRequestStatus.CREATING

        # A fenti lefixált állapotokhoz tartozó hívások count-ja

        assert exchangeMockBinance.createLimitBuyOrder.await_count == 1
        assert exchangeMockBinance.createLimitSellOrder.await_count == 1
        assert exchangeMockBinance.fetchOrder.await_count == 0
        assert exchangeMockBinance.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 3

        assert exchangeMockKraken.createLimitSellOrder.await_count == 1
        assert exchangeMockKraken.createLimitBuyOrder.await_count == 1
        assert exchangeMockKraken.fetchOrder.await_count == 0
        assert exchangeMockKraken.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 2

        assert exchangeMockPloniex.createLimitSellOrder.await_count == 1
        assert exchangeMockPloniex.createLimitBuyOrder.await_count == 1
        assert exchangeMockPloniex.fetchOrder.await_count == 0
        assert exchangeMockPloniex.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 2


    async def test_canceled_more_exchanges_middle_canceled(self):
        """
           3 exchanges, the 5. order canceled by the exchange, should cancel all orders
        """

        exchangeMockBinance = self.binance.return_value
        exchangeMockKraken = self.kraken.return_value
        exchangeMockPloniex = self.poloniex.return_value

        async def mockCreateLimitSellOrder(symbol, amount, price):
            await asyncio.sleep(1)
            return {'id': amount}

        async def mockCreateLimitBuyOrder(symbol, amount, price):
            await asyncio.sleep(1)
            return {'id': amount}

        async def mockFetchOrder(id):
            await asyncio.sleep(1)
            if id == 22:
                return {'status': CCXT_ORDER_STATUS_CANCELED}
            else:
                return {'status': CCXT_ORDER_STATUS_OPEN}

        exchangeMockBinance.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockBinance.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockBinance.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockKraken.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockKraken.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockKraken.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)
        exchangeMockPloniex.createLimitSellOrder = CoroutineMock(side_effect=mockCreateLimitSellOrder)
        exchangeMockPloniex.createLimitBuyOrder = CoroutineMock(side_effect=mockCreateLimitBuyOrder)
        exchangeMockPloniex.fetchOrder = CoroutineMock(side_effect=mockFetchOrder)

        sorl = self.__SORL_3()
        assert sorl.getOrderRequests()[0].amount == 11
        assert sorl.getOrderRequests()[3].amount == 21
        assert sorl.getOrderRequests()[6].amount == 31

        await self.trader.execute(sorl)

        # A tesztet úgy kell vizsgálni, hogy fixáljuk le az execute() eredményét, mert az függ a futási
        # logikától és a mock-ban használt sleep timeoktól

        assert sorl.getOrderRequests()[0].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[1].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[2].getStatus() == OrderRequestStatus.OPEN

        assert sorl.getOrderRequests()[3].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[4].getStatus() == OrderRequestStatus.CANCELED # Ez döglik meg MAJD
        assert sorl.getOrderRequests()[5].getStatus() == OrderRequestStatus.OPEN

        assert sorl.getOrderRequests()[6].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[7].getStatus() == OrderRequestStatus.OPEN
        assert sorl.getOrderRequests()[8].getStatus() == OrderRequestStatus.OPEN

        # A fenti lefixált állapotokhoz tartozó hívások count-ja

        assert exchangeMockBinance.createLimitSellOrder.await_count == 1
        assert exchangeMockBinance.createLimitBuyOrder.await_count == 2
        assert exchangeMockBinance.fetchOrder.await_count == 3
        assert exchangeMockBinance.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 3
        assert exchangeMockKraken.createLimitSellOrder.await_count == 1
        assert exchangeMockKraken.createLimitBuyOrder.await_count == 2
        assert exchangeMockKraken.fetchOrder.await_count == 3
        assert exchangeMockKraken.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 3
        assert exchangeMockPloniex.createLimitSellOrder.await_count == 1
        assert exchangeMockPloniex.createLimitBuyOrder.await_count == 2
        assert exchangeMockPloniex.fetchOrder.await_count == 3
        assert exchangeMockPloniex.cancelOrder.await_count == Trader.NOF_CCTX_RETRY * 3
        for i in range(9):
            if i == 4:
                assert sorl.getOrderRequests()[i].getStatus() == OrderRequestStatus.CANCELED
            else:
                assert sorl.getOrderRequests()[i].getStatus() == OrderRequestStatus.OPEN
        print(sorl.logStatusLogs())