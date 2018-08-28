import asyncio
import json
import ccxt.async_support as ccxt
from InitLogger import *

class Trader:
    def __init__(self, exchangeNames=[],credfile='./cred/api.json',enableSandbox=True):
        self.keys = {}
        self.balance = {}
        self.credfile =  credfile
        self.enableSandbox = enableSandbox

        with open(self.credfile) as file:
            self.keys = json.load(file)

        self.exchanges = {}
        tasks=[]
        for exchangeName in exchangeNames:
            tasks.append(asyncio.ensure_future(self.initExchange(exchangeName)))
        
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))

    async def initExchange(self,exchangeName):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
        if self.enableSandbox == True:
            if 'test' in exchange.urls:
                exchange.urls['api'] = exchange.urls['test']
                await exchange.load_markets()
                self.exchanges[exchangeName.lower()] = exchange
        else:
            exchange.load_markets()
            self.exchanges[exchangeName.lower()] = exchange


    async def fetchBalance(self,exchange):
        try:
            self.balance[exchange.name.lower()] = await exchange.fetch_balance()
        except (ccxt.ExchangeError, ccxt.NetworkError) as error:
            logger.error('Fetch balance from '+exchange.name+" "+type(error).__name__+" "+ str(error.args))

        await exchange.close()
    
    def fetchBalances(self):
        self.balance = {}
        tasks=[]
        for _, exchange in self.exchanges.items():
            tasks.append(asyncio.ensure_future(self.fetchBalance(exchange)))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))
        
    def getFreeBalance(self,exchangeName,symbol):
        try:
            return float(self.balance[exchangeName][symbol]["free"])
        except Exception as e:
            logger.warning("No balance available from "+exchangeName+" "+symbol+" "+str(e.args))
            return None

    def isSufficientStock(self,exchange,symbol,requiredStock):
        return self.getFreeBalance(exchange,symbol)>=requiredStock

    def isTransactionValid(self,exchange,symbol,amount):        
        if exchange.markets[symbol]['limits']['price']['min']:
            if amount<exchange.markets[symbol]['limits']['price']['min']:
                logger.warning('Amount too small, won''t execute on '+exchange.name+" "+symbol+" Amount: "+str(amount))
                return False

        if exchange.markets[symbol]['limits']['price']['max']:
            if amount>exchange.markets[symbol]['limits']['price']['max']:
                logger.warning('Amount too big, won''t execute on '+exchange.name+" "+symbol+" Amount: "+str(amount))
                return False
        
        return True

    async def marketBuyOrder(self,exchange,symbol,amount):
        response={}

        if exchange.has['createMarketOrder']:
            try:
                response= await exchange.createMarketBuyOrder(symbol, amount)
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error('createMarketBuyOrder failed from '+exchange.name+" "+symbol+": "+ type(error).__name__+" "+ str(error.args))
            #except Exception as error:
            #    logger.error('createMarketBuyOrder failed from '+exchange.name+" "+symbol+": "+ type(error).__name__+" "+ str(error.args))
        else:
            logger.error("No market oder possible on "+exchange.name)
        await exchange.close()
        return response

    def marketBuyOrders(self,tradelist):
        orders = []
        
        allTransactionsValid = True
        for trade in tradelist:
            exchange = self.exchanges[trade[0]]
            symbol = trade[1]
            amount = trade[2]
            allTransactionsValid = (allTransactionsValid and self.isTransactionValid(exchange,symbol,amount))

        if not allTransactionsValid:
            logger.warn("Arbitrage deal cannot be executed as at least one transaction is invalid")
            return
        
        for trade in tradelist:
            exchange = self.exchanges[trade[0].lower()]
            symbol = trade[1]
            amount = trade[2]
            orders.append(asyncio.ensure_future(self.marketBuyOrder(exchange,symbol,amount)))

        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*orders))

if __name__ == "__main__":
    logger.info("Trader start")
    trader = Trader(exchangeNames=["gdax"],credfile='./cred/api_sandbox.json',enableSandbox=True)
    #trader = Trader(exchangeNames=["kraken","gdax","bitstamp"],credfile='./cred/api_sandbox.json',enableSandbox=True)
    trader.fetchBalances()
    logger.info("Free balance on GDAX:"+str(trader.getFreeBalance("gdax","BTC")))
    tradelist = [
        ("gdax","BTC/USD",0.01),
        #("bitstamp","BTC/USD",0.0001)
        #("bitstamp","BTC/USD",0.0001)
    ]

    trader.marketBuyOrders(tradelist)

    #print(stock.isSufficientStock("kraken","BTC",2))