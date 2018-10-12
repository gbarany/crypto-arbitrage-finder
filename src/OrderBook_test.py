import pytest
from OrderBook import OrderBook, OrderBookPair

@pytest.fixture
def orderbookPairStrInit():
    
    return OrderBookPair(
        symbol="BTC/USD",
        asks="[[7500, 1],[8000, 1]]",
        bids="[[7000, 1],[6500, 1]]",
        rateBTCxBase=1,
        rateBTCxQuote=7750)


@pytest.fixture
def orderbookPairListInit():
    return OrderBookPair(
        symbol="BTC/USD",
        asks=[[7500, 1], [8000, 1]],
        bids=[[7000, 1], [6500, 1]],
        rateBTCxBase=1,
        rateBTCxQuote=7750)


class TestClass(object):
    def test_one(self):
        orderBookPair = orderbookPairStrInit()
        askprice = orderBookPair.asks.getPrice(1)
        bidprice = orderBookPair.bids.getPrice(1)

        assert askprice.meanPrice == 7500
        assert askprice.limitPrice == 7500
        assert bidprice.meanPrice == 7000
        assert bidprice.limitPrice == 7000

    def test_two(self):
        orderBookPair = orderbookPairStrInit()
        askprice = orderBookPair.asks.getPrice(2)
        bidprice = orderBookPair.bids.getPrice(2)

        assert askprice.meanPrice == 7750
        assert askprice.limitPrice == 8000
        assert bidprice.meanPrice == 6750
        assert bidprice.limitPrice == 6500

    def test_zero(self):
        orderBookPair = orderbookPairStrInit()
        askprice = orderBookPair.asks.getPrice(3)
        bidprice = orderBookPair.bids.getPrice(3)

        assert askprice.meanPrice == None
        assert askprice.limitPrice == None
        assert bidprice.meanPrice == None
        assert bidprice.limitPrice == None

    def test_equivalence(self):
        orderBookPair1 = orderbookPairStrInit()
        orderBookPair2 = orderbookPairListInit()
        orderBook1 = orderBookPair1.asks
        orderBook2 = orderBookPair2.asks
        assert orderBook1 == orderBook2
