import ast


class OrderBookPrice:
    def __init__(self, meanprice=None, limitprice=None, vol_BASE=None):
        self.meanprice = meanprice
        self.limitprice = limitprice
        self.vol_BASE = vol_BASE

    def __str__(self):
        return "mean price:" + str(
            self.meanprice) + ", " + "limit price:" + str(self.limitprice)


class OrderBook:
    def __init__(self, symbol, asks, bids, rate_BTC_to_base=None):
        self.symbol = symbol
        if isinstance(asks, str):
            self.asks = list(ast.literal_eval(asks))
        else:
            self.asks = asks

        if isinstance(bids, str):
            self.bids = list(ast.literal_eval(bids))
        else:
            self.bids = bids

        self.rate_BTC_to_base = rate_BTC_to_base

    def __eq__(self, other):
        return isinstance(
            other, self.__class__
        ) and self.symbol == other.symbol and self.asks == other.asks and self.bids == other.bids

    def getPrice(self, orderbook, vol_total):
        vol_price = 0
        vol = vol_total

        if vol_total <= 0:
            return OrderBookPrice()

        for entry in orderbook:
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
                meanprice=vol_price / vol_total,
                limitprice=entry_price,
                vol_BASE=vol_total)
        else:
            return OrderBookPrice()

    def getAskPrice(self, vol):
        return self.getPrice(self.asks, vol)

    def get_ask_price_by_BTC_volume(self, vol_BTC):
        return self.getPrice(self.asks, vol_BTC*self.rate_BTC_to_base)

    def getBidPrice(self, vol):
        return self.getPrice(self.bids, vol)

    def get_bid_price_by_BTC_volume(self, vol_BTC):
        return self.getPrice(self.bids, vol_BTC*self.rate_BTC_to_base)

    @staticmethod
    def convert_nested_list_to_str(list):
        return '['+','.join(['['+str(pair[0])+','+str(pair[1])+']' for pair in list])+']'

    @staticmethod
    def flip_nested_list(list):
        return [[lst[1], lst[0]] for lst in list]

    def get_asks_str(self):
        return OrderBook.convert_nested_list_to_str(self.asks)

    def get_asks_in_base_str(self):
        return OrderBook.convert_nested_list_to_str(OrderBook.flip_nested_list(self.asks))

    def get_bids_str(self):
        return OrderBook.convert_nested_list_to_str(self.bids)

    def get_bids_in_base_str(self):
        return OrderBook.convert_nested_list_to_str(OrderBook.flip_nested_list(self.bids))


if __name__ == "__main__":
    orderBook = OrderBook(
        symbol="BTC/USD",
        asks="[[7500, 1],[8000, 1]]",
        bids="[[7000, 1],[6500, 1]]")

    print("Ask:", orderBook.getAskPrice(1))
    print("Bid:", orderBook.getBidPrice(1))
