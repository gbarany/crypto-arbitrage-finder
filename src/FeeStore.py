import ccxt
import numbers
import logging

logger = logging.getLogger('CryptoArbitrageApp')

class FeeStore:

    DEFAULT_TAKER_FEE = 0.003
    DEFAULT_MAKER_FEE = 0.0026

    def __init__(self):
        self.exchanges = {}

    def getExchange(self, exchangename):
        if exchangename in self.exchanges:
            return self.exchanges[exchangename]
        else:
            self.exchanges[exchangename] = getattr(ccxt, exchangename)()
            self.exchanges[exchangename].load_markets()
            return self.exchanges[exchangename]

    def numberOrZero(self, x):
        if isinstance(x, numbers.Number):
            return x
        else:
            return FeeStore.DEFAULT_TAKER_FEE

    def getTakerFee(self, exchangename, symbols):
        if exchangename == 'oanda': # TODO: refactor
            return 0.0
        elif exchangename == 'sfox': # TODO: refactor
            return 0.003

        try:
            return self.numberOrZero(
                self.getExchange(
                    exchangename.lower()).markets[symbols]['taker'])
        except Exception as e:
            logger.warning("Couldn't fetch taker fee from " + exchangename + " "+ symbols +" , defaulting to " + str(FeeStore.DEFAULT_TAKER_FEE) + " " + str(e.args))
            return FeeStore.DEFAULT_TAKER_FEE

    def getMakerFee(self, exchangename, symbols):
        if exchangename == 'oanda': # TODO: refactor
            return 0.0
        elif exchangename == 'sfox': # TODO: refactor
            return 0.003

        try:
            return self.numberOrZero(
                self.getExchange(
                    exchangename.lower()).markets[symbols]['maker'])
        except Exception as e:
            logger.warn("Couldn't fetch maker fee from " + exchangename + " "+ symbols +" , defaulting to " + str(FeeStore.DEFAULT_MAKER_FEE) + " " + str(e.args))
            return FeeStore.DEFAULT_MAKER_FEE