import ccxt
import numbers

class ExchangeFeeStore:
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
        return self.numberOrZero(self.getExchange(exchangename).markets[symbols]['taker'])

    def getMakerFee(self,exchangename,symbols):
        return self.numberOrZero(self.getExchange(exchangename).markets[symbols]['maker'])

    def getFundingFee(self,exchangename,symbol):
        return self.numberOrZero(self.getExchange(exchangename).currencies[symbol]['fee'])

if __name__ == "__main__":
    exchangeFeeStore = ExchangeFeeStore()
    print("Taker",exchangeFeeStore.getTakerFee('poloniex','BTC/USDT'))
    print("Maker",exchangeFeeStore.getMakerFee('kraken','BTC/USD'))
    print("Funding",exchangeFeeStore.getFundingFee('kraken','BTC'))