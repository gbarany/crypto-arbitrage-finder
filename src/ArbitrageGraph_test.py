import pytest
import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ArbitrageGraphPath import ArbitrageGraphPath
from OrderBook import OrderBookPrice
from Trade import Trade, TradeStatus, TradeType


class TestClass(object):
    def test_intraExchange(self):
        arbitrageGraph = ArbitrageGraph()
        p1 = arbitrageGraph.updatePoint(
            symbol="BTC/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(
                meanprice=10000, limitprice=10000, vol_BASE=1),
            bidPrice=OrderBookPrice(
                meanprice=9000, limitprice=9000, vol_BASE=1),
            timestamp=0)
        assert p1.isNegativeCycle == False

        p2 = arbitrageGraph.updatePoint(
            symbol="ETH/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=200, limitprice=200, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=100, limitprice=100, vol_BASE=1),
            timestamp=1)

        assert p2.isNegativeCycle == False

        p3 = arbitrageGraph.updatePoint(
            symbol="BTC/ETH",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=5, limitprice=5, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=4, limitprice=4, vol_BASE=1),
            timestamp=2)

        assert p3.isNegativeCycle == True

        with pytest.raises(ValueError):
            path = arbitrageGraph.getPath(
                nodes=["BTC", "XRP", "ETH"], timestamp=4)

        with pytest.raises(ValueError):
            path = arbitrageGraph.getPath(
                nodes=["kraken-BTC", "kraken-XRP", "kraken-ETH"], timestamp=4)

        path = arbitrageGraph.getPath(
            nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
            timestamp=4)
        assert path.edges_age_s == [4, 3, 2]
        assert path.edges_weight == [9000, 1 / 200, 1 / 5]
        assert path.hops == 3
        assert path.exchanges_involved == ['kraken']
        assert path.nof_exchanges_involved == 1

        segmentedTradeList = path.toSegmentedTradeList()
        assert (segmentedTradeList[0][0].exchangeName,
                segmentedTradeList[0][0].symbol,
                segmentedTradeList[0][0].tradetype) == ('kraken', 'BTC/USD',
                                                        TradeType.SELL)
        assert (segmentedTradeList[0][1].exchangeName,
                segmentedTradeList[0][1].symbol,
                segmentedTradeList[0][1].tradetype) == ('kraken', 'ETH/USD',
                                                        TradeType.BUY)
        assert (segmentedTradeList[0][2].exchangeName,
                segmentedTradeList[0][2].symbol,
                segmentedTradeList[0][2].tradetype) == ('kraken', 'ETH/BTC',
                                                        TradeType.SELL)

    def test_multipleExchanges(self):
        arbitrageGraph = ArbitrageGraph(edgeTTL=5)

        arbitrageGraph.updatePoint(
            symbol="BTC/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(
                meanprice=10000, limitprice=10000, vol_BASE=1),
            bidPrice=OrderBookPrice(
                meanprice=9000, limitprice=9000, vol_BASE=1),
            timestamp=0)

        arbitrageGraph.updatePoint(
            symbol="ETH/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=200, limitprice=200, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=100, limitprice=100, vol_BASE=1),
            timestamp=1)

        arbitrageGraph.updatePoint(
            symbol="BTC/ETH",
            exchangename="poloniex",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=5, limitprice=5, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=4, limitprice=4, vol_BASE=1),
            timestamp=2)

        arbitrageGraphPath = ArbitrageGraphPath(
            gdict=arbitrageGraph.gdict,
            nodes=[
                'kraken-BTC', 'kraken-USD', 'kraken-ETH', 'poloniex-ETH',
                'poloniex-BTC', 'kraken-BTC'
            ],
            timestamp=3,
            edgeTTL_s=10,
            isNegativeCycle=None,
            length=None)
        segmentedTradeList = arbitrageGraphPath.toSegmentedTradeList()
        print('fone')

    def test_TTLTest_one(self):
        arbitrageGraph = ArbitrageGraph(edgeTTL=5)

        arbitrageGraph.updatePoint(
            symbol="BTC/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(
                meanprice=10000, limitprice=10000, vol_BASE=1),
            bidPrice=OrderBookPrice(
                meanprice=9000, limitprice=9000, vol_BASE=1),
            timestamp=0)

        arbitrageGraph.updatePoint(
            symbol="ETH/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=200, limitprice=200, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=100, limitprice=100, vol_BASE=1),
            timestamp=1)

        arbitrageGraph.updatePoint(
            symbol="BTC/ETH",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=5, limitprice=5, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=4, limitprice=4, vol_BASE=1),
            timestamp=2)

        with pytest.raises(ValueError):
            arbitrageGraph.getPath(
                nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
                timestamp=6)

    def test_TTLTest_two(self):
        arbitrageGraph = ArbitrageGraph(edgeTTL=5)
        arbitrageGraph.updatePoint(
            symbol="BTC/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(
                meanprice=10000, limitprice=10000, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=9000, limitprice=9000),
            timestamp=0)
        arbitrageGraph.updatePoint(
            symbol="ETH/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=200, limitprice=200, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=100, limitprice=100),
            timestamp=3)
        arbitrageGraph.updatePoint(
            symbol="BTC/ETH",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(meanprice=5, limitprice=5, vol_BASE=1),
            bidPrice=OrderBookPrice(meanprice=4, limitprice=4),
            timestamp=4)

        with pytest.raises(ValueError):
            arbitrageGraph.getPath(
                nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
                timestamp=6)

        arbitrageGraph.updatePoint(
            symbol="BTC/USD",
            exchangename="kraken",
            feeRate=0.0,
            askPrice=OrderBookPrice(
                meanprice=12000, limitprice=12000, vol_BASE=1),
            bidPrice=OrderBookPrice(
                meanprice=5000, limitprice=5000, vol_BASE=1),
            timestamp=5)

        path = arbitrageGraph.getPath(
            nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
            timestamp=6)
        assert path.edges_age_s == [1, 3, 2]
        assert path.edges_weight == [5000, 1 / 200, 1 / 5]
        assert path.hops == 3
        assert path.exchanges_involved == ['kraken']
        assert path.nof_exchanges_involved == 1


if __name__ == "__main__":
    tc = TestClass()
    tc.test_multipleExchanges()
