import pytest

from Trader import Trader
from Trade import Trade, TradeStatus, TradeType


@pytest.fixture(scope="class")
def getOrderbookAnalyser():
    pass


class TestClass(object):
    exch = "binance"

    @pytest.mark.asyncio
    async def test_execute_trades(self):
        exch = self.exch
        market_symbol = 'ETH/BTC'
        with Trader(exchangeNames=[exch], credfile='./cred/api_balance.json', isSandboxMode=True) as trader:
            exchange = trader.get_exchange(exch)
            ob = await exchange.fetch_order_book(market_symbol, limit=20)
            print(ob)
            trade = Trade(exch, market_symbol, trader.get_min_trade_amount(exch, market_symbol), 1, TradeType.BUY)
            trader.execute_trades([trade])

    def test_fetch_balances(self):
        exch = self.exch
        with Trader(exchangeNames=[exch], credfile='./cred/api_balance.json', isSandboxMode=True) as trader:
            assert trader.isSandboxMode is True
            assert (exch in trader.balance) is False
            trader.fetch_balances()
            assert (exch in trader.balance) is True
            assert len(trader.balance) > 0
            assert len(trader.balance[exch]) > 0

    def test_transaction_valid(self, mocker):
        exch = self.exch
        with Trader(exchangeNames=[exch], credfile='./cred/api_balance.json', isSandboxMode=True) as trader:
            # monkeypatch.setattr(trader, 'get_free_balance', lambda: 123)

            market = 'ETH/BTC'
            assert trader.isSandboxMode is True
            with pytest.raises(ValueError):
                trader.is_transaction_valid(exch, 'FGH', 1)
            assert market in trader.exchanges[exch].markets
            with pytest.raises(ValueError):
                trader.is_transaction_valid(exch, market, 0.00000000001)
            with pytest.raises(ValueError):
                trader.is_transaction_valid(exch, market, 1000000000000)
            max_amount = trader.exchanges[exch].markets[market]['limits']['price']['max']
            min_amount = trader.exchanges[exch].markets[market]['limits']['price']['min']
            with pytest.raises(ValueError):
                trader.is_transaction_valid(exch, market, max_amount)

            trader.exchanges[exch].markets[market]['limits']['price']['max'] = 2  # MOCK for the test
            trader.get_free_balance = mocker.MagicMock(return_value=1)  # MOCK for the test
            assert trader.is_transaction_valid(exch, market, 1) is True
            with pytest.raises(ValueError):
                assert trader.is_transaction_valid(exch, market, 1.5) is True
            with pytest.raises(ValueError):
                trader.is_transaction_valid(exch, market, 2.5) is True

    def test_fetch_order_statuses(self):
        exch = self.exch
        with Trader(exchangeNames=[exch], credfile='./cred/api_balance.json', isSandboxMode=True) as trader:
            trader.fetch_order_statuses()

    #
    # def test_one(self):
    #     with Trader(exchangeNames=["binance"]
    #                   , credfile='./cred/api_balance.json', isSandboxMode=True) as trader:
    #         trade_list = [
    #             Trade("binance", "BTC/USD", 0.1, 20000, TradeType.SELL),
    #         ]
    #         assert trader.isSandboxMode is True
    #         assert ('binance' in trader.balance) is False
    #         trader.executeTrades(trade_list)
    #         assert ('binance' in trader.balance) is True
    #         print("done")

# if __name__ == "__main__":
#     TC = TestClass()
#     TC.test_fetch_balances()
#     TC.test_transaction_valid()
