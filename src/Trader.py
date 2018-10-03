import traceback
from typing import Dict, List, Any

import asyncio
import json
import ccxt.async_support as ccxt
from ccxt.async_support.base.exchange import Exchange
from InitLogger import logger
from Trade import Trade, TradeStatus, TradeType
from Exceptions import OrderCreationError, TradesShowstopper
import time


class Trader:
    NOF_CCTX_RETRY = 4
    TTL_TRADEORDER_S = 10

    def __init__(self,
                 exchangeNames: List[str] = [],
                 credfile='./cred/api.json',
                 isSandboxMode=True):
        self.keys = {}
        self.balance = {}
        self.credfile = credfile
        self.trades = {}
        self.isSandboxMode = isSandboxMode
        with open(self.credfile) as file:
            self.keys = json.load(file)

        self.exchanges: Dict[str, Exchange] = {}
        tasks = []
        for exchangeName in exchangeNames:
            tasks.append(
                asyncio.ensure_future(self.initExchange(exchangeName)))
        logger.info("Exchanges init started")
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Exchanges init completed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closeExchanges()

    async def initExchange(self, exchangeName: str):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
        await exchange.load_markets()
        self.exchanges[exchangeName.lower().replace(" ", "")] = exchange

    async def closeExchange(self, exchange):
        await exchange.close()

    def closeExchanges(self):
        tasks = []
        for _, exchange in self.exchanges.items():
            tasks.append(asyncio.ensure_future(self.closeExchange(exchange)))
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Exchanges closed")

    async def cancelTradeOrder(self, trade: Trade):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                response = await self.exchanges[
                    trade.exchangeNameStd].cancelOrder(trade.id)
                if response['error']:
                    raise ValueError('Error in exchange response:' +
                                     str(response['error']))
                logger.info('Cancelled trade oder ' + trade.id + ' on ' +
                            trade.exchangeNameStd)
                del self.trades[trade.id]
                return
            except Exception as e:
                logger.error('Trader order cancellation failed for ' +
                             str(trade.id) + " " + trade.market + " " +
                             trade.exchangeName + " " + str(e.args) +
                             " retrycntr:" + str(retrycntr))
                await asyncio.sleep(
                    self.exchanges[trade.exchangeNameStd].rateLimit / 1000)

    def cancelOpenTradeOrders(self):
        tasks = []
        for _, trade in self.trades.items():
            if trade.status == 'open':
                tasks.append(
                    asyncio.ensure_future(self.cancelTradeOrder(trade)))
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Cancellation of open trade orders completed")

    def purgeClosedTradeOrders(self):
        for _, trade in self.trades.items():
            if trade.status == 'closed':
                del self.trades[trade.id]
        logger.info("Purging of closed trade orders completed")
        if bool(self.trades):
            logger.error(
                "There are pending trades left after purging. Trades dump:" +
                json.dumps(self.trades))
        else:
            logger.info("Trades purged successfully")

    async def fetchOrderStatus(self, trade: Trade):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                response = await self.exchanges[
                    trade.exchangeNameStd].fetchOrder(trade.id)
                trade.timestamp = response["timestamp"]
                trade.datetime = response["datetime"]
                trade.status = response["status"]
                trade.cost = response["cost"]
                trade.amount = response["amount"]
                trade.filled = response["filled"]
                trade.remaining = response["remaining"]
                self.trades[trade.id] = trade
                logger.info('Order status fetched ' + trade.id + ' from ' +
                            trade.exchangeName)
                return
            except Exception as e:
                logger.error('Order status fetching failed for ' +
                             str(trade.id) + " " + trade.market + " " +
                             trade.exchangeName + " " + str(e.args) +
                             " retrycntr:" + str(retrycntr))
                await asyncio.sleep(
                    self.exchanges[trade.exchangeNameStd].rateLimit / 1000)

    def fetch_order_statuses(self):
        tasks = []
        for _, trade in self.trades.items():
            tasks.append(asyncio.ensure_future(self.fetchOrderStatus(trade)))
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Order statuses fetching completed")

    async def fetch_balance(self, exchange):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                self.balance[exchange.name.lower().replace(
                    " ", "")] = await exchange.fetch_balance()
                logger.info('Balance fetching completed from ' + exchange.name)
                return
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error('Fetch balance failed from ' + exchange.name +
                             " " + type(error).__name__ + " " +
                             str(error.args) + " retrycntr:" + str(retrycntr))
                await asyncio.sleep(exchange.rateLimit / 1000)

    def fetch_balances(self):
        self.balance = {}
        tasks = []
        for _, exchange in self.exchanges.items():
            tasks.append(asyncio.ensure_future(self.fetch_balance(exchange)))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

    def get_free_balance(self, exchangeName, symbol) -> float:
        try:
            return float(self.balance[exchangeName][symbol]["free"])
        except Exception as e:
            logger.warning("No balance available from " + exchangeName + " " +
                           symbol + " " + str(e.args))
            return 0

    def get_exchange(self, exchange_name: str) -> Exchange:
        if exchange_name not in self.exchanges:
            raise ValueError(
                f'Exchange ({exchange_name}) does not exists in initialized exchanges'
            )
        return self.exchanges[exchange_name]

    def get_market(self, exchange_name: str,
                   market_str: str) -> Dict[str, Any]:
        exchange = self.get_exchange(exchange_name)
        if market_str not in exchange.markets:
            raise ValueError(
                f'Symbol ({market_str}) does not exists in exchange ({exchange_name})'
            )
        return exchange.markets[market_str]

    def get_min_trade_amount(self, exchange_name: str, market_str: str):
        market = self.get_market(exchange_name, market_str)
        return market['limits']['price']['min']

    def is_transaction_valid(self, exchange_name: str, market_str: str,
                             amount: float):
        exchange = self.get_exchange(exchange_name)
        market = self.get_market(exchange_name, market_str)
        if market['limits']['price']['min']:
            if amount < exchange.markets[market_str]['limits']['price']['min']:
                raise ValueError(
                    'Amount too small, won'
                    't execute on ' + exchange.name + " " + market_str +
                    " Amount: " + str(amount) + " Min.amount:" +
                    str(exchange.markets[market_str]['limits']['price']['min'])
                )

        if market['limits']['price']['max']:
            if amount > exchange.markets[market_str]['limits']['price']['max']:
                raise ValueError(
                    'Amount too big, won'
                    't execute on ' + exchange.name + " " + market_str +
                    " Amount: " + str(amount) + " Max.amount:" +
                    str(exchange.markets[market_str]['limits']['price']['max'])
                )

        if self.get_free_balance(exchange_name,
                                 market_str.split('/')[0]) < amount:
            raise ValueError(
                'Insufficient stock on ' + exchange.name + " " + market_str +
                " Amount available: " +
                str(self.get_free_balance(exchange_name, market_str)) +
                " Amount required:" + str(amount))

        return True

    def is_trade_valid(self, trade: Trade):
        return self.is_transaction_valid(trade.exchangeNameStd, trade.market,
                                         trade.amount)

    async def create_limit_order(self, trade: Trade):
        response = {}
        exchange = self.exchanges[trade.exchangeNameStd]
        symbol = trade.market
        amount = trade.amount
        price = trade.price
        tradetype = trade.trade_type
        try:
            if self.isSandboxMode == True:
                raise ValueError('trader sandbox mode ON')

            if tradetype == TradeType.BUY:
                response = await exchange.createLimitBuyOrder(
                    symbol, amount, price)
                logger.info("createLimitBuyOrder " + symbol + " Amount:" +
                            str(amount) + " Price:" + str(price) + " ID: " +
                            response['id'] + " created successfully")
            elif tradetype == TradeType.SELL:
                response = await exchange.createLimitSellOrder(
                    symbol, amount, price)
                logger.info("createLimitSellOrder " + symbol + " Amount:" +
                            str(amount) + " Price:" + str(price) + " ID: " +
                            response['id'] + " created successfully")
            else:
                raise ValueError('trade_type has an invalid value')

            trade.status = TradeStatus.CREATED
            trade.id = response['id']
            trade.errorlog = response['info']['error']
            self.trades[trade.id] = trade

            if 'info' in response:
                if 'error' in response['info']:
                    if response['info']['error']:
                        raise ValueError('Error in exchange response:' +
                                         str(response['error']))

        except Exception as error:
            logger.error('createLimitBuyOrder failed from ' + exchange.name +
                         " " + symbol + ": " + type(error).__name__ + " " +
                         str(error.args))
            raise OrderCreationError("Order creation failed: " +
                                     exchange.name + " " + symbol)

    def create_limit_orders(self, tradelist: List[Trade]):
        orders = []
        try:
            # Pre-check transactions
            for trade in tradelist:
                if trade.exchangeNameStd in self.exchanges.keys():
                    self.is_trade_valid(trade)
                else:
                    raise ValueError('Exchange ' + trade[0] +
                                     ' is not intialized')

            # Fire real transactions
            for trade in tradelist:
                orders.append(
                    asyncio.ensure_future(self.create_limit_order(trade)))

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(*orders))

        except Exception as e:
            logger.error("Arbitrage deal cannot be executed, " + str(e.args))
            traceback.print_exc()
            raise TradesShowstopper("Trade showstopper")

    def execute_trades(self, tradelist=[]):
        try:
            self.fetch_balances()
            self.create_limit_orders(tradelist)
            logger.info("Waiting for the trades to complete for " +
                        str(Trader.TTL_TRADEORDER_S) + "s")
            time.sleep(Trader.TTL_TRADEORDER_S)
        except Exception as e:
            logger.error("Trade stopped" + str(e.args))
        finally:
            self.fetch_order_statuses()
            self.cancelOpenTradeOrders()
            self.purgeClosedTradeOrders()
