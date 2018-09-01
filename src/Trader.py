import asyncio
import json
import ccxt.async_support as ccxt
from InitLogger import logger
from Trade import Trade
from TraderExceptions import OrderCreationError, TradesShowstopper
import time

class Trader:
    BUY_ORDER = "BUY_ORDER"
    SELL_ORDER = "SELL_ORDER"
    NOF_CCTX_RETRY = 4
    TTL_TRADEORDER_S = 10

    def __init__(self, exchangeNames=[],credfile='./cred/api.json',isSandboxMode=True):
        self.keys = {}
        self.balance = {}
        self.credfile =  credfile
        self.trades = {}
        self.isSandboxMode=isSandboxMode
        with open(self.credfile) as file:
            self.keys = json.load(file)

        self.exchanges = {}
        tasks=[]
        for exchangeName in exchangeNames:
            tasks.append(asyncio.ensure_future(self.initExchange(exchangeName)))
        logger.info("Exchanges init started")
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Exchanges init completed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closeExchanges()

    async def initExchange(self,exchangeName):
        exchange = getattr(ccxt, exchangeName)(self.keys[exchangeName])
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

    async def cancelTradeOrder(self,trade):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                response=await trader.exchanges[trade.exchangeNameStd].cancelOrder(trade.id)
                if response['error']:
                    raise ValueError('Error in exchange response:' + str(response['error']))
                logger.info('Cancelled trade oder '+trade.id+' on '+trade.exchangeNameStd)
                del self.trades[trade.id]
                return
            except Exception as e:
                logger.error('Trader order cancellation failed for ' + str(trade.id) + " "+trade.symbol + " "+trade.exchangeName + " "+str(e.args)+ " retrycntr:"+str(retrycntr))
                await asyncio.sleep(trader.exchanges[trade.exchangeNameStd].rateLimit / 1000)

    def cancelOpenTradeOrders(self):
        tasks=[]
        for _,trade in self.trades.items():
            if trade.status=='open':
                tasks.append(asyncio.ensure_future(self.cancelTradeOrder(trade)))        
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Cancellation of open trade orders completed")
    
    def purgeClosedTradeOrders(self):
        for _,trade in self.trades.items():
            if trade.status=='closed':
                del self.trades[trade.id]
        logger.info("Purging of closed trade orders completed")
        if bool(self.trades):
            logger.error("There are pending trades left after purging. Trades dump:"+json.dumps(self.trades))
        else:
            logger.info("Trades purged successfully")

    async def fetchOrderStatus(self,trade):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                response=await trader.exchanges[trade.exchangeNameStd].fetchOrder(trade.id)
                trade.timestamp = response["timestamp"]
                trade.datetime = response["datetime"]
                trade.status = response["status"]
                trade.cost = response["cost"]
                trade.amount = response["amount"]
                trade.filled = response["filled"]
                trade.remaining = response["remaining"]
                self.trades[trade.id]=trade
                logger.info('Order status fetched '+trade.id+' from '+trade.exchangeName)
                return
            except Exception as e:
                logger.error('Order status fetching failed for ' + str(trade.id) + " "+trade.symbol + " "+trade.exchangeName + " "+str(e.args)+ " retrycntr:"+str(retrycntr))
                await asyncio.sleep(trader.exchanges[trade.exchangeNameStd].rateLimit / 1000)

    def fetchOrderStatuses(self):
        tasks=[]
        for _,trade in self.trades.items():
            tasks.append(asyncio.ensure_future(self.fetchOrderStatus(trade)))        
        asyncio.get_event_loop().run_until_complete(asyncio.gather(*tasks))
        logger.info("Order statuses fetching completed")


    async def fetchBalance(self,exchange):
        for retrycntr in range(Trader.NOF_CCTX_RETRY):
            try:
                self.balance[exchange.name.lower().replace(" ","")] = await exchange.fetch_balance()
                logger.info('Balance fetching completed from '+exchange.name)
                return
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error('Fetch balance failed from '+exchange.name+" "+type(error).__name__+" "+ str(error.args) + " retrycntr:"+str(retrycntr))
                await asyncio.sleep(exchange.rateLimit / 1000)
    
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

        if self.getFreeBalance(exchangeNameStd,symbol.split('/')[0])<amount:
            raise ValueError('Insufficient stock on '+exchange.name+" "+symbol+" Amount available: "+str(self.getFreeBalance(exchangeNameStd,symbol))+
                " Amount required:"+str(amount))

        return True

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
                logger.info("createLimitBuyOrder "+symbol+" Amount:"+str(amount)+" Price:"+str(price)+" ID: "+ response['id'] +" created successfully")
            elif tradetype==Trader.SELL_ORDER:
                response= await exchange.createLimitSellOrder(symbol, amount,price)
                logger.info("createLimitSellOrder "+symbol+" Amount:"+str(amount)+" Price:"+str(price)+" ID: "+response['id']+" created successfully")
            else:
                raise ValueError('tradetype has an invalid value')

            trade.status = trade.STATUS_CREATED
            trade.id = response['id']
            trade.errorlog = response['info']['error']
            self.trades[trade.id] = trade

            if 'info' in response:
                if 'error' in response['info']:
                    if response['info']['error']:
                        raise ValueError('Error in exchange response:' + str(response['error']))

        except Exception as error:
            logger.error('createLimitBuyOrder failed from '+exchange.name+" "+symbol+": "+ type(error).__name__+" "+ str(error.args))
            raise OrderCreationError("Order creation failed"+exchange.name+" "+symbol)

    def createLimitOrders(self,tradelist):
        orders = []
        try:
            if self.isSandboxMode==True:
                raise ValueError('trader sandbox mode ON')
                
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

        except Exception as e:
            logger.error("Arbitrage deal cannot be executed, "+str(e.args))
            raise TradesShowstopper("Trade showstopper")

    def executeTrades(self,tradelist=[]):
        try:
            self.fetchBalances()
            self.createLimitOrders(tradelist)
            logger.info("Waiting for the trades to complete for "+str(Trader.TTL_TRADEORDER_S)+"s")
            time.sleep(Trader.TTL_TRADEORDER_S)
        except Exception as e:
            logger.error("Trade stopped" + str(e.args))
        finally:
            self.fetchOrderStatuses()
            self.cancelOpenTradeOrders()
            self.purgeClosedTradeOrders()


if __name__ == "__main__":

    with Trader(exchangeNames=["kraken"],credfile='./cred/api_trading.json') as trader:
        tradelist = [
            Trade("kraken","BTC/USD",0.1,20000,Trader.SELL_ORDER),
        ]
        trader.executeTrades(tradelist)
