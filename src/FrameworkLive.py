#!/usr/bin/python

import sys
import getopt
import asyncio
import aiohttp

import ccxt.async_support as ccxt
import numpy as np
import matplotlib.pyplot as plt
import time
from OrderbookAnalyser import OrderbookAnalyser
from Trader import Trader
from threading import Condition, Thread
import datetime
from InitLogger import logger
import json
from FWLiveParams import FWLiveParams


class FrameworkLive:
    def __init__(self, frameworklive_parameters):
        self.exchanges = {}
        self.symbols = {}
        self.parameters = frameworklive_parameters
        self.exchanges["poloniex"] = ccxt.poloniex({'enableRateLimit': True})
        self.exchanges["kraken"] = ccxt.kraken({'enableRateLimit': True})
        self.exchanges["coinfloor"] = ccxt.coinfloor({'enableRateLimit': True})
        self.exchanges["bitstamp"] = ccxt.bitstamp({'enableRateLimit': True})
        self.exchanges["gdax"] = ccxt.gdax({'enableRateLimit': True})
        self.exchanges["bittrex"] = ccxt.bittrex({'enableRateLimit': True})

        self.symbols['coinfloor'] = [
            'BTC/EUR', 'BTC/EUR', 'BCH/GBP', 'BTC/GBP', 'BTC/USD'
        ]
        self.symbols['kraken'] = [
            'BTC/USD', 'BTC/EUR', 'BTC/USD', 'BCH/USD', 'XRP/USD', 'LTC/EUR',
            'LTC/USD', 'ETH/BTC', 'BCH/BTC', 'XRP/BTC'
        ]
        self.symbols['bittrex'] = [
            'XRP/BTC', 'BTC/USD', 'BCH/BTC', 'BTC/USD', 'LTC/BTC', 'XRP/ETH',
            'BCH/ETH', 'ETH/BTC', 'LTC/ETH', 'BCH/USDT'
        ]
        self.symbols['gdax'] = [
            'BCH/BTC', 'BTC/EUR', 'LTC/EUR', 'BTC/USD', 'BTC/EUR', 'ETH/USD',
            'ETH/EUR', 'BCH/EUR', 'ETH/BTC', 'BCH/USD'
        ]
        self.symbols['bitstamp'] = [
            'BTC/EUR', 'ETH/BTC', 'BTC/USD', 'ETH/USD', 'BCH/EUR', 'BCH/BTC',
            'LTC/EUR', 'ETH/EUR', 'XRP/BTC', 'LTC/BTC'
        ]
        self.symbols['poloniex'] = [
            'BCH/BTC', 'XRP/BTC', 'LTC/BTC', 'ETH/BTC', 'BCH/ETH', 'ETC/BTC',
            'ETC/ETH', 'LSK/ETH', 'LSK/BTC', 'LTC/USDT'
        ]

        if self.parameters.enable_plotting is True:
            plt.figure(1)
            plt.plot(1, 2)
            plt.ion()
            plt.show()
            plt.pause(0.001)

        self.arbTradeTriggerEvent = Condition()
        self.arbTradeQueue = []

        self.cmc = ccxt.coinmarketcap({'enableRateLimit': True})
        self.orderbookAnalyser = OrderbookAnalyser(
            vol_BTC=[1],  # [1,0.1,0.01],
            edgeTTL=20,
            priceTTL=600,
            resultsdir=self.parameters.results_dir,
            tradeLogFilename='tradelog_live.csv',
            priceSource=OrderbookAnalyser.PRICE_SOURCE_CMC,
            arbTradeTriggerEvent=self.arbTradeTriggerEvent,
            arbTradeQueue=self.arbTradeQueue,
            neo4j_mode=self.parameters.neo4j_mode)

    async def pollOrderbook(self, exchange, symbols):
        i = 0
        while True:
            symbol = symbols[i % len(symbols)]
            try:
                yield (symbol, await exchange.fetch_order_book(
                    symbol, limit=20))
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error('Fetch orderbook from ' + exchange.name + " " +
                             symbol + ": " + type(error).__name__ + " " +
                             str(error.args))

            i += 1
            await asyncio.sleep(exchange.rateLimit / 1000)

    async def pollForex(self, symbols, authkey):
        i = 0
        while True:
            symbol = symbols[i % len(symbols)]
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                            url="https://api-fxpractice.oanda.com/v1/prices",
                            headers={'Authorization': ('Bearer ' + authkey)},
                            params='instruments=' + symbol) as resp:
                        yield (await resp.json())
            except Exception as error:
                logger.error("Fetch forex rates from Oanda: " +
                             type(error).__name__ + " " + str(error.args))
            i += 1
            await asyncio.sleep(1)

    async def forexPoller(self, symbols, authkey, orderbookAnalyser):
        async for ticker in self.pollForex(symbols=symbols, authkey=authkey):
            logger.info("Received " +
                        ticker['prices'][0]['instrument'].replace("_", "/") +
                        " prices from Oanda")
            orderbookAnalyser.updateForexPrice(ticker['prices'][0])

    async def pollCoinmarketcap(self, cmc):
        i = 0
        symbols = ['USD', 'BTC', 'ETH', 'EUR', 'GBP']
        while True:
            symbol_quote = symbols[i % len(symbols)]
            try:
                yield (await cmc.fetch_tickers(
                    symbol_quote, params={
                        "limit": 40,
                        "sort": "rank"
                    }))
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error("Fetch tickers from coinmarketcap: " + type(error).__name__ + " " + str(error.args))
            i += 1
            await asyncio.sleep(cmc.rateLimit / 1000)

    async def coinmarketcapPoller(self, cmc, orderbookAnalyser):
        async for ticker in self.pollCoinmarketcap(cmc):
            logger.info("Received prices from coinmarketcap")
            orderbookAnalyser.updateCoinmarketcapPrice(ticker)

    async def exchangePoller(self, exchange, symbols,
                             orderbookAnalyser: OrderbookAnalyser,
                             enablePlotting):
        id = 0
        async for (symbol, order_book) in self.pollOrderbook(
                exchange, symbols):
            logger.info("Received " + symbol + " from " + exchange.name)
            orderbookAnalyser.update(
                exchangename=exchange.name,
                symbol=symbol,
                bids=order_book['bids'],
                asks=order_book['asks'],
                id=id,
                timestamp=time.time())
            id += 1
            if enablePlotting:
                orderbookAnalyser.plotGraphs()

    def consumeArbTradeTriggerEvent(self, arbTradeTriggerEvent, arbTradeQueue,
                                    isSandboxMode):
        while True:
            arbTradeTriggerEvent.acquire()
            arbTradeTriggerEvent.wait(
            )  # Blocks until an item is available for consumption.
            # do stuff with the trading queue
            with Trader(
                    exchangeNames=["kraken"],
                    credfile='./cred/api_trading.json',
                    isSandboxMode=isSandboxMode) as trader:
                trader.execute_trades(arbTradeQueue.pop())

            arbTradeTriggerEvent.release()
            logger.info("Arbitrage trade trigger event consumed")

    def run(self):
        for exchange in self.exchanges.keys():
            asyncio.ensure_future(
                self.exchangePoller(
                    exchange=self.exchanges[exchange],
                    symbols=self.symbols[exchange],
                    orderbookAnalyser=self.orderbookAnalyser,
                    enablePlotting=self.parameters.enable_plotting))

        asyncio.ensure_future(
            self.coinmarketcapPoller(self.cmc, self.orderbookAnalyser))

        if self.parameters.is_forex_enabled is True:
            with open('./cred/oanda.json') as file:
                authkeys = json.load(file)
                asyncio.ensure_future(
                    self.forexPoller(
                        symbols=['EUR_USD', 'GBP_USD'],
                        authkey=authkeys['practice'],
                        orderbookAnalyser=self.orderbookAnalyser))

        def stop_loop():
            input('Press <enter> to stop')
            loop.call_soon_threadsafe(loop.stop)

        loop = asyncio.get_event_loop()
        Thread(target=stop_loop).start()
        Thread(
            target=self.consumeArbTradeTriggerEvent,
            args=(self.arbTradeTriggerEvent, self.arbTradeQueue,
                  self.parameters.is_sandbox_mode)).start()
        loop.run_forever()

        self.orderbookAnalyser.generateExportFilename(
            list(self.exchanges.keys()))
        self.orderbookAnalyser.save()
        logger.info("FrameworkLive exited normally. Bye.")


