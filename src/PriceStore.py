import ast
from InitLogger import logger
import dateutil.parser as dp

class PriceStore:
    def __init__(self,priceTTL=60):
        self.price = {}
        self.priceTTL = priceTTL
    
    def isOrderbookEmpty(self,ob):
        if len(ob)==0:
            return True
        else:
            if len(ob[0])==0:
                return True

        return False

    def updatePriceFromForex(self,forexTicker):
        symbolsplit = forexTicker['instrument'].split('_')
        symbol_base  = ('forex',symbolsplit[0])
        symbol_quote  = ('forex',symbolsplit[1])

        
        timestamp = int(dp.parse(forexTicker['time']).strftime('%s'))
        key1 = (symbol_quote,symbol_base)
        key2 = (symbol_base,symbol_quote)
        self.price[key1] = (timestamp,1/forexTicker['ask'])
        self.price[key2] = (timestamp,forexTicker['bid'])
                        


    def updatePriceFromCoinmarketcap(self,ticker):
        #self.price.clear()
        for symbol, tickeritem in ticker.items():
            try:
                symbolsplit = symbol.split('/')
                symbol_base  = ('coinmarketcap',symbolsplit[0])
                symbol_quote  = ('coinmarketcap',symbolsplit[1])
                price = tickeritem['last']
                timestamp = tickeritem['timestamp']
                if price != None:
                    if price>0:
                        key1 = (symbol_quote,symbol_base)
                        key2 = (symbol_base,symbol_quote)
                        self.price[key1] = (timestamp,1/price)
                        self.price[key2] = (timestamp,price)
                        
                        # convert price to BTC (from USD price)
                        key3 = (symbol_base,('coinmarketcap','BTC'))
                        key4 = (('coinmarketcap','BTC'),symbol_base)
                        self.price[key3] = price*1/ticker['BTC/'+symbol_quote[1]]['last']
                        self.price[key4] = 1/self.price[key3]
            except Exception as e:
                logger.error("Error occured parsing CMC ticker "+symbol+" "+str(e.args))

    def updatePriceFromOrderBook(self,symbol,exchangename,asks,bids,timestamp):
        self.symbol = symbol
        
        if isinstance(asks, str):
            asks = list(ast.literal_eval(asks))
        else:
            asks = asks
        
        if isinstance(bids, str):
            bids = list(ast.literal_eval(bids))
        else:
            bids = bids
        
        if self.isOrderbookEmpty(asks) or self.isOrderbookEmpty(bids):
            return
        
        price = (asks[0][0]+bids[0][0])/2

        symbolsplit = symbol.split('/')
        
        if len(symbolsplit)!=2:
            return

        symbol_base  = (exchangename,symbolsplit[0])
        symbol_quote  = (exchangename,symbolsplit[1])

        key1 = (symbol_quote,symbol_base)
        key2 = (symbol_base,symbol_quote)
        self.price[key1] = (timestamp,1/price)
        self.price[key2] = (timestamp,price)
    
    def getMeanPrice(self, symbol_base_ref,symbol_quote_ref,timestamp):
        acc = 0
        cntr = 0
        
        if symbol_base_ref == symbol_quote_ref:
            return 1

        for k, v in self.price.items():
            symbol_base = k[0][1]
            exchange_base = k[0][0]
            symbol_quote = k[1][1]
            exchange_quote = k[1][0]
            ts =  v[0]
            rate = v[1]

            if symbol_base_ref == symbol_base \
                and symbol_quote_ref == symbol_quote \
                and exchange_base == exchange_quote \
                and (timestamp-ts)<=self.priceTTL \
                and timestamp>ts:
                acc += rate
                cntr += 1
        if cntr != 0:
            return acc/cntr
        else:
            raise ValueError('Price information not available %s/%s timestamp %f'% (symbol_base_ref,symbol_quote_ref,timestamp))