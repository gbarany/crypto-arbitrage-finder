import pytest
from asynctest import TestCase, logging

from Trader import Trader
from OrderRequest import OrderRequest, OrderRequestStatus, OrderRequestType, OrderRequestList, SegmentedOrderRequestList
import jsonpickle

POLONIEX = 'poloniex'
BINANCE = 'binance'
KRAKEN = 'kraken'
BITSTAMP = 'bitstamp'
COINBASEPRO = 'coinbasepro'
BITTREX = 'bittrex'
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
    isSandboxMode = False

    async def setUp(self):
        self.trader = Trader(is_sandbox_mode=TestClass.isSandboxMode)
        await self.trader.initExchangesFromAWSParameterStore()

    async def TearDown(self):
        await self.trader.close_exchanges()

    async def __test_fetch_balances(self, exch):
        assert (exch in self.trader.getBalances()) is True
        assert len(self.trader.getBalances()) > 0
        assert len(self.trader.getBalances()[exch]) > 0

    @pytest.mark.skip(reason="e2e test")
    @pytest.mark.asyncio
    async def test_fetch_balances(self):
        assert self.trader.isSandboxMode() is False
        await self.__test_fetch_balances(KRAKEN)
        await self.__test_fetch_balances(BITSTAMP)
        await self.__test_fetch_balances(BITTREX)
        await self.__test_fetch_balances(COINBASEPRO)


    @pytest.mark.skip(reason="e2e test")
    @pytest.mark.asyncio
    async def test_execute_trades(self):

        self.trader.input = lambda x: 'ok'

        or11 = OrderRequest(COINBASEPRO, ETH_BTC, amount=0.1, price=0.02, requestType=OrderRequestType.BUY)

        orl1 = OrderRequestList([or11])
        # orl2 = OrderRequestList([or21, or22])
        stl = SegmentedOrderRequestList([orl1])
        await self.trader.execute(stl)
