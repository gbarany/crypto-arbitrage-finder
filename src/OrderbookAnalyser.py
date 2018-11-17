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
import asyncio

logger = logging.getLogger('CryptoArbitrageApp')

class OrderbookAnalyser:
    PRICE_SOURCE_ORDERBOOK = "PRICE_SOURCE_ORDERBOOK"
    PRICE_SOURCE_CMC = "PRICE_SOURCE_CMC"

    def __init__(self,
                 vol_BTC=[1],
                 edgeTTL=5,
                 priceTTL=60,
                 resultsdir='./',
                 priceSource=PRICE_SOURCE_ORDERBOOK,
                 trader=None,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled,
                 dealfinder_mode=FWLiveParams.dealfinder_mode_networkx):

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
        self.dealfinder_mode = dealfinder_mode
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


        
        # ArbitrageGraphNeo deal finder (Neo4j)
        if self.dealfinder_mode & FWLiveParams.dealfinder_mode_neo4j:
            
            self.arbitrageGraphNeo.updatePoint(orderBookPair=orderBookPair)
            paths_neo=self.arbitrageGraphNeo.getArbitrageDeal(
                timestamp=timestamp,
                asset=Asset(exchange=orderBookPair.exchange, symbol=orderBookPair.getSymbolBase()))
            

            for path_neo in paths_neo:
                if path_neo.isProfitable() is True:
                    logger.info("Neo4j Found arbitrage deal: "+str(path_neo))
                    path_neo.log()
                    sorl = path_neo.toSegmentedOrderList()
                    asyncio.ensure_future(self.trader.execute(sorl))

        # ArbitrageGraph deal finder (NetworkX)
        if self.dealfinder_mode & FWLiveParams.dealfinder_mode_networkx:
            for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
                arbitrageGraph.updatePoint(orderBookPair=orderBookPair,volumeBTC = self.vol_BTC[idx])
                path = arbitrageGraph.getArbitrageDeal(timestamp)
                if path.isProfitable() is True:
                    logger.info("NetX Found arbitrage deal: "+str(path))
                    path.log()
                    sorl = path.toSegmentedOrderList()
                    asyncio.ensure_future(self.trader.execute(sorl))


    def terminate(self):
        self.isRunning = False

    def plotGraphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plotGraph(
                figid=(idx + 1), vol_BTC=self.vol_BTC[idx])
