import pytest
from OrderBook import OrderBook, OrderBookPair

@pytest.fixture
def orderbookPairStrInit():
    
    return OrderBookPair(
        timestamp=123,
        exchange="Kraken",
        timeToLiveSec=5,
        symbol="BTC/USD",
        asks="[[7500, 1],[8000, 1]]",
        bids="[[7000, 1],[6500, 1]]",
        rateBTCxBase=1,
        rateBTCxQuote=7750,
        feeRate=0.1)


@pytest.fixture
def orderbookPairListInit():
    return OrderBookPair(
        timestamp=123,
        exchange="Kraken",
        timeToLiveSec=5,
        symbol="BTC/USD",
        asks=[[7500, 1], [8000, 1]],
        bids=[[7000, 1], [6500, 1]],
        rateBTCxBase=1,
        rateBTCxQuote=7750,
        feeRate=0.1)


class TestClass(object):
    def test_one(self):
        orderBookPair = orderbookPairStrInit()
        askprice = orderBookPair.asks.getPrice(volumeBase=1)
        bidprice = orderBookPair.bids.getPrice(volumeBase=1)

        assert askprice.meanPrice == 7500
        assert askprice.meanPriceNet == 7500*0.9
        assert askprice.limitPrice == 7500
        assert askprice.volumeBTC == 1
        assert askprice.volumeBase == 1
        assert askprice.feeRate==0.1
        assert askprice.feeAmountBTC == 0.1
        assert askprice.feeAmountBase == 0.1

        assert bidprice.meanPrice == 7000
        assert bidprice.meanPriceNet == 7000*0.9
        assert bidprice.limitPrice == 7000
        assert bidprice.volumeBTC == 1
        assert bidprice.volumeBase == 1
        assert bidprice.feeRate==0.1
        assert bidprice.feeAmountBTC == 0.1
        assert bidprice.feeAmountBase == 0.1


    def test_two(self):
        orderBookPair = orderbookPairStrInit()
        askprice = orderBookPair.asks.getPrice(volumeBase=2)
        bidprice = orderBookPair.bids.getPrice(volumeBase=2)

        assert askprice.meanPrice == 7750
        assert askprice.limitPrice == 8000
        assert askprice.volumeBTC == 2
        assert askprice.volumeBase == 2
        assert askprice.feeRate==0.1
        assert askprice.feeAmountBTC == 0.2
        assert askprice.feeAmountBase == 0.2

        assert bidprice.meanPrice == 6750
        assert bidprice.limitPrice == 6500
        assert bidprice.volumeBTC == 2
        assert bidprice.volumeBase == 2
        assert bidprice.feeRate==0.1
        assert bidprice.feeAmountBTC == 0.2
        assert bidprice.feeAmountBase == 0.2

    def test_rebaseOrderbook(self):
        orderBookAskRebased = orderbookPairStrInit().getRebasedAsksOrderbook()
        orberbook = orderBookAskRebased.getPrice(volumeBase=1000)
        assert orberbook.feeAmountBase == 100.0
        assert orberbook.feeRate == 0.1
        assert orberbook.feeAmountBTC == 100.0/7750
        assert orberbook.limitPrice == 1/7500
        assert orberbook.meanPrice == 1/7500
        assert orberbook.meanPriceNet == 1/7500*0.9
        assert orberbook.volumeBTC == 1000/7750
        assert orberbook.volumeBase == 1000

    def test_zero(self):
        orderBookPair = orderbookPairStrInit()
        askprice = orderBookPair.asks.getPrice(3)
        bidprice = orderBookPair.bids.getPrice(3)

        assert askprice.meanPrice == None
        assert askprice.limitPrice == None
        assert askprice.volumeBTC == None
        assert askprice.volumeBase == None
        assert askprice.feeAmountBTC == None
        assert askprice.feeAmountBase == None

        assert bidprice.meanPrice == None
        assert bidprice.limitPrice == None
        assert bidprice.volumeBTC == None
        assert bidprice.volumeBase == None
        assert bidprice.feeAmountBTC == None
        assert bidprice.feeAmountBase == None

    def test_equivalence(self):
        orderBookPair1 = orderbookPairStrInit()
        orderBookPair2 = orderbookPairListInit()
        orderBook1 = orderBookPair1.asks
        orderBook2 = orderBookPair2.asks
        assert orderBook1 == orderBook2
