import ast
import copy

class OrderBookPrice:
    def __init__(self, meanPrice=None, limitPrice=None, volumeBase=None,volumeBTC=None,feeRate=None):        
        self.meanPrice = meanPrice

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
        self.volumeBTC = volumeBTC

    def __str__(self):
        return "mean price:" + str(
            self.meanPrice) + ", " + "limit price:" + str(self.limitPrice)

class OrderBookPair:
    def __init__(self,symbol,asks,bids,rateBTCxBase,rateBTCxQuote,feeRate):
            self.bids = OrderBook(symbol=symbol,orderbook=bids,rateBTCxBase=rateBTCxBase,rateBTCxQuote=rateBTCxQuote,feeRate=feeRate)
            self.asks = OrderBook(symbol=symbol,orderbook=asks,rateBTCxBase=rateBTCxBase,rateBTCxQuote=rateBTCxQuote,feeRate=feeRate)

    def getBidsOrderbook(self):
        return self.bids

    def getAsksOrderbook(self):
        return self.asks

    def getRebasedAsksOrderbook(self):
        return self.asks.getRebasedOrderbook()

class OrderBook:
    def __init__(self, symbol, orderbook, rateBTCxBase, rateBTCxQuote,feeRate):
        self.symbol = symbol
        if isinstance(orderbook, str):
            self.orderbook = list(ast.literal_eval(orderbook))
        else:
            self.orderbook = orderbook

        self.rateBTCxBase = rateBTCxBase
        self.rateBTCxQuote = rateBTCxQuote
        self.feeRate = feeRate
    def __eq__(self, other):
        return isinstance(
            other, self.__class__
        ) and self.symbol == other.symbol and self.orderbook == other.orderbook

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
                meanPrice=vol_price / volumeBase,
                limitPrice=entry_price,
                volumeBase=volumeBase,
                volumeBTC=volumeBase/self.rateBTCxBase,
                feeRate=self.feeRate)
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
        # flip orderbook
        newobj.orderbook = [[1/lst[0], lst[0]*lst[1]] for lst in self.orderbook]
        
        # adjust base conversion
        newobj.rateBTCxBase = self.rateBTCxQuote
        newobj.rateBTCxQuote = self.rateBTCxBase
        return newobj

