import ast

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

    def getPrice(self,orderbook,vol_total):
        vol_price = 0
        vol = vol_total

        if vol_total<=0:
            return None

        for entry in orderbook:
            entry_price = entry[0]
            entry_vol = entry[1]
            if vol >= entry_vol:
                vol_price += entry_vol*entry_price
                vol -= entry_vol
            else:
                vol_price += vol*entry_price
                vol = 0
                break
        if vol==0:
            return vol_price/vol_total
        else:
            return None

    def getAskPrice(self,vol):
        return self.getPrice(self.asks,vol)

    def getBidPrice(self,vol):
        return self.getPrice(self.bids,vol)


if __name__ == "__main__":
    orderBook = OrderBook(
        symbol="BTC/USD",
        asks="[[7500, 1],[8000, 1]]",
        bids="[[7000, 1],[6500, 1]]")

    print("Ask price",orderBook.getAskPrice(0.5))
    print("Bid price",orderBook.getBidPrice(0.5))