def main(argv):
    frameworklive_parameters = FWLiveParams()
    try:
        opts, _ = getopt.getopt(argv, "nrl",
                                ["noplot",
                                 "resultsdir=",
                                 "resultsdir=",
                                 "neo4jmode=",
                                 "live",
                                 "noforex"])
    except getopt.GetoptError:
        logger.error(
            'Invalid parameter(s) entered. List of valid parameters:\n'
            ' --noplot: suppress graph plots\n'
            ' --resultsdir=path: output directory\n'
            ' --live: trades are executed in live mode\n'
            ' --noforex: disable forex\n'
            ' --neo4jmode=local: connect to neo4j running on localhost\n'
            ' --neo4jmode=aws: connect to neo4j running in AWS\n'
        )
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-n", "--noplot"):
            frameworklive_parameters.enable_plotting = False
        if opt in ("-r", "--resultsdir"):
            frameworklive_parameters.results_dir = arg
        if opt in ("-r", "--neo4jmode"):
            if arg == 'local':
                frameworklive_parameters.neo4j_mode = FWLiveParams.neo4j_mode_localhost
            if arg == 'aws':
                frameworklive_parameters.neo4j_mode = FWLiveParams.neo4j_mode_aws_cloud
            if arg not in ['local', 'aws']:
                logger.error('Invalid neo4j mode in parameter')
                return

        if opt in ("-l", "--live"):
            frameworklive_parameters.is_sandbox_mode = False
        if opt in ("-l", "--noforex"):
            frameworklive_parameters.is_forex_enabled = False

    if frameworklive_parameters.is_sandbox_mode is True:
        logger.info("Running in sandbox mode, TRADES WILL NOT BE EXECUTED")
    else:
        logger.info("Running in live mode, TRADES WILL BE EXECUTED")

    frameworkLive = FrameworkLive(frameworklive_parameters)
    frameworkLive.run()


if __name__ == "__main__":
    main(sys.argv[1:])
