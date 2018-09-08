import pytest  
from PriceStore import PriceStore

@pytest.fixture(scope="class")
def getCMCSampleFetch():
    ticker = {}
    info = {
        'id':'bitcoin',
        'name':'Bitcoin',
        'symbol':'BTC',
        'rank':'1',
        'price_usd':'6487.0022136',
        'price_btc':'1.0',
        '24h_volume_usd':'4348124443.29',
        'market_cap_usd':'111933301040',
        'available_supply':'17255012.0',
        'total_supply':'17255012.0',
        'max_supply':'21000000.0',
        'percent_change_1h':'0.2',
        'percent_change_24h':'0.17',
        'percent_change_7d':'-7.76',
        'last_updated':'1536357442'}


    ticker['BTC/USD']={
        'symbol':'BTC/USD',
        'timestamp':1536357080000,
        'datetime':'2018-09-07T21:51:20.000Z',
        'high':None,
        'low':None,
        'bid':None,
        'bidVolume':None,
        'ask':None,
        'askVolume':None,
        'vwap':None,
        'open':None,
        'close':6500,
        'last':6500,
        'previousClose':None,
        'change':0.4,
        'percentage':None,
        'average':None,
        'baseVolume':None,
        'quoteVolume':4348848637.63,
        'info':info}
    return ticker


class TestClass(object):

    def test_onePriceFromOrderbookWithinTTL(self):
        priceStore = PriceStore()
        priceStore.updatePriceFromOrderBook(symbol="BTC/USD", exchangename="kraken",asks=[[10000,1]],bids=[[9000,1]],timestamp=1)
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=30) == 9500
        with pytest.raises(ValueError):
            priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=0)


    def test_twoPriceFromOrderbookOneWithinOneOutOfTTL(self):
        priceStore = PriceStore()
        priceStore.updatePriceFromOrderBook(symbol="BTC/USD", exchangename="bitfinex",asks=[[20000,1]],bids=[[9000,1]],timestamp=0)
        priceStore.updatePriceFromOrderBook(symbol="BTC/USD", exchangename="kraken",asks=[[10000,1]],bids=[[9000,1]],timestamp=1)
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=20) == 12000
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=60) == 12000
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=61) == 9500

    def test_priceFromCoinmarketcap(self):
        priceStore = PriceStore()
        ticker=getCMCSampleFetch()
        priceStore.updatePriceFromCoinmarketcap(ticker)
        
        with pytest.raises(ValueError):
            priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=0)
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=1536357080000+1) == 6500

    def test_OB_CMC_combo(self):
        priceStore = PriceStore()
        ticker=getCMCSampleFetch()
        priceStore.updatePriceFromOrderBook(symbol="BTC/USD", exchangename="kraken",asks=[[10000,1]],bids=[[9000,1]],timestamp=1)
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=30) == 9500

        priceStore.updatePriceFromCoinmarketcap(ticker)
        with pytest.raises(ValueError):
            priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=0)
        assert priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref='USD',timestamp=1536357080000+1) == 6500
