import ast

class OrderBookPrice:
    def __init__(self,meanprice=None,limitprice=None,vol_BASE=None):
        self.meanprice = meanprice
        self.limitprice = limitprice 
        self.vol_BASE = vol_BASE
    def __str__(self):
        return "mean price:"+str(self.meanprice)+ ", " + "limit price:"+str(self.limitprice)

class OrderBook:
    def __init__(self,symbol,asks,bids):
        self.symbol = symbol
        if isinstance(asks, str):
            self.asks = list(ast.literal_eval(asks))
        else:
            self.asks = asks
        
        if isinstance(bids, str):
            self.bids = list(ast.literal_eval(bids))
        else:
            self.bids = bids

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.symbol == other.symbol and self.asks == other.asks and self.bids == other.bids

    def getPrice(self,orderbook,vol_total):
        vol_price = 0
        vol = vol_total

        if vol_total<=0:
            return OrderBookPrice()

        for entry in orderbook:
            entry_price = entry[0]
            entry_vol = entry[1]
            if vol >= entry_vol:
                vol_price += entry_vol*entry_price
                vol -= entry_vol
                if vol==0:
                    break
            else:
                vol_price += vol*entry_price
                vol = 0
                break
        if vol==0:
            return OrderBookPrice(meanprice=vol_price/vol_total, limitprice=entry_price,vol_BASE=vol_total)
        else:
            return OrderBookPrice()

    def getAskPrice(self,vol):
        return self.getPrice(self.asks,vol)

    def getBidPrice(self,vol):
        return self.getPrice(self.bids,vol)


if __name__ == "__main__":
    orderBook = OrderBook(
        symbol="BTC/USD",
        asks="[[7500, 1],[8000, 1]]",
        bids="[[7000, 1],[6500, 1]]")

    print("Ask:",orderBook.getAskPrice(1))
    print("Bid:",orderBook.getBidPrice(1))