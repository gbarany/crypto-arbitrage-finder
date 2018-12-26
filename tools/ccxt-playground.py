import ccxt

exchange = ccxt.gdax({'enableRateLimit': True})
#exchange = ccxt.kraken({'enableRateLimit': True})
exchange.loadMarkets()
a=exchange.amountToPrecision('LTC/EUR', "6.143752931875697")
b=exchange.priceToPrecision('BTC/EUR', "0.0005")
print(a)
print(b)
#exchange.close()