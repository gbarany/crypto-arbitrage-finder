import asyncio
import json
import ccxt.async_support as ccxt
from InitLogger import *

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
        tasks=[]
        for exchangeName in self.exchangeNames:
            tasks.append(asyncio.ensure_future(self.fetchBalance(exchangeName)))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))
        
    def getFreeBalance(self,exchangeName,symbol):
        return float(self.balance[exchangeName][symbol]["free"])
    def isSufficientStock(self,exchangeName,symbol,requiredStock):
        return float(self.balance[exchangeName][symbol]["free"])>=requiredStock

    async def marketBuyOrder(self,exchangeName,symbol,amount):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
        response={}
        if exchange.has['createMarketOrder']:
            try:
                response= await exchange.createLimitBuyOrder(symbol, amount)
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error('creatingLimitBuyOrder failed from '+exchangeName+" "+symbol+": "+ type(error).__name__+" "+ str(error.args))
        else:
            logger.error("No market oder possible on "+exchangeName)
        await exchange.close()
        return response

    def marketBuyOrders(self,tradelist):
        orders = []
        for trade in tradelist:
            exchangeName = trade[0]
            symbol = trade[1]
            amount = trade[2]
            orders.append(asyncio.ensure_future(self.marketBuyOrder(exchangeName,symbol,amount)))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*orders))

if __name__ == "__main__":
    logger.info("hello world")
    trader = Trader(exchangeNames=["kraken","gdax","bitstamp"],credfile='./cred/api.json')
    trader.fetchBalances()
    logger.info("Free balance on GDAX:"+str(trader.getFreeBalance("gdax","BTC")))
    tradelist = [
        #("gdax","BTC/USD",0.0001),
        ("bitstamp","BTC/USD",0.0001)
    ]

    trader.marketBuyOrders(tradelist)

    #print(stock.isSufficientStock("kraken","BTC",2))