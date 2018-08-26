#!/usr/bin/python

import sys, getopt
import asyncio
import ccxt.async_support as ccxt
import numpy as np
import matplotlib.pyplot as plt
import time
from OrderbookAnalyser import OrderbookAnalyser
import threading
import datetime


async def pollOrderbook(exchange,symbols):
    i = 0    
    while True:
        symbol = symbols[i % len(symbols)]
        yield (symbol, await exchange.fetch_order_book(symbol, limit=20))
        i += 1
        await asyncio.sleep(exchange.rateLimit / 1000)

async def pollCoinmarketcap(cmc):
    while True:
        yield (await cmc.fetch_tickers())
        await asyncio.sleep(cmc.rateLimit / 1000)

async def coinmarketcapPoller(cmc):
    #await cmc.load_markets()
    async for ticker in pollCoinmarketcap(cmc):
        print(datetime.datetime.now(), "Received prices from coinmarketcap (BTC/USD",ticker['BTC/USD']['last'],')')

async def exchangePoller(exchange,symbols,orderbookAnalyser,enablePlotting):
    id = 0
    async for (symbol, order_book) in pollOrderbook(exchange,symbols):
        print(datetime.datetime.now(), "Received",symbol, "from",exchange.name)
        orderbookAnalyser.update(
                exchangename=exchange.name,
                symbol = symbol,
                bids = order_book['bids'],
                asks = order_book['asks'],
                id = id,
                timestamp = time.time()
                )
        id += 1
        if enablePlotting:
            orderbookAnalyser.plot_graphs()


def main(argv):
    enablePlotting = True
    resultsdir = './'
    try:
        opts, _ = getopt.getopt(argv,"nr",["noplot","resultsdir="])
    except getopt.GetoptError:
        print('Invalid parameter. Use --noplot to suppress plots')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-n", "--noplot"):
            enablePlotting = False
        if opt in ("-r", "--resultsdir"):
            resultsdir = arg

    if enablePlotting:
        plt.figure(1)
        plt.plot(1,2)
        plt.ion()
        plt.show()
        plt.pause(0.001)

    exchanges = {}
    symbols = {}
    
    exchanges["Poloniex"]=ccxt.poloniex({'enableRateLimit': True})
    exchanges["Kraken"]=ccxt.kraken({'enableRateLimit': True})
    exchanges["coinfloor"]=ccxt.coinfloor({'enableRateLimit': True})
    exchanges["Bitstamp"]=ccxt.bitstamp({'enableRateLimit': True})
    exchanges["Gdax"]=ccxt.gdax({'enableRateLimit': True})
    exchanges["Bittrex"]=ccxt.bittrex({'enableRateLimit': True})

    symbols['coinfloor'] =['BTC/EUR','BTC/EUR','BCH/GBP','BTC/GBP','BTC/USD']
    symbols['Kraken'] =['BTC/USD','BTC/EUR','BTC/USD','BCH/USD','XRP/USD','LTC/EUR','LTC/USD','ETH/BTC','BCH/BTC','XRP/BTC']
    symbols['Bittrex'] =['XRP/BTC','BTC/USD','BCH/BTC','BTC/USD','LTC/BTC','XRP/ETH','BCH/ETH','ETH/BTC','LTC/ETH','BCH/USDT']
    symbols['Gdax'] =['BCH/BTC','BTC/EUR','LTC/EUR','BTC/USD','BTC/EUR','ETH/USD','ETH/EUR','BCH/EUR','ETH/BTC','BCH/USD']
    symbols['Bitstamp'] =['BTC/EUR','ETH/BTC','BTC/USD','ETH/USD','BCH/EUR','BCH/BTC','LTC/EUR','ETH/EUR','XRP/BTC','LTC/BTC']
    symbols['Poloniex'] =['BCH/BTC','XRP/BTC','LTC/BTC','ETH/BTC','BCH/ETH','ETC/BTC','ETC/ETH','LSK/ETH','LSK/BTC','LTC/USDT']

    cmc = ccxt.coinmarketcap({'enableRateLimit': True})
    orderbookAnalyser = OrderbookAnalyser(
        vol_BTC=[1,0.1,0.01],
        edgeTTL=30,
        priceTTL=60,
        resultsdir=resultsdir,
        tradeLogFilename='tradelog_live.csv')
    

    for exchange in exchanges.keys():
        asyncio.ensure_future(exchangePoller(exchanges[exchange],symbols[exchange],orderbookAnalyser,enablePlotting))
    
    asyncio.ensure_future(coinmarketcapPoller(cmc))
    
    def stop_loop():
        input('Press <enter> to stop')
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.get_event_loop()
    threading.Thread(target=stop_loop).start()
    loop.run_forever()
    
    orderbookAnalyser.generateExportFilename(list(exchanges.keys()))
    orderbookAnalyser.save()
    for _, exchange in exchanges.items():
        exchange.close()

if __name__ == "__main__":
    main(sys.argv[1:])