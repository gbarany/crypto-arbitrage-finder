#!/usr/bin/python

import sys
import signal
import getopt
import asyncio
import aiohttp

import ccxt.async_support as ccxt
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import time
from OrderbookAnalyser import OrderbookAnalyser
from Trader import Trader
from threading import Condition, Thread
import datetime
from InitLogger import logger
import json
from FWLiveParams import FWLiveParams
import ptvsd
from aiokafka import AIOKafkaConsumer
import logging

logger = logging.getLogger('CryptoArbitrageApp')

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
        self.trader = Trader(is_sandbox_mode=frameworklive_parameters.is_sandbox_mode)
        

        kafkaCredentials=self.parameters.getKafkaProducerCredentials()
        self.orderbookAnalyser = OrderbookAnalyser(
            vol_BTC=[0.05], # TODO : this should be conigurable
            edgeTTL=15,
            priceTTL=600,
            resultsdir=self.parameters.results_dir,
            priceSource=OrderbookAnalyser.PRICE_SOURCE_CMC,
            trader=self.trader,
            neo4j_mode=self.parameters.neo4j_mode,
            dealfinder_mode=self.parameters.dealfinder_mode,
            kafkaCredentials=kafkaCredentials)

    async def pollOrderbook(self, exchange, symbols):
        i = 0
        while True:
            symbol = symbols[i % len(symbols)]
            try:
                yield (symbol, await exchange.fetch_order_book(
                    symbol, limit=20))
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                logger.error('Fetch orderbook network/exchange error ' + exchange.name + " " + symbol + ": " + type(error).__name__ + " " + str(error.args))
            except Exception as error:
                logger.error('Fetch orderbook error ' + exchange.name + " " + symbol + ": " + type(error).__name__ + " " + str(error.args))

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
                logger.error("Fetch forex rates from Oanda: " + type(error).__name__ + " " + str(error.args))
                
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
                logger.error("Fetch tickers from coinmarketcap network/exchange error: " + type(error).__name__ + " " + str(error.args))
            except Exception as error:
                logger.error("Fetch tickers from coinmarketcap generic exception: " + type(error).__name__ + " " + str(error.args))

            i += 1
            await asyncio.sleep(cmc.rateLimit / 1000)

    async def coinmarketcapPoller(self, cmc, orderbookAnalyser):
        async for ticker in self.pollCoinmarketcap(cmc):
            logger.info("Received prices from coinmarketcap")
            orderbookAnalyser.updateCoinmarketcapPrice(ticker)

    async def exchangePoller(self, exchange, symbols,orderbookAnalyser: OrderbookAnalyser,enablePlotting):
        async for (symbol, order_book) in self.pollOrderbook(exchange, symbols):
            logger.info("Received " + symbol + " from " + exchange.name)
            orderbookAnalyser.update(
                exchangename=exchange.name,
                symbol=symbol,
                bids=order_book['bids'],
                asks=order_book['asks'],
                timestamp=time.time())
            if enablePlotting:
                orderbookAnalyser.plotGraphs()

    async def kafkaConsumer(self):

        cred=self.parameters.getKafkaConsumerCredentials()
        topic = cred['topic']
        kafka_server = cred['uri']
        group_id = cred['group_id']

        loop = asyncio.get_event_loop()
        consumer = AIOKafkaConsumer(
            topic,
            loop=loop,
            bootstrap_servers=kafka_server,
            group_id=group_id,
            auto_offset_reset='latest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')))
        
        # Get cluster layout and join group
        await consumer.start()
        try:
            # Consume messages
            async for msg in consumer:
                try:
                    payload = json.loads(msg.value)
                    if payload['exchange'] == 'coinmarketcap':
                        self.orderbookAnalyser.updateCoinmarketcapPrice(payload['data'])
                    else:
                        logger.info("Received " + payload['symbol'] + " from " + payload['exchange'] + ' producer timestamp [ms]:' + str(payload['timestamp']) + ' (delay [ms]:'+str(time.time()*1000-float(payload['timestamp']))+')')
                        self.orderbookAnalyser.update(
                            exchangename=payload['exchange'],
                            symbol=payload['symbol'],
                            bids=payload['data']['bids'],
                            asks=payload['data']['asks'],
                            timestamp=payload['timestamp']/1000)
                except Exception as e:
                    logger.error('Error during parsing Kafka stream JSON, error:'+str(e))

        finally:
            # Will leave consumer group; perform autocommit if enabled.
            await consumer.stop()

    async def asyncRun(self):

        await self.trader.initExchangesFromAWSParameterStore()

        # start local pollers if selected as datasource 
        if self.parameters.datasource is FWLiveParams.datasource_localpollers:
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

        # start kafka consumer if selected as datasource 
        if self.parameters.datasource is FWLiveParams.datasource_kafka_local or self.parameters.datasource is FWLiveParams.datasource_kafka_aws:
            asyncio.ensure_future(self.kafkaConsumer())


    def run(self):

        asyncio.ensure_future(self.asyncRun())

        loop = asyncio.get_event_loop()      
        loop.run_forever()
        logger.info("FrameworkLive exited normally. Bye.")



