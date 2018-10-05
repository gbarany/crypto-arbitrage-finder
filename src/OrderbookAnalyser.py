import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ArbitrageGraphNeo import ArbitrageGraphNeo
from FeeStore import FeeStore
from OrderBook import OrderBook
from PriceStore import PriceStore
import pandas as pd
import os
import dill
import datetime
import logging
from Trader import Trader
from FWLiveParams import FWLiveParams
logger = logging.getLogger('CryptoArbitrageApp')


class OrderbookAnalyser:
    PRICE_SOURCE_ORDERBOOK = "PRICE_SOURCE_ORDERBOOK"
    PRICE_SOURCE_CMC = "PRICE_SOURCE_CMC"

    def __init__(self,
                 vol_BTC=[1],
                 edgeTTL=5,
                 priceTTL=60,
                 resultsdir='./',
                 tradeLogFilename="tradelog.csv",
                 priceSource=PRICE_SOURCE_ORDERBOOK,
                 arbTradeTriggerEvent=None,
                 arbTradeQueue=None,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled):

        # create Arbitrage Graph objects
        self.arbitrageGraphs = [ArbitrageGraph(edgeTTL=edgeTTL) for count in range(len(vol_BTC))]
        self.arbitrage_graph_neo = ArbitrageGraphNeo(edgeTTL=edgeTTL,neo4j_mode=neo4j_mode)
        
        self.feeStore = FeeStore()
        self.priceStore = PriceStore(priceTTL=priceTTL)
        self.vol_BTC = vol_BTC
        self.resultsdir = resultsdir
        self.timestamp_start = datetime.datetime.now()
        self.cmcTicker = None
        self.neo4j_mode = neo4j_mode
        self.arbTradeTriggerEvent = arbTradeTriggerEvent
        self.arbTradeQueue = arbTradeQueue
        self.priceSource = priceSource
        self.df_results = pd.DataFrame(columns=[
            'id', 'timestamp', 'vol_BTC', 'length', 'profit_perc', 'nodes',
            'edges_weight', 'edges_age_s', 'hops', 'exchanges_involved',
            'nof_exchanges_involved'
        ])
        self.tradeLogFilename = self.timestamp_start.strftime(
            '%Y%m%d-%H%M%S') + "_" + tradeLogFilename
        try:
            os.remove(self.resultsdir + self.tradeLogFilename)
        except OSError:
            pass
        with open(self.resultsdir + self.tradeLogFilename, 'a') as f:
            self.df_results.to_csv(f, header=True, index=False)

        self.generateExportFilename()
        self.isRunning = True

    def updateCoinmarketcapPrice(self, cmcTicker):
        self.cmcTicker = cmcTicker

    def updateForexPrice(self, forexTicker):
        self.priceStore.updatePriceFromForex(forexTicker)

    def logArbitrageDeal(self, id, vol_BTC, timestamp, path):
        df_new = path.toDataFrameLog(
            id=id,
            timestamp=timestamp,
            vol_BTC=vol_BTC,
            df_columns=self.df_results.columns)
        self.df_results = self.df_results.append(df_new, ignore_index=True)

        with open(self.resultsdir + self.tradeLogFilename, 'a') as f:
            df_new.to_csv(f, header=False, index=False)

    def update(self, exchangename, symbol, bids, asks, id, timestamp):

        if self.priceSource == OrderbookAnalyser.PRICE_SOURCE_ORDERBOOK:
            self.priceStore.updatePriceFromOrderBook(
                symbol=symbol,
                exchangename=exchangename,
                asks=asks,
                bids=bids,
                timestamp=timestamp)
        elif self.priceSource == OrderbookAnalyser.PRICE_SOURCE_CMC:
            if self.cmcTicker is not None:
                self.priceStore.updatePriceFromCoinmarketcap(
                    ticker=self.cmcTicker)
            else:
                # logger.info('No CMC ticker received yet, reverting to orderbook pricing')
                # self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks,bids=bids,timestamp=timestamp)
                logger.info('No CMC ticker received yet, skipping update')
                return
        try:
            rate_BTC_to_base = self.priceStore.getMeanPrice(
                symbol_base_ref='BTC',
                symbol_quote_ref=symbol.split('/')[0],
                timestamp=timestamp)
            orderBook = OrderBook(symbol=symbol, asks=asks, bids=bids,rate_BTC_to_base=rate_BTC_to_base)
            
            # Price store doesn't have an exchange rate for this trading pair
            # therefore trading graph won't be updated
            if rate_BTC_to_base is None:
                return

            self.arbitrage_graph_neo.updatePoint(
                symbol=symbol,
                exchange_name=exchangename,
                fee_rate=self.feeStore.getTakerFee(exchangename, symbol),
                orderbook=orderBook
            )

            for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
                vol_BASE = self.vol_BTC[idx] * rate_BTC_to_base

                askPrice = orderBook.getAskPrice(vol=vol_BASE)
                bidPrice = orderBook.getBidPrice(vol=vol_BASE)

                path = arbitrageGraph.updatePoint(
                    symbol=symbol,
                    exchangename=exchangename,
                    feeRate=self.feeStore.getTakerFee(exchangename, symbol),
                    askPrice=askPrice,
                    bidPrice=bidPrice,
                    timestamp=timestamp)

                if path.isNegativeCycle is True:
                    logger.info("Found arbitrage deal")
                    self.logArbitrageDeal(
                        id=id,
                        timestamp=timestamp,
                        vol_BTC=self.vol_BTC[idx],
                        path=path)

                    if self.arbTradeTriggerEvent is not None and self.arbTradeQueue is not None:
                        self.arbTradeTriggerEvent.acquire()
                        self.arbTradeQueue.append(path)
                        self.arbTradeTriggerEvent.notify()
                        self.arbTradeTriggerEvent.release()
                        logger.info(
                            "Arbitrage trade event created succesfully")

                    else:
                        logger.info(
                            "Creating arbitrage trade event failed, invalid event or queue"
                        )

        except Exception as e:
            logger.error("Exception on exchangename:" + exchangename +
                         " symbol:" + symbol + ":" + str(e))

    def generateExportFilename(self, exchangeList=None):
        if exchangeList is None:
            self.exportFilename = "arbitrage_Vol=%s" % ("-".join(
                [str(i) + "BTC" for i in self.vol_BTC]))
        else:
            self.exportFilename = "arbitrage_Vol=%s_XC=%s" % ("-".join(
                [str(i) + "BTC"
                 for i in self.vol_BTC]), '-'.join(exchangeList))

    def terminate(self):
        self.isRunning = False

    def save(self):
        fname = self.resultsdir + self.timestamp_start.strftime(
            '%Y%m%d-%H%M%S') + "_" + self.exportFilename
        self.df_results.to_csv(fname + ".csv", index=False)
        with open(fname + ".pkl", 'wb') as f:
            dill.dump(self, f)
        logger.info("Orderbook analyser results saved at " + fname)

    def plotGraphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plotGraph(
                figid=(idx + 1), vol_BTC=self.vol_BTC[idx])
