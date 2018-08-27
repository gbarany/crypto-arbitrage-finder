import asyncio
import json

import ccxt.async_support as ccxt

class Trader:
    def __init__(self, exchangeNames=[],credfile='./cred/api.json'):
        self.exchangeNames =  exchangeNames
        self.credfile =  credfile
        self.balance = {}
        self.keys = {}
        with open(self.credfile) as file:
            self.keys = json.load(file)

    async def fetchBalance(self,exchangeName):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
        self.balance[exchangeName] = await exchange.fetch_balance()
        await exchange.close()
    
    def fetchBalances(self):
        self.balance = {}

        for exchangeName in self.exchangeNames:
            asyncio.ensure_future(self.fetchBalance(exchangeName))

        pending = asyncio.Task.all_tasks()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*pending))
        
    def getFreeBalance(self,exchangeName,symbol):
        return float(self.balance[exchangeName][symbol]["free"])
    def isSufficientStock(self,exchangeName,symbol,requiredStock):
        return float(self.balance[exchangeName][symbol]["free"])>=requiredStock

    async def marketBuyOrder(self,exchangeName,symbol,amount):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
        if exchange.has['createMarketOrder']:
            try:
                response= await exchange.createLimitBuyOrder(symbol, amount)
            except Exception as e:
                print('Failed to create order with', exchange.id, type(e).__name__, str(e))
        else:
            print("No market oder possible on",exchangeName)
        await exchange.close()
        return response

    def marketBuyOrders(self,tradelist):
        for trade in tradelist:
            exchangeName = trade[0]
            symbol = trade[1]
            amount = trade[2]
            asyncio.ensure_future(self.marketBuyOrder(exchangeName,symbol,amount))

        pending = asyncio.Task.all_tasks()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*pending))

if __name__ == "__main__":
    trader = Trader(exchangeNames=["kraken","gdax","bitstamp"],credfile='./cred/api.json')
    #trader.fetchBalances()
    #print(trader.getFreeBalance("kraken","BTC"))
    tradelist = [
        ("kraken","BTC",0.0001)
    ]

    trader.marketBuyOrders(tradelist)

    #print(stock.isSufficientStock("kraken","BTC",2))