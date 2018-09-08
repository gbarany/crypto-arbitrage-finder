import pytest  
from Trade import Trade


class TestClass(object):

    def test_TradeInitialization(self):
        exchangeName="Coinbase Pro"
        symbol = "BTC/USD"
        amount=1
        price = 1000
        tradetype=Trade.BUY_ORDER
        trade = Trade(exchangeName=exchangeName,symbol=symbol,amount=amount,price=price,tradetype=tradetype)
        
        assert trade.exchangeName == exchangeName
        assert trade.exchangeNameStd == "coinbasepro"
        assert trade.symbol==symbol
        assert trade.amount==amount
        assert trade.price==price
        assert trade.tradetype==tradetype
        assert trade.status == Trade.STATUS_INITIAL
        assert trade.id == None
        assert trade.timestamp == None
        assert trade.datetime == None
        assert trade.cost == None
        assert trade.filled == None
        assert trade.remaining == None