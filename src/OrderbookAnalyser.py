import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ArbitrageGraphNeo import ArbitrageGraphNeo
from FeeStore import FeeStore
from OrderBook import OrderBook, OrderBookPair, Asset
from PriceStore import PriceStore
import os
import dill
import datetime
import logging
from Trader import Trader, SegmentedOrderRequestList, OrderRequestList
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
                 trader=None,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled):

        # create Arbitrage Graph objects
        self.arbitrageGraphs = [ArbitrageGraph() for count in range(len(vol_BTC))]
        self.arbitrageGraphNeo = ArbitrageGraphNeo(neo4j_mode=neo4j_mode,volumeBTCs=vol_BTC)
        self.edgeTTL=edgeTTL
        self.feeStore = FeeStore()
        self.priceStore = PriceStore(priceTTL=priceTTL)
        self.vol_BTC = vol_BTC
        self.resultsdir = resultsdir
        self.timestamp_start = datetime.datetime.now()
        self.cmcTicker = None
        self.neo4j_mode = neo4j_mode
        self.priceSource = priceSource
        self.tradeLogFilename = self.timestamp_start.strftime(
            '%Y%m%d-%H%M%S') + "_" + tradeLogFilename
        try:
            os.remove(self.resultsdir + self.tradeLogFilename)
        except OSError:
            pass

        self.isRunning = True
        assert trader is not None
        self.trader = trader

    def updateCoinmarketcapPrice(self, cmcTicker):
        self.cmcTicker = cmcTicker

    def updateForexPrice(self, forexTicker):
        self.priceStore.updatePriceFromForex(forexTicker)

    def update(self, exchangename, symbol, bids, asks, timestamp):

        if self.priceSource == OrderbookAnalyser.PRICE_SOURCE_ORDERBOOK:
            self.priceStore.updatePriceFromOrderBook(
                symbol=symbol,
                exchangename=exchangename,
                asks=asks,
                bids=bids,
                timestamp=timestamp)
        elif self.priceSource == OrderbookAnalyser.PRICE_SOURCE_CMC:
            if self.cmcTicker is not None:
                self.priceStore.updatePriceFromCoinmarketcap(ticker=self.cmcTicker)
            else:
                # logger.info('No CMC ticker received yet, reverting to orderbook pricing')
                # self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks,bids=bids,timestamp=timestamp)
                logger.info('No CMC ticker received yet, skipping update')
                return
        try:
            rateBTCxBase = self.priceStore.getMeanPrice(
                symbol_base_ref='BTC',
                symbol_quote_ref=symbol.split('/')[0],
                timestamp=timestamp)

            rateBTCxQuote = self.priceStore.getMeanPrice(
                symbol_base_ref='BTC',
                symbol_quote_ref=symbol.split('/')[1],
                timestamp=timestamp)

            # Price store doesn't have an exchange rate for this trading pair
            # therefore trading graph won't be updated
            if rateBTCxBase is None or rateBTCxQuote is None :
                return

            orderBookPair = OrderBookPair(
                timestamp=timestamp,
                symbol=symbol,
                exchange=exchangename,
                asks=asks,
                bids=bids,
                rateBTCxBase=rateBTCxBase,
                rateBTCxQuote=rateBTCxQuote,
                feeRate=self.feeStore.getTakerFee(exchangename, symbol),
                timeToLiveSec=self.edgeTTL)

            path_neo=self.arbitrageGraphNeo.updatePoint(orderBookPair=orderBookPair,volumeBTCs=self.vol_BTC)


            for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
                path = arbitrageGraph.updatePoint(orderBookPair=orderBookPair,volumeBTC = self.vol_BTC[idx])

                if path.isNegativeCycle is True:
                    logger.info("Found arbitrage deal")
                    path.log()                    
                    sorl = path.toSegmentedOrderList()
                    self.trader.execute(sorl)
                    logger.info("Arbitrage trade event created succesfully")


        except Exception as e:
            logger.error("Exception on exchangename:" + exchangename +
                         " symbol:" + symbol + ":" + str(e))

    def terminate(self):
        self.isRunning = False

    def plotGraphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plotGraph(
                figid=(idx + 1), vol_BTC=self.vol_BTC[idx])
