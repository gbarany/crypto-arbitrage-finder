from typing import List

import pytest
from OrderbookAnalyser import OrderbookAnalyser
from Trade import Trade, TradeStatus, TradeType

from threading import Condition, Thread
import time

arbTradeTriggerEvent = Condition()
arbTradeQueue = []
#vol_BTC=[1,0.1,0.01]
vol_BTC = [1]


@pytest.fixture(scope="class")
def getOrderbookAnalyser():
    return OrderbookAnalyser(
        vol_BTC=vol_BTC,
        edgeTTL=30,
        priceTTL=60,
        tradeLogFilename='tradelog_live_test.csv',
        priceSource=OrderbookAnalyser.PRICE_SOURCE_CMC,
        arbTradeTriggerEvent=arbTradeTriggerEvent,
        arbTradeQueue=arbTradeQueue)


@pytest.fixture(scope="class")
def getCMCSampleFetch():
    ticker = {}

    ticker['BTC/USD'] = {'symbol': 'BTC/USD', 'timestamp': 100, 'last': 9000}

    ticker['ETH/USD'] = {'symbol': 'ETH/USD', 'timestamp': 100, 'last': 100}

    ticker['ETH/BTC'] = {'symbol': 'ETH/BTC', 'timestamp': 100, 'last': 0.03}

    return ticker


class TestClass(object):
    def test_one(self):

        orderbookAnalyser = getOrderbookAnalyser()
        cmc = getCMCSampleFetch()

        def feedSamples():
            time.sleep(0.2)
            orderbookAnalyser.updateCmcPrice(cmc)
            orderbookAnalyser.update(
                'kraken',
                'BTC/USD',
                bids=[[9000, 1]],
                asks=[[10000, 1]],
                id=1,
                timestamp=100)
            orderbookAnalyser.update(
                'kraken',
                'ETH/USD',
                bids=[[100, 1000]],
                asks=[[200, 1000]],
                id=2,
                timestamp=101)
            orderbookAnalyser.update(
                'kraken',
                'ETH/BTC',
                bids=[[0.03, 1000]],
                asks=[[0.04, 1000]],
                id=3,
                timestamp=102)

        Thread(target=feedSamples).start()

        for i in range(len(vol_BTC)):
            arbTradeTriggerEvent.acquire()
            TRADE_EVENT_TRIGGERED = arbTradeTriggerEvent.wait(1)
            #TRADE_EVENT_TRIGGERED = arbTradeTriggerEvent.wait()
            arbTradeTriggerEvent.release()
            assert (i, TRADE_EVENT_TRIGGERED) == (i, True)

        assert len(arbTradeQueue) == len(vol_BTC)

        path = arbTradeQueue[0]
        tradeList: List[Trade] = path.toTradeList()
        trade = tradeList[0]
        assert (trade.market, trade.amount, trade.price, trade.trade_type,
                trade.status) == ('BTC/USD', vol_BTC[0], 9000, TradeType.BUY,
                                  TradeStatus.INITIAL)

        trade = tradeList[1]
        assert (trade.market, trade.amount, trade.price, trade.trade_type,
                trade.status) == ('ETH/USD',
                                  vol_BTC[0] / cmc['ETH/BTC']['last'], 200,
                                  TradeType.BUY, TradeStatus.INITIAL)

        trade = tradeList[2]
        assert (trade.market, trade.amount, trade.price, trade.trade_type,
                trade.status) == ('ETH/BTC',
                                  vol_BTC[0] / cmc['ETH/BTC']['last'], 0.03,
                                  TradeType.SELL, TradeStatus.INITIAL)


if __name__ == "__main__":
    tc = TestClass()
    tc.test_one()
