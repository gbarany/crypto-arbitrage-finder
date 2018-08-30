import asyncio
import json
import ccxt.async_support as ccxt
from InitLogger import *
from Trade import Trade
from TraderExceptions import OrderCreationError

 
class Trader:
    BUY_ORDER = "BUY_ORDER"
    SELL_ORDER = "SELL_ORDER"

    def __init__(self, exchangeNames=[],credfile='./cred/api.json',enableSandbox=True):
        self.keys = {}
        self.balance = {}
        self.credfile =  credfile
        self.enableSandbox = enableSandbox
        self.trades = {}
        with open(self.credfile) as file:
            self.keys = json.load(file)

        self.exchanges = {}
        tasks=[]
        for exchangeName in exchangeNames:
            tasks.append(asyncio.ensure_future(self.initExchange(exchangeName)))
        logger.info("Exchanges init started")
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Exchanges init completed")
    async def initExchange(self,exchangeName):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
        if self.enableSandbox == True:
            if 'test' in exchange.urls:
                exchange.urls['api'] = exchange.urls['test']
                await exchange.load_markets()
                self.exchanges[exchangeName.lower().replace(" ","")] = exchange
        else:
            await exchange.load_markets()
            self.exchanges[exchangeName.lower().replace(" ","")] = exchange

    async def closeExchange(self,exchange):
        await exchange.close()

    def closeExchanges(self):
        tasks=[]
        for _,exchange in self.exchanges.items():
            tasks.append(asyncio.ensure_future(self.closeExchange(exchange)))        
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Exchanges closed")

    async def fetchOrderStatus(self,trade):
        response=await trader.exchanges[trade.exchangeNameStd].fetchOrder(trade.id)
        trade.timestamp = response["timestamp"]
        trade.datetime = response["datetime"]
        trade.status = response["status"]
        trade.cost = response["cost"]
        trade.amount = response["amount"]
        trade.filled = response["filled"]
        trade.remaining = response["remaining"]
        self.trades[trade.id]=trade

    def fetchOrderStatuses(self):
        tasks=[]
        for _,trade in self.trades.items():
            tasks.append(asyncio.ensure_future(self.fetchOrderStatus(trade)))        
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Order statuses fetched")


    async def fetchBalance(self,exchange):
        try:
            self.balance[exchange.name.lower().replace(" ","")] = await exchange.fetch_balance()
        except (ccxt.ExchangeError, ccxt.NetworkError) as error:
            logger.error('Fetch balance from '+exchange.name+" "+type(error).__name__+" "+ str(error.args))

        #await exchange.close()
    
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

    def isTransactionValid(self,exchangeNameStd,symbol,amount):        
        exchange = self.exchanges[exchangeNameStd]
        if exchange.markets[symbol]['limits']['price']['min']:
            if amount<exchange.markets[symbol]['limits']['price']['min']:
                raise ValueError('Amount too small, won''t execute on '+exchange.name+" "+symbol+" Amount: "+str(amount)+
                " Min.amount:"+str(exchange.markets[symbol]['limits']['price']['min']))


        if exchange.markets[symbol]['limits']['price']['max']:
            if amount>exchange.markets[symbol]['limits']['price']['max']:
                raise ValueError('Amount too big, won''t execute on '+exchange.name+" "+symbol+" Amount: "+str(amount)+
                " Max.amount:"+str(exchange.markets[symbol]['limits']['price']['max']))

    async def createLimitOrder(self,trade):
        response={}
        exchange=self.exchanges[trade.exchangeNameStd]
        symbol=trade.symbol
        amount=trade.amount
        price=trade.price
        tradetype=trade.tradetype
        try:
            if tradetype==Trader.BUY_ORDER:
                response= await exchange.createLimitBuyOrder(symbol, amount,price)
                logger.info("createLimitBuyOrder "+symbol+" Amount:"+str(amount)+" Price:"+str(price)+" created successfully. "+str(response))
            elif tradetype==Trader.SELL_ORDER:
                response= await exchange.createLimitSellOrder(symbol, amount,price)
                logger.info("createLimitSellOrder "+symbol+" Amount:"+str(amount)+" Price:"+str(price)+" created successfully. "+str(response))
            else:
                raise ValueError('tradetype has an invalid value')
            trade.status = trade.STATUS_CREATED
            trade.id = response['id']
            trade.errorlog = response['info']['error']
            self.trades[trade.id] = trade
        except Exception as error:
            logger.error('createLimitBuyOrder failed from '+exchange.name+" "+symbol+": "+ type(error).__name__+" "+ str(error.args))
            raise OrderCreationError("Order creation failed"+exchange.name+" "+symbol)

    def createLimitOrders(self,tradelist):
        orders = []
        try:
            # Pre-check transactions
            for trade in tradelist:
                if trade.exchangeNameStd in self.exchanges.keys():
                    self.isTransactionValid(trade.exchangeNameStd,trade.symbol,trade.amount)
                else:
                    raise ValueError('exchange '+ trade[0] +' is not intialized')
            
            # Fire real transactions
            for trade in tradelist:
                orders.append(asyncio.ensure_future(self.createLimitOrder(trade)))

            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.gather(*orders))

        except OrderCreationError as e:
            # TODO: cancel all orders in the deal
            pass
        except Exception as e:
            logger.error("Arbitrage deal cannot be executed, "+str(e.args))

if __name__ == "__main__":
    trader = Trader(exchangeNames=["kraken"],credfile='./cred/api_trading.json',enableSandbox=False)
    trader.fetchBalances()
    logger.info("Free balance:"+str(trader.getFreeBalance("kraken","BTC")))
    tradelist = [
        Trade("kraken","BTC/USD",0.1,20000,Trader.SELL_ORDER),
        #("bitstamp","BTC/USD",0.0001)
        #("bitstamp","BTC/USD",0.0001)
    ]

    trader.createLimitOrders(tradelist)
    trader.fetchOrderStatuses()
    trader.closeExchanges()
    #print(stock.isSufficientStock("kraken","BTC",2))