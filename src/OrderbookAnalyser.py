import numpy as np
from ArbitrageGraph import ArbitrageGraph
from FeeStore import FeeStore
from OrderBook import OrderBook
from PriceStore import PriceStore
import pandas as pd
import os
import dill
import datetime
import logging
from Trader import Trader

logger = logging.getLogger('CryptoArbitrageApp')

class OrderbookAnalyser:
    PRICE_SOURCE_ORDERBOOK="PRICE_SOURCE_ORDERBOOK"
    PRICE_SOURCE_CMC="PRICE_SOURCE_CMC"

    def __init__(self,vol_BTC=[1],edgeTTL=5,priceTTL=60,resultsdir='./',tradeLogFilename="tradelog.csv",priceSource=PRICE_SOURCE_ORDERBOOK,arbTradeTriggerEvent=None,arbTradeQueue=None):
        self.arbitrageGraphs = [ArbitrageGraph(edgeTTL=edgeTTL) for count in range(len(vol_BTC))] # create Arbitrage Graph objects
        self.feeStore = FeeStore()
        self.priceStore = PriceStore(priceTTL=priceTTL)
        self.vol_BTC = vol_BTC
        self.resultsdir = resultsdir
        self.timestamp_start = datetime.datetime.now()
        self.cmcTicker = None
        
        self.arbTradeTriggerEvent=arbTradeTriggerEvent
        self.arbTradeQueue=arbTradeQueue
        self.priceSource = priceSource
        self.df_results = pd.DataFrame(
            columns=['id','timestamp','vol_BTC','length','profit_perc','nodes','edges_weight','edges_age_s','hops','exchanges_involved','nof_exchanges_involved'])
        self.tradeLogFilename = self.timestamp_start.strftime('%Y%m%d-%H%M%S')+"_"+tradeLogFilename
        try:
            os.remove(self.resultsdir+self.tradeLogFilename)
        except OSError:
            pass
        with open(self.resultsdir+self.tradeLogFilename, 'a') as f:
            self.df_results.to_csv(f, header=True, index=False)

        self.generateExportFilename()
        self.isRunning = True

    def updateCmcPrice(self,cmcTicker):
        self.cmcTicker = cmcTicker

    def logArbitrageDeal(self,id,timestamp,path):
        df_new = path.toDataFrame(id=id, timestamp=timestamp,vol_BTC=self.vol_BTC[idx])
        self.df_results=self.df_results.append(df_new,ignore_index=True)

        with open(self.resultsdir+self.tradeLogFilename, 'a') as f:
            df_new.to_csv(f, header=False, index=False)

    def update(self,exchangename,symbol,bids,asks,id,timestamp):

        if self.priceSource == OrderbookAnalyser.PRICE_SOURCE_ORDERBOOK:
            self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks,bids=bids,timestamp=timestamp)
        elif self.priceSource == OrderbookAnalyser.PRICE_SOURCE_CMC:
            if self.cmcTicker!=None:
                self.priceStore.updatePriceFromCoinmarketcap(ticker=self.cmcTicker)
            else:
                logger.info('No CMC ticker received yet, reverting to orderbook pricing')
                self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks,bids=bids,timestamp=timestamp)
                

        try:
            orderBook = OrderBook(symbol=symbol,asks=asks,bids=bids)
            rate_BTC_to_BASE = self.priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref=symbol.split('/')[0],timestamp=timestamp)

            for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
                vol_BASE = self.vol_BTC[idx]*rate_BTC_to_BASE

                askPrice=orderBook.getAskPrice(vol=vol_BASE)
                bidPrice=orderBook.getBidPrice(vol=vol_BASE)
                
                path = arbitrageGraph.updatePoint(
                    symbol,
                    exchangename,
                    self.feeStore.getTakerFee(exchangename,symbol),
                    askPrice.meanprice,
                    bidPrice.meanprice,
                    timestamp)
                
                if path.isNegativeCycle == True:
                    logger.info("Found arbitrage deal")
                    self.logArbitrageDeal(id=id,timestamp=timestamp,path=path)

                    if self.arbTradeTriggerEvent!=None and self.arbTradeQueue!=None:
                        self.arbTradeTriggerEvent.acquire()                        
                        self.arbTradeQueue.append(path.toTradeList())
                        self.arbTradeTriggerEvent.notify()
                        self.arbTradeTriggerEvent.release()        
                        logger.info("Arbitrage trade event created succesfully")
                        
                    else:
                        logger.info("Creating arbitrage trade event failed, invalid event or queue")
                    
        except Exception as e:
            logger.error("Exception on exchangename:"+exchangename+" symbol:"+symbol+":"+e)

    def generateExportFilename(self,exchangeList=None):
        if exchangeList == None:
            self.exportFilename = "arbitrage_Vol=%s"%("-".join([str(i)+"BTC" for i in self.vol_BTC]))
        else:
            self.exportFilename = "arbitrage_Vol=%s_XC=%s"%("-".join([str(i)+"BTC" for i in self.vol_BTC]),'-'.join(exchangeList))

    def terminate(self):
        self.isRunning = False

    def save(self):
        fname = self.resultsdir+self.timestamp_start.strftime('%Y%m%d-%H%M%S')+"_"+self.exportFilename
        self.df_results.to_csv(fname+".csv",index=False)
        with open(fname+".pkl", 'wb') as f:
            dill.dump(self, f)
        logger.info("Orderbook analyser results saved at " +fname)

    def plotGraphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plotGraph(figid=(idx+1),vol_BTC=self.vol_BTC[idx])