import dill

filename ='./results/arbitrage_Vol=1BTC-0.1BTC-0.01BTC_XC=Poloniex-Bitfinex-Kraken-coinfloor-Bitstamp-Gdax.pkl'

with open(filename, 'rb') as f:
    orderbookAnalyser = dill.load(f)
orderbookAnalyser.plot_graphs()

input('Hit enter to continue')