import pytest
from Trade import Trade, TradeStatus, TradeType


class TestClass(object):
    def test_trade_initialization(self):
        exchange_name = "Coinbase Pro"
        symbol = "BTC/USD"
        amount = 1
        price = 1000
        trade_type = TradeType.BUY
        trade = Trade(
            exchange=exchange_name,
            market=symbol,
            amount=amount,
            price=price,
            trade_type=trade_type)

        assert trade.exchangeName == exchange_name
        assert trade.exchangeNameStd == "coinbasepro"
        assert trade.market == symbol
        assert trade.amount == amount
        assert trade.price == price
        assert trade.trade_type == trade_type
        assert trade.status == TradeStatus.INITIAL
        assert trade.id == None
        assert trade.timestamp == None
        assert trade.datetime == None
        assert trade.cost == None
        assert trade.filled == None
        assert trade.remaining == None
