import pytest
import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ArbitrageGraphPath import ArbitrageGraphPath
from OrderBook import OrderBookPair
from Trade import Trade, TradeStatus, TradeType


class TestClass(object):
    def test_intraExchange(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5
        p1 = arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                symbol="BTC/USD",
                exchange="kraken",
                asks=[[10000, 10]],
                bids=[[9000, 10]],
                rateBTCxBase=1,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=0,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)
        assert p1.isNegativeCycle == False

        p2 = arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="ETH/USD",
                asks=[[200, 1000]],
                bids=[[100, 1000]],
                rateBTCxBase=4.5,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=1,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        assert p2.isNegativeCycle == False

        p3 = arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="BTC/ETH",
                asks=[[5, 100]],
                bids=[[4, 100]],
                rateBTCxBase=1,
                rateBTCxQuote=4.5,
                feeRate=0,
                timestamp=2,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

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

        # segmentedTradeList = path.toSegmentedTradeList()
        # assert (segmentedTradeList[0][0].exchangeName,
        #        segmentedTradeList[0][0].symbol,
        #        segmentedTradeList[0][0].tradetype) == ('kraken', 'BTC/USD',
        #                                                TradeType.SELL)
        # assert (segmentedTradeList[0][1].exchangeName,
        #        segmentedTradeList[0][1].symbol,
        #        segmentedTradeList[0][1].tradetype) == ('kraken', 'ETH/USD',
        #                                                TradeType.BUY)
        # assert (segmentedTradeList[0][2].exchangeName,
        #        segmentedTradeList[0][2].symbol,
        #        segmentedTradeList[0][2].tradetype) == ('kraken', 'ETH/BTC',
        #                                                TradeType.SELL)

    def test_multipleExchanges(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5
        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="BTC/USD",
                asks=[[10000, 10]],
                bids=[[9000, 10]],
                rateBTCxBase=1,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=0,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="ETH/USD",
                asks=[[200, 1000]],
                bids=[[100, 1000]],
                rateBTCxBase=4.5,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=1,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                symbol="BTC/ETH",
                asks=[[5, 100]],
                bids=[[4, 100]],
                rateBTCxBase=1,
                rateBTCxQuote=4.5,
                feeRate=0,
                timestamp=2,
                exchange="poloniex",
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        arbitrageGraphPath = ArbitrageGraphPath(
            gdict=arbitrageGraph.gdict,
            nodes=[
                'kraken-BTC', 'kraken-USD', 'kraken-ETH', 'poloniex-ETH',
                'poloniex-BTC', 'kraken-BTC'
            ],
            timestamp=3,
            isNegativeCycle=None,
            length=None)
        # segmentedTradeList = arbitrageGraphPath.toSegmentedTradeList()
        print('done')

    def test_TTLTest_one(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="BTC/USD",
                asks=[[10000, 10]],
                bids=[[9000, 10]],
                rateBTCxBase=1,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=0,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="ETH/USD",
                asks=[[200, 1000]],
                bids=[[100, 1000]],
                rateBTCxBase=4.5,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=1,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="BTC/ETH",
                asks=[[5, 100]],
                bids=[[4, 100]],
                rateBTCxBase=1,
                rateBTCxQuote=4.5,
                feeRate=0,
                timestamp=2,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        with pytest.raises(ValueError):
            arbitrageGraph.getPath(
                nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
                timestamp=6)

    def test_TTLTest_two(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5

        arbitrageGraph.updatePoint(
        orderBookPair=OrderBookPair(
            exchange="kraken",
            symbol="BTC/USD",
            asks=[[10000, 10]],
            bids=[[9000, 10]],
            rateBTCxBase=1,
            rateBTCxQuote=9500,
            feeRate=0,
            timestamp=0,
            timeToLiveSec=edgeTTL
        ),
        volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="ETH/USD",
                asks=[[200, 1000]],
                bids=[[100, 1000]],
                rateBTCxBase=4.5,
                rateBTCxQuote=9500,
                feeRate=0,
                timestamp=3,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",
                symbol="BTC/ETH",
                asks=[[5, 100]],
                bids=[[4, 100]],
                rateBTCxBase=1,
                rateBTCxQuote=4.5,
                feeRate=0,
                timestamp=4,
                timeToLiveSec=edgeTTL
            ),
            volumeBTC=1)

        with pytest.raises(ValueError):
            arbitrageGraph.getPath(
                nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
                timestamp=6)

        arbitrageGraph.updatePoint(
                orderBookPair=OrderBookPair(
                    exchange="kraken",  
                    symbol="BTC/USD",
                    asks=[[12000, 10]],
                    bids=[[5000, 10]],
                    rateBTCxBase=1,
                    rateBTCxQuote=7500,
                    feeRate=0,
                    timestamp=5,
                    timeToLiveSec=edgeTTL
                ),
                volumeBTC=1)

        path = arbitrageGraph.getPath(
            nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
            timestamp=6)
        assert path.edges_age_s == [1, 3, 2]
        assert path.edges_weight == [5000, 1 / 200, 1 / 5]
        assert path.hops == 3
        assert path.exchanges_involved == ['kraken']
        assert path.nof_exchanges_involved == 1

