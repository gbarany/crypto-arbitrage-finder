import pytest
import numpy as np
from ArbitrageGraph import ArbitrageGraph
from OrderBook import OrderBookPair
from OrderRequest import OrderRequestType


class TestClass(object):
    def test_intraExchange(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5
        arbitrageGraph.updatePoint(
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
        p1 = arbitrageGraph.getArbitrageDeal(0)
        assert p1.isProfitable() == False

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
        p2 = arbitrageGraph.getArbitrageDeal(1)
        assert p2.isProfitable() == False

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
        p3 = arbitrageGraph.getArbitrageDeal(2)
        assert p3.isProfitable() == True

        with pytest.raises(ValueError):
            path = arbitrageGraph.getPath(
                nodes=["BTC", "XRP", "ETH"], timestamp=4)

        with pytest.raises(ValueError):
            path = arbitrageGraph.getPath(
                nodes=["kraken-BTC", "kraken-XRP", "kraken-ETH"], timestamp=4)

        path = arbitrageGraph.getPath(
            nodes=["kraken-BTC", "kraken-USD", "kraken-ETH", "kraken-BTC"],
            timestamp=4)
        assert path.getAge() == [4, 3, 2]
        assert path.getPrice() == [9000, 1 / 200, 1 / 5]
        assert path.getNofTotalTransactions() == 3
        assert path.getNofIntraexchangeTransactions() == 3
        assert path.getExchangesInvolved() == ['kraken']
        assert path.getNofExchangesInvolved() == 1
        assert path.getProfit() == 800

        segmentedOrderList = path.toSegmentedOrderList().getOrderRequestLists()
        assert (segmentedOrderList[0][0].exchange_name,
                segmentedOrderList[0][0].market,
                segmentedOrderList[0][0].type) == ('kraken', 'BTC/USD',OrderRequestType.SELL)
        assert (segmentedOrderList[0][1].exchange_name,
                segmentedOrderList[0][1].market,
                segmentedOrderList[0][1].type) == ('kraken', 'ETH/USD',OrderRequestType.BUY)
        assert (segmentedOrderList[0][2].exchange_name,
                segmentedOrderList[0][2].market,
                segmentedOrderList[0][2].type) == ('kraken', 'ETH/BTC',OrderRequestType.SELL)

    def test_multipleExchanges(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5
        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(exchange="kraken",symbol="BTC/USD",asks=[[10000, 10]],bids=[[9000, 10]],rateBTCxBase=1,rateBTCxQuote=9500,feeRate=0,timestamp=0,timeToLiveSec=edgeTTL),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",symbol="ETH/USD",asks=[[200, 1000]],bids=[[100, 1000]],rateBTCxBase=4.5,rateBTCxQuote=9500,feeRate=0,timestamp=1,timeToLiveSec=edgeTTL),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="poloniex",symbol="BTC/ETH",asks=[[5, 100]],bids=[[4, 100]],rateBTCxBase=1,rateBTCxQuote=4.5,feeRate=0,timestamp=2,timeToLiveSec=edgeTTL),
            volumeBTC=1)

        path = arbitrageGraph.getPath(
            nodes=['kraken-BTC', 'kraken-USD', 'kraken-ETH', 'poloniex-ETH','poloniex-BTC', 'kraken-BTC'],
            timestamp=3)
        assert path.getProfit() == 800

        segmentedOrderRequestLists = path.toSegmentedOrderList().getOrderRequestLists()
        assert len(segmentedOrderRequestLists) == 2
        assert len(segmentedOrderRequestLists[0].getOrderRequests()) == 2
        assert len(segmentedOrderRequestLists[1].getOrderRequests()) == 1

        segmentedOrderRequestLists[0].getOrderRequests()[0].exchange_name == 'kraken'
        segmentedOrderRequestLists[0].getOrderRequests()[0].market == 'BTC/USD'
        segmentedOrderRequestLists[0].getOrderRequests()[0].price == 9000
        segmentedOrderRequestLists[0].getOrderRequests()[0].amount == 1

        segmentedOrderRequestLists[0].getOrderRequests()[1].exchange_name == 'kraken'
        segmentedOrderRequestLists[0].getOrderRequests()[1].market == 'ETH/USD'
        segmentedOrderRequestLists[0].getOrderRequests()[1].price == 200
        segmentedOrderRequestLists[0].getOrderRequests()[1].amount == 4.5

        segmentedOrderRequestLists[1].getOrderRequests()[0].exchange_name == 'poloniex'
        segmentedOrderRequestLists[1].getOrderRequests()[0].market == 'ETH/BTC'
        segmentedOrderRequestLists[1].getOrderRequests()[0].price == 0.2
        segmentedOrderRequestLists[1].getOrderRequests()[0].amount == 4.5


    def test_multipleExchanges_merge_segments(self):
        arbitrageGraph = ArbitrageGraph()
        edgeTTL=5
        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(exchange="kraken",symbol="BTC/USD",asks=[[10000, 10]],bids=[[9000, 10]],rateBTCxBase=1,rateBTCxQuote=9500,feeRate=0,timestamp=0,timeToLiveSec=edgeTTL),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="kraken",symbol="ETH/USD",asks=[[200, 1000]],bids=[[100, 1000]],rateBTCxBase=4.5,rateBTCxQuote=9500,feeRate=0,timestamp=1,timeToLiveSec=edgeTTL),
            volumeBTC=1)

        arbitrageGraph.updatePoint(
            orderBookPair=OrderBookPair(
                exchange="poloniex",symbol="BTC/ETH",asks=[[5, 100]],bids=[[4, 100]],rateBTCxBase=1,rateBTCxQuote=4.5,feeRate=0,timestamp=2,timeToLiveSec=edgeTTL),
            volumeBTC=1)

        path = arbitrageGraph.getPath(
            nodes=['kraken-USD', 'kraken-ETH', 'poloniex-ETH','poloniex-BTC', 'kraken-BTC','kraken-USD'],
            timestamp=3)
        assert path.getProfit() == 800

        segmentedOrderRequestLists = path.toSegmentedOrderList().getOrderRequestLists()
        assert len(segmentedOrderRequestLists) == 2
        assert len(segmentedOrderRequestLists[0].getOrderRequests()) == 2
        assert len(segmentedOrderRequestLists[1].getOrderRequests()) == 1

        segmentedOrderRequestLists[0].getOrderRequests()[0].exchange_name == 'kraken'
        segmentedOrderRequestLists[0].getOrderRequests()[0].market == 'BTC/USD'
        segmentedOrderRequestLists[0].getOrderRequests()[0].price == 9000
        segmentedOrderRequestLists[0].getOrderRequests()[0].amount == 1

        segmentedOrderRequestLists[0].getOrderRequests()[1].exchange_name == 'kraken'
        segmentedOrderRequestLists[0].getOrderRequests()[1].market == 'ETH/USD'
        segmentedOrderRequestLists[0].getOrderRequests()[1].price == 200
        segmentedOrderRequestLists[0].getOrderRequests()[1].amount == 4.5

        segmentedOrderRequestLists[1].getOrderRequests()[0].exchange_name == 'poloniex'
        segmentedOrderRequestLists[1].getOrderRequests()[0].market == 'ETH/BTC'
        segmentedOrderRequestLists[1].getOrderRequests()[0].price == 0.2
        segmentedOrderRequestLists[1].getOrderRequests()[0].amount == 4.5
        
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
        assert path.getAge() == [1, 3, 2]
        assert path.getPrice() == [5000, 1 / 200, 1 / 5]
        assert path.getNofTotalTransactions() == 3
        assert path.getNofIntraexchangeTransactions() == 3
        assert path.getExchangesInvolved() == ['kraken']
        assert path.getNofExchangesInvolved() == 1
        assert path.getProfit() == 400

        segmentedOrderRequestLists = path.toSegmentedOrderList().getOrderRequestLists()
        assert len(segmentedOrderRequestLists)==1
        assert len(segmentedOrderRequestLists[0])==3
        
        assert segmentedOrderRequestLists[0][0].exchange_name == 'kraken'
        assert segmentedOrderRequestLists[0][0].market == 'BTC/USD'
        assert segmentedOrderRequestLists[0][0].price == 5000
        assert segmentedOrderRequestLists[0][0].amount == 1

        assert segmentedOrderRequestLists[0][1].exchange_name == 'kraken'
        assert segmentedOrderRequestLists[0][1].market == 'ETH/USD'
        assert segmentedOrderRequestLists[0][1].price == 200
        assert segmentedOrderRequestLists[0][1].amount == 4.5

        assert segmentedOrderRequestLists[0][2].exchange_name == 'kraken'
        assert segmentedOrderRequestLists[0][2].market == 'ETH/BTC'
        assert segmentedOrderRequestLists[0][2].price == 1/5
        assert segmentedOrderRequestLists[0][2].amount == 4.5
