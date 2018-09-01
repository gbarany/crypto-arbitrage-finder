import pytest

@pytest.fixture
def orderbookStrInit():
    from OrderBook import OrderBook
    return OrderBook(symbol="BTC/USD",asks="[[7500, 1],[8000, 1]]",bids="[[7000, 1],[6500, 1]]")

@pytest.fixture
def orderbookListInit():
    from OrderBook import OrderBook
    return OrderBook(symbol="BTC/USD",asks=[[7500, 1],[8000, 1]],bids=[[7000, 1],[6500, 1]])

class TestClass(object):

    def test_one(self):
        orderBook=orderbookStrInit()
        askprice = orderBook.getAskPrice(1)
        bidprice = orderBook.getBidPrice(1)

        assert askprice.meanprice == 7500
        assert askprice.limitprice == 7500
        assert bidprice.meanprice == 7000
        assert bidprice.limitprice == 7000

    def test_two(self):
        orderBook=orderbookStrInit()
        askprice = orderBook.getAskPrice(2)
        bidprice = orderBook.getBidPrice(2)

        assert askprice.meanprice == 7750
        assert askprice.limitprice == 8000
        assert bidprice.meanprice == 6750
        assert bidprice.limitprice == 6500

    def test_zero(self):
        orderBook=orderbookStrInit()
        askprice = orderBook.getAskPrice(0)
        bidprice = orderBook.getBidPrice(0)

        assert askprice.meanprice == None
        assert askprice.limitprice ==  None
        assert bidprice.meanprice ==  None
        assert bidprice.limitprice ==  None

    def test_equivalence(self):
        orderBook1=orderbookStrInit()
        orderBook2=orderbookListInit()
        assert orderBook1==orderBook2