def signal_handler(sig, frame):
    print('Ctrl+C detected, application will quit soon.')
    loop = asyncio.get_event_loop()
    loop.stop()
signal.signal(signal.SIGINT, signal_handler)

def main(argv):
    frameworklive_parameters = FWLiveParams()
    try:
        opts, _ = getopt.getopt(argv, "nrodpslfe",
                                ["enableplotting",
                                 "resultsdir=",
                                 "neo4jmode=",
                                 "dealfinder=",
                                 "output=",
                                 "datasource=",
                                 "live",
                                 "noforex",
                                 "remotedebug"])
    except getopt.GetoptError:
        logger.error(
            'Invalid parameter(s) entered. List of valid parameters:\n'
            ' --enableplotting: enable NetworkX graph plots\n'
            ' --resultsdir =  path: output directory\n'
            ' --dealfinder =  neo4j: use neo4j to find arbitrage deals\n'
            '                 networkx: use networkx/belman-ford to find arbitrage deals\n'
            '                 all: run both neo4j and networkx in parallel to find arbitrage deals\n'
            ' --datasource =  localpollers: local pollers are used as data-source \n'
            '                 kafkalocal: locally hosted kafka stream used as data-source \n'
            '                 kafkaaws: asyncio pollers are used as data-source \n'
            ' --output =      logfiles: save output to logfiles (default)\n'
            '                 kafkalocal: save output to logfiles \n'
            '                 kafkaaws: save output to logfiles \n'
            ' --live:         trades are actually executed (not a sandbox)\n'
            ' --noforex:      disable forex\n'
            ' --neo4jmode =   local: connect to neo4j running on localhost\n'
            '                 aws: connect to neo4j running in AWS\n'
            ' --remotedebug: enable remote debugging\n'
        )
        sys.exit(2)
    except Exception as error:
        logger.error('Generic exception whilst parsing console arguments '+ str(error.args))

    for opt, arg in opts:
        if opt in ("-n", "--enableplotting"):
            frameworklive_parameters.enable_plotting = True
        if opt in ("-r", "--resultsdir"):
            frameworklive_parameters.results_dir = arg
        if opt in ("-o", "--neo4jmode"):
            if arg == 'local':
                frameworklive_parameters.neo4j_mode = FWLiveParams.neo4j_mode_localhost
            if arg == 'aws':
                frameworklive_parameters.neo4j_mode = FWLiveParams.neo4j_mode_aws_cloud
            if arg not in ['local', 'aws']:
                logger.error('Invalid neo4j mode in parameter')
                return

        if opt in ("-d", "--dealfinder"):
            if arg == 'neo4j':
                frameworklive_parameters.dealfinder_mode = FWLiveParams.dealfinder_mode_neo4j
            if arg == 'networkx':
                frameworklive_parameters.dealfinder_mode = FWLiveParams.dealfinder_mode_networkx
            if arg == 'all':
                frameworklive_parameters.dealfinder_mode = FWLiveParams.dealfinder_mode_networkx + FWLiveParams.dealfinder_mode_neo4j

            if arg not in ['neo4j', 'networkx','all']:
                logger.error('Invalid dealfiner mode in parameter')
                return

        if opt in ("-p", "--output"):
            if arg == 'logfiles':
                frameworklive_parameters.output = FWLiveParams.output_logfiles
            if arg == 'kafkalocal':
                frameworklive_parameters.output = FWLiveParams.output_kafkalocal
            if arg == 'kafkaaws':
                frameworklive_parameters.output = FWLiveParams.output_kafkaaws

            if arg not in ['logfiles', 'kafkalocal','kafkaaws']:
                logger.error("Invalid value in 'output' parameter")
                return

        if opt in ("-s", "--datasource"):
            if arg == 'localpollers':
                frameworklive_parameters.datasource = FWLiveParams.datasource_localpollers
            if arg == 'kafkaaws':
                frameworklive_parameters.datasource = FWLiveParams.datasource_kafka_aws
            if arg == 'kafkalocal':
                frameworklive_parameters.datasource = FWLiveParams.datasource_kafka_local

            if arg not in ['localpollers', 'kafkaaws','kafkalocal']:
                logger.error('Invalid datasource in parameter')
                return

        if opt in ("-l", "--live"):
            frameworklive_parameters.is_sandbox_mode = False
        if opt in ("-f", "--noforex"):
            frameworklive_parameters.is_forex_enabled = False

        if opt in ("-e", "--noforex"):
            frameworklive_parameters.remoteDebuggingEnabled = False

    if frameworklive_parameters.is_sandbox_mode is True:
        logger.info("Running in sandbox mode, TRADES WILL NOT BE EXECUTED")
    else:
        logger.info("Running in live mode, TRADES WILL BE EXECUTED")

    if frameworklive_parameters.remoteDebuggingEnabled is True:
        logger.info('Waiting for remote python debugger to connect')
        ptvsd.enable_attach()
        ptvsd.wait_for_attach()

    frameworkLive = FrameworkLive(frameworklive_parameters)
    frameworkLive.run()


if __name__ == "__main__":
    main(sys.argv[1:])