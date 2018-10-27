import ast
import copy
import numpy as np

class Asset:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol

    def getExchange(self):
        return self.exchange

    def getSymbol(self):
        return self.symbol

class OrderBookPrice:
    def __init__(self, timestamp=None,meanPrice=None, limitPrice=None, volumeBase=None,volumeBTC=None,volumeQuote=None,feeRate=None,timeToLive=None): 
        self.timestamp = timestamp
        self.meanPrice = meanPrice
        self.timeToLive = timeToLive
        if meanPrice is not None and feeRate is not None:
            self.meanPriceNet = meanPrice*(1-feeRate)
        else:
            self.meanPriceNet = None

        self.limitPrice = limitPrice
        self.feeRate = feeRate

        if volumeBase is not None and feeRate is not None:
            self.feeAmountBase=volumeBase*feeRate
        else:
            self.feeAmountBase = None


        if volumeBTC is not None and feeRate is not None:
            self.feeAmountBTC=volumeBTC*feeRate
        else:
            self.feeAmountBTC = None
        self.volumeBase = volumeBase
        self.volumeQuote = volumeQuote
        self.volumeBTC = volumeBTC

    def __str__(self):
        return "mean price:" + str(self.meanPrice) + ", " + "limit price:" + str(self.limitPrice)

    def getLogPrice(self):
        return -1.0 * np.log(self.meanPriceNet)
    
    def getPrice(self):
        return self.meanPriceNet
    
    def getLimitPrice(self):
        return self.limitPrice
    
    def getVolumeQuote(self):
        return self.volumeQuote
    
    def getVolumeBase(self):
        return self.volumeBase

class OrderBookPair:
    def __init__(self,timestamp,symbol,exchange,asks,bids,rateBTCxBase,rateBTCxQuote,feeRate,timeToLiveSec):
            self.bids = OrderBook(timestamp=timestamp,symbol=symbol,exchange=exchange,orderbook=bids,rateBTCxBase=rateBTCxBase,rateBTCxQuote=rateBTCxQuote,feeRate=feeRate,timeToLiveSec=timeToLiveSec)
            self.asks = OrderBook(timestamp=timestamp,symbol=symbol,exchange=exchange,orderbook=asks,rateBTCxBase=rateBTCxBase,rateBTCxQuote=rateBTCxQuote,feeRate=feeRate,timeToLiveSec=timeToLiveSec)
            self.exchange = exchange
            self.symbol = symbol
            self.timestamp = timestamp
            self.timeToLiveSec = timeToLiveSec
    def getBidsOrderbook(self):
        return self.bids

    def getAsksOrderbook(self):
        return self.asks

    def getRebasedAsksOrderbook(self):
        return self.asks.getRebasedOrderbook()

    def getSymbolBase(self):
        return self.symbol.split('/')[0]
        
    def getSymbolQuote(self):
        return self.symbol.split('/')[1]

    def getExchange(self):
        return self.exchange
    
    def getTimestamp(self):
        return self.timestamp

class OrderBook:
    def __init__(self, timestamp, symbol, exchange,orderbook, rateBTCxBase, rateBTCxQuote,feeRate,timeToLiveSec):
        self.timestamp = timestamp
        self.symbol = symbol
        self.exchange = exchange
        if isinstance(orderbook, str):
            self.orderbook = list(ast.literal_eval(orderbook))
        else:
            self.orderbook = orderbook

        self.rateBTCxBase = rateBTCxBase
        self.rateBTCxQuote = rateBTCxQuote
        self.feeRate = feeRate
        self.timeToLiveSec = timeToLiveSec

        self.baseAsset = Asset(exchange=exchange, symbol=symbol.split('/')[0])
        self.quoteAsset = Asset(exchange=exchange, symbol=symbol.split('/')[1])

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.symbol == other.symbol and self.orderbook == other.orderbook

    def getBaseAsset(self):
        return self.baseAsset

    def getTimestamp(self):
        return self.timestamp

    def getQuoteAsset(self):
        return self.quoteAsset

    def getSymbolBase(self):
        return self.baseAsset.symbol
        
    def getSymbolQuote(self):
        return self.quoteAsset.symbol

    def getPrice(self, volumeBase):
        vol_price = 0
        vol = volumeBase

        if volumeBase <= 0:
            return OrderBookPrice()

        for entry in self.orderbook:
            entry_price = entry[0]
            entry_vol = entry[1]
            if vol >= entry_vol:
                vol_price += entry_vol * entry_price
                vol -= entry_vol
                if vol == 0:
                    break
            else:
                vol_price += vol * entry_price
                vol = 0
                break
        if vol == 0:
            return OrderBookPrice(
                timestamp=self.timestamp,
                meanPrice=vol_price / volumeBase,
                limitPrice=entry_price,
                volumeBase=volumeBase,
                volumeBTC=volumeBase/self.rateBTCxBase,
                volumeQuote=volumeBase/self.rateBTCxBase*self.rateBTCxQuote,
                feeRate=self.feeRate,
                timeToLive=self.timeToLiveSec)
        else:
            return OrderBookPrice()


    def getPriceByBTCVolume(self, volumeBTC):
        return self.getPrice(volumeBTC*self.rateBTCxBase)


    @staticmethod
    def convertNestedListToStr(list):
        return '['+','.join(['['+str(pair[0])+','+str(pair[1])+']' for pair in list])+']'

    def getOrderbookStr(self):
        return OrderBook.convertNestedListToStr(self.orderbook)

    def getRebasedOrderbook(self):
        newobj = copy.copy(self)
        # flip symbols
        symbols = newobj.symbol.split('/')
        newobj.symbol = symbols[1]+'/'+symbols[0]
        # flip assets
        newobj.baseAsset = Asset(exchange=self.exchange, symbol=symbols[1])
        newobj.quoteAsset = Asset(exchange=self.exchange, symbol=symbols[0])

        # flip orderbook
        newobj.orderbook = [[1/lst[0], lst[0]*lst[1]] for lst in self.orderbook]


        # adjust base conversion
        newobj.rateBTCxBase = self.rateBTCxQuote
        newobj.rateBTCxQuote = self.rateBTCxBase
        return newobj

