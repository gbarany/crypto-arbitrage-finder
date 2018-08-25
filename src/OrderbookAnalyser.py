from tqdm import tqdm
import MySQLdb as MySQLdb
import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ExchangeFeeStore import ExchangeFeeStore
from OrderBook import OrderBook
from PriceStore import PriceStore
import pandas as pd
import os
import dill
import datetime

class OrderbookAnalyser:
    def __init__(self,vol_BTC=[1],edgeTTL=5,priceTTL=60,resultsdir='./',tradeLogFilename="tradelog.csv"):
        self.arbitrageGraphs = [ArbitrageGraph(edgeTTL=edgeTTL) for count in range(len(vol_BTC))] # create Arbitrage Graph objects
        self.exchangeFeeStore = ExchangeFeeStore()
        self.priceStore = PriceStore(priceTTL=priceTTL)
        self.vol_BTC = vol_BTC
        self.resultsdir = resultsdir
        self.timestamp_start = datetime.datetime.now()
        self.df_results = pd.DataFrame(
            columns=['id','vol_BTC','length','profit_perc','nodes','edges_weight','edges_age_s','hops','exchanges_involved','nof_exchanges_involved'])
        self.tradeLogFilename = self.timestamp_start.strftime('%Y%m%d-%H%M%S')+"_"+tradeLogFilename
        try:
            os.remove(self.resultsdir+self.tradeLogFilename)
        except OSError:
            pass
        with open(self.resultsdir+self.tradeLogFilename, 'a') as f:
            self.df_results.to_csv(f, header=True, index=False)

        self.generateExportFilename()
        self.isRunning = True

    def getSQLQuery(self,exchangeList,limit):
        sql="""
        SELECT exchange, pair, bids, asks, id, orderbook_time 
        FROM orderbook"""
        if exchangeList:
            sql += " WHERE exchange IN %s" % ("('"+"','".join(exchangeList)+"')")
        
        sql += " ORDER BY ID"
        if limit:
            sql += " LIMIT %d"%limit
        
        sql += ";"
        return sql

    def update(self,exchangename,symbol,bids,asks,id,timestamp):

        self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks,bids=bids,timestamp=timestamp)

        try:
            orderBook = OrderBook(symbol=symbol,asks=asks,bids=bids)
            rate_BTC_to_BASE = self.priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref=symbol.split('/')[0],timestamp=timestamp)                

            if rate_BTC_to_BASE == None:
                return
            for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
                vol_BASE = self.vol_BTC[idx]*rate_BTC_to_BASE

                askPrice=orderBook.getAskPrice(vol=vol_BASE)
                bidPrice=orderBook.getBidPrice(vol=vol_BASE)
                
                length, nodes, negative_cycle = arbitrageGraph.update_point(
                    symbol,
                    exchangename,
                    self.exchangeFeeStore.getTakerFee(exchangename,symbol),
                    askPrice,
                    bidPrice,
                    timestamp)
                
                if negative_cycle == True:
                    edges_weight, edges_age_s, hops, exchanges_involved, nof_exchanges_involved=arbitrageGraph.nodeslist_to_edges(nodes,timestamp)
                    df_new = pd.DataFrame([[
                        int(id),
                        float(self.vol_BTC[idx]),
                        length,np.exp(-1.0*length)*100-100,
                        ",".join(str(x) for x in nodes),
                        ",".join(str(x) for x in edges_weight),
                        ",".join(str(x) for x in edges_age_s),
                        hops,
                        ",".join(str(x) for x in exchanges_involved),
                        nof_exchanges_involved]],
                        columns=self.df_results.columns)
                    self.df_results=self.df_results.append(df_new,ignore_index=True)
                    with open(self.resultsdir+self.tradeLogFilename, 'a') as f:
                        df_new.to_csv(f, header=False, index=False)
                    
        except IndexError:
            print("*** Invalid orderbook ***")
        except NameError:
            print("*** NoneType error ***")
        except TypeError:
            print("*** TypeError error ***")
        except Exception as e:
            print("*** General error within the update loop error:", e)

    def generateExportFilename(self,exchangeList=None):
        if exchangeList == None:
            self.exportFilename = "arbitrage_Vol=%s"%("-".join([str(i)+"BTC" for i in self.vol_BTC]))
        else:
            self.exportFilename = "arbitrage_Vol=%s_XC=%s"%("-".join([str(i)+"BTC" for i in self.vol_BTC]),'-'.join(exchangeList))

    def terminate(self):
        self.isRunning = False

    def runSimFromDB(self,dbconfig,exchangeList=None,limit=None):
        self.generateExportFilename(exchangeList)
        sql = self.getSQLQuery(exchangeList=exchangeList,limit=limit)
        db = MySQLdb.connect(
            host=dbconfig["host"],
            user=dbconfig["user"],
            passwd=dbconfig["passwd"],
            db=dbconfig["db"],
            port=dbconfig["port"])
        cursor = db.cursor()
        nof_rows=cursor.execute(sql)
        print("Rows fetched:",nof_rows)
        

        for row in tqdm(cursor):
            if self.isRunning:
                self.update(
                    exchangename=row[0],
                    symbol = row[1],
                    bids = row[2],
                    asks = row[3],
                    id = int(row[4]),
                    timestamp = float(row[5])
                    )
                #arbitrageGraph.plot_graph()
            else:
                break
        db.close()
        return self.df_results

    def save(self):
        fname = self.resultsdir+self.timestamp_start.strftime('%Y%m%d-%H%M%S')+"_"+self.exportFilename
        self.df_results.to_csv(fname+".csv",index=False)
        with open(fname+".pkl", 'wb') as f:
            dill.dump(self, f)
    

    def plot_graphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plot_graph(figid=(idx+1),vol_BTC=self.vol_BTC[idx])