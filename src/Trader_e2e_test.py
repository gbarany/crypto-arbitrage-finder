import pytest
from Trader import Trader
from OrderRequest import OrderRequest, OrderRequestStatus, OrderRequestType, OrderRequestList, SegmentedOrderRequestList
import jsonpickle


class TestClass(object):
    exch = "kraken"

    @pytest.mark.skip(reason="e2e test")
    @pytest.mark.asyncio
    async def test_execute_trades(self):
        exch = self.exch
        market_symbol = 'ETH/EUR'
        # market_symbol = 'ETH/BTC'
        trader = Trader(
            credfile='./cred/api_balance.json',
            is_sandbox_mode=False)
        await trader.initExchanges()
        exchange = trader.get_exchange(exch)
        ob = await exchange.fetch_order_book(market_symbol, limit=20)
        lowest_ask = ob["asks"][0][0]
        highest_bid = ob["bids"][0][0]
        min_cost = exchange.market(market_symbol)["limits"]["cost"]["min"]
        price = 200
        amount = max(exchange.market(market_symbol)["limits"]["amount"]["min"], trader.get_min_trade_amount(
            exch,
            market_symbol))  # https://support.kraken.com/hc/en-us/articles/205893708-What-is-the-minimum-order-size-
        if 0 < min_cost < amount * price:
            amount = min_cost / 0.1
        # amount = 0.01
        trade_1 = OrderRequest(exch, market_symbol, amount, price, OrderRequestType.SELL)
        # trade_2 = Trade(exch, market_symbol, trader.get_min_trade_amount(exch, market_symbol), price, TradeType.SELL)
        print(jsonpickle.encode(trade_1))
        tl = OrderRequestList([trade_1])
        stl = SegmentedOrderRequestList([tl])
        await trader.execute(stl)
        # await trader.cancel_all_trade_orders()
        # await trader.close_exchanges()

    @pytest.mark.skip(reason="e2e test")
    @pytest.mark.asyncio
    async def test_fetch_balances(self):
        exch = self.exch
        trader = Trader(
            exchange_names=[exch],
            credfile='./cred/api_balance.json',
            is_sandbox_mode=True)
        await trader.initExchanges()
        assert trader.is_sandbox_mode is True
        assert (exch in trader.__balance) is False
        await trader.fetch_balances()
        assert (exch in trader.__balance) is True
        assert len(trader.__balance) > 0
        assert len(trader.__balance[exch]) > 0
        await trader.close_exchanges()

    @pytest.mark.skip(reason="e2e test")
    @pytest.mark.asyncio
    async def test_transaction_valid(self, mocker):
        exch = self.exch
        trader = Trader(
            exchange_names=[exch],
            credfile='./cred/api_balance.json',
            is_sandbox_mode=True)
        await trader.initExchanges()
        # monkeypatch.setattr(trader, 'get_free_balance', lambda: 123)

        market = 'ETH/BTC'
        assert trader.is_sandbox_mode is True
        with pytest.raises(ValueError):
            trader.is_transaction_valid(exch, 'FGH', 1)
        assert market in trader.__exchanges[exch].markets
        with pytest.raises(ValueError):
            trader.is_transaction_valid(exch, market, 0.00000000001)
        with pytest.raises(ValueError):
            trader.is_transaction_valid(exch, market, 1000000000000)
        max_amount = trader.__exchanges[exch].markets[market]['limits']['price']['max']
        min_amount = trader.__exchanges[exch].markets[market]['limits']['price']['min']
        with pytest.raises(ValueError):
            trader.is_transaction_valid(exch, market, max_amount)

        # MOCK for the test
        trader.__exchanges[exch].markets[market]['limits']['price']['max'] = 2
        trader.get_free_balance = mocker.MagicMock(
            return_value=1)  # MOCK for the test
        assert trader.is_transaction_valid(exch, market, 1) is True
        with pytest.raises(ValueError):
            assert trader.is_transaction_valid(exch, market, 1.5) is True
        with pytest.raises(ValueError):
            trader.is_transaction_valid(exch, market, 2.5) is True

        await trader.close_exchanges()

    @pytest.mark.skip(reason="e2e test")
    @pytest.mark.asyncio
    async def test_fetch_order_statuses(self):
        exch = self.exch
        trader = Trader(exchange_names=[
            exch], credfile='./cred/api_balance.json', is_sandbox_mode=True)
        await trader.initExchanges()
        await trader.fetch_order_statuses()
        await trader.close_exchanges()
