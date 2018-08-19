import ast

class PriceStore:
    def __init__(self,priceTTL=5):
        self.price = {}
        self.priceTTL = 60
    
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
        price = (asks[0][0]+bids[0][0])/2
        symbol_base  = (exchangename,symbol.split('/')[0])
        symbol_quote  = (exchangename,symbol.split('/')[1])

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
                and (timestamp-ts)<=self.priceTTL:
                acc += rate
                cntr += 1
        if cntr != 0:
            return acc/cntr
        else:
            return None