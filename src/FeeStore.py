import ccxt
import numbers

class FeeStore:
    def __init__(self):
        self.exchanges = {}

    def getExchange(self,exchangename):
        if exchangename in self.exchanges:
            return self.exchanges[exchangename]
        else:
            self.exchanges[exchangename] = getattr(ccxt, exchangename)()
            self.exchanges[exchangename].load_markets()
            return self.exchanges[exchangename]
    
    def numberOrZero(self,x):
        if isinstance(x, numbers.Number):
            return x
        else:
            return 0

    def getTakerFee(self,exchangename,symbols):
        #return self.numberOrZero(self.getExchange(exchangename).markets[symbols]['taker'])
        return 0.003 # TODO: add fee calculation lookup table

    def getMakerFee(self,exchangename,symbols):
        #return self.numberOrZero(self.getExchange(exchangename).markets[symbols]['maker'])
        return 0.0026 # TODO: add fee calculation lookup table
    def getFundingFee(self,exchangename,symbol):
        #return self.numberOrZero(self.getExchange(exchangename).currencies[symbol]['fee'])
        return 0 # TODO: add fee calculation lookup table

if __name__ == "__main__":
    exchangeFeeStore = FeeStore()
    print("Taker",exchangeFeeStore.getTakerFee('poloniex','BTC/USDT'))
    print("Maker",exchangeFeeStore.getMakerFee('kraken','BTC/USD'))
    print("Funding",exchangeFeeStore.getFundingFee('kraken','BTC'))