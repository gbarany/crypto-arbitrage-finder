import pytest  
from OrderbookAnalyser import OrderbookAnalyser

from threading import Condition, Thread

arbTradeTriggerEvent = Condition()
arbTradeQueue = []

@pytest.fixture(scope="class")
def getOrderbookAnalyser():
  return OrderbookAnalyser(
        vol_BTC=[1,0.1,0.01],
        edgeTTL=30,
        priceTTL=60,
        tradeLogFilename='tradelog_live_test.csv',
        priceSource=OrderbookAnalyser.PRICE_SOURCE_CMC,
        arbTradeTriggerEvent=arbTradeTriggerEvent,
        arbTradeQueue=arbTradeQueue)

class TestClass(object):

    def test_one(self):
        orderbookAnalyser = getOrderbookAnalyser()
        assert orderbookAnalyser.priceSource==OrderbookAnalyser.PRICE_SOURCE_CMC
