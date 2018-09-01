#!/usr/bin/python

import sys, getopt
import asyncio
import ccxt.async_support as ccxt
import numpy as np
import matplotlib.pyplot as plt
import time
from OrderbookAnalyser import OrderbookAnalyser
from Trader import Trader
from threading import Condition, Thread
import datetime
from InitLogger import logger

async def pollOrderbook(exchange,symbols):
    i = 0    
    while True:    
        symbol = symbols[i % len(symbols)]
        try:
            yield (symbol, await exchange.fetch_order_book(symbol, limit=20))
        except (ccxt.ExchangeError, ccxt.NetworkError) as error:
            logger.error('Fetch orderbook from '+exchange.name+" "+symbol+": "+ type(error).__name__+" "+ str(error.args))

        i += 1
        await asyncio.sleep(exchange.rateLimit / 1000)

async def pollCoinmarketcap(cmc):
    while True:
        try:
            yield (await cmc.fetch_tickers())
        except (ccxt.ExchangeError, ccxt.NetworkError) as error:
            logger.error("Fetch tickers from coinmarketcap: "+ type(error).__name__+" "+ str(error.args))

        await asyncio.sleep(cmc.rateLimit / 1000)

async def coinmarketcapPoller(cmc,orderbookAnalyser):
    async for ticker in pollCoinmarketcap(cmc):
        logger.info("Received prices from coinmarketcap")
        orderbookAnalyser.updateCmcPrice(ticker)

async def exchangePoller(exchange,symbols,orderbookAnalyser,enablePlotting):
    id = 0
    async for (symbol, order_book) in pollOrderbook(exchange,symbols):
        logger.info("Received "+symbol+" from "+exchange.name)
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

def consumeArbTradeTriggerEvent(arbTradeTriggerEvent,arbTradeQueue,isSandboxMode):
    while True:
        arbTradeTriggerEvent.acquire()
        arbTradeTriggerEvent.wait()  # Blocks until an item is available for consumption.
        # do stuff with the trading queue
        with Trader(exchangeNames=["kraken"],credfile='./cred/api_trading.json',isSandboxMode=isSandboxMode) as trader:
            trader.executeTrades(arbTradeQueue.pop())

        arbTradeTriggerEvent.release()
        logger.info("Arbitrage trade trigger event consumed")

def main(argv):
    enablePlotting = True
    isSandboxMode = True

    resultsdir = './'
    try:
        opts, _ = getopt.getopt(argv,"nrl",["noplot","resultsdir=","live"])
    except getopt.GetoptError:
        logger.error('Invalid parameter. --noplot: suppress plots, --resultsdir=: output directory, --live:execute trades')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-n", "--noplot"):
            enablePlotting = False
        if opt in ("-r", "--resultsdir"):
            resultsdir = arg
        if opt in ("-l", "--live"):
            isSandboxMode = False

    if isSandboxMode:
        logger.info("Running in sandbox mode, TRADES WILL NOT BE EXECUTED")
    else:
        logger.info("Running in live mode, TRADES WILL BE EXECUTED")

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
    

    if enablePlotting:
        plt.figure(1)
        plt.plot(1,2)
        plt.ion()
        plt.show()
        plt.pause(0.001)


    arbTradeTriggerEvent = Condition()
    arbTradeQueue = []

    cmc = ccxt.coinmarketcap({'enableRateLimit': True})
    orderbookAnalyser = OrderbookAnalyser(
        vol_BTC=[1,0.1,0.01],
        edgeTTL=30,
        priceTTL=60,
        resultsdir=resultsdir,
        tradeLogFilename='tradelog_live.csv',
        priceSource=OrderbookAnalyser.PRICE_SOURCE_CMC,
        arbTradeTriggerEvent=arbTradeTriggerEvent,
        arbTradeQueue=arbTradeQueue)
    

    for exchange in exchanges.keys():
        asyncio.ensure_future(exchangePoller(exchanges[exchange],symbols[exchange],orderbookAnalyser,enablePlotting))
    
    asyncio.ensure_future(coinmarketcapPoller(cmc,orderbookAnalyser))
    
    def stop_loop():
        input('Press <enter> to stop')
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.get_event_loop()
    Thread(target=stop_loop).start()
    Thread(target=consumeArbTradeTriggerEvent, args=(arbTradeTriggerEvent,arbTradeQueue,isSandboxMode)).start()
    loop.run_forever()
    
    orderbookAnalyser.generateExportFilename(list(exchanges.keys()))
    orderbookAnalyser.save()
    logger.info("FrameworkLive exited normally. Bye.")
if __name__ == "__main__":
    main(sys.argv[1:])