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

@pytest.fixture(scope="class")
def getCMCSampleFetch():
    ticker = {}

    ticker['BTC/USD']={
        'symbol':'BTC/USD',
        'timestamp':100,
        'last':6500}
    
    ticker['ETH/USD']={
        'symbol':'ETH/USD',
        'timestamp':100,
        'last':6500}

    ticker['ETH/BTC']={
        'symbol':'ETH/BTC',
        'timestamp':100,
        'last':6500}

    return ticker


class TestClass(object):

    def test_one(self):

        orderbookAnalyser = getOrderbookAnalyser()
        cmc=getCMCSampleFetch()
        orderbookAnalyser.updateCmcPrice(cmc)
        orderbookAnalyser.update('kraken','BTC/USD',bids=[[9000,1]],asks=[[10000,1]],id=1,timestamp=100)
        orderbookAnalyser.update('kraken','ETH/USD',bids=[[100,10]],asks=[[200,10]],id=2,timestamp=101)
        orderbookAnalyser.update('kraken','ETH/BTC',bids=[[1/4,10]],asks=[[1/5,10]],id=3,timestamp=102)

        arbTradeTriggerEvent.acquire()
        TRADE_EVENT_TRIGGERED = arbTradeTriggerEvent.wait(2)            
        arbTradeTriggerEvent.release()
            

        assert TRADE_EVENT_TRIGGERED == True

if __name__ == "__main__":
    tc=TestClass()
    tc.test_one()