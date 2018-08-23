from tqdm import tqdm
import MySQLdb as MySQLdb
import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ExchangeFeeStore import ExchangeFeeStore
from OrderBook import OrderBook
from PriceStore import PriceStore
import pandas as pd


class OrderbookAnalyser:
    def __init__(self,vol_BTC=[1],edgeTTL=5,priceTTL=60):
        self.arbitrageGraphs = [ArbitrageGraph(edgeTTL=edgeTTL) for count in range(len(vol_BTC))] # create Arbitrage Graph objects
        self.exchangeFeeStore = ExchangeFeeStore()
        self.priceStore = PriceStore(priceTTL=priceTTL)
        self.vol_BTC = vol_BTC
        self.df_results = pd.DataFrame(
            columns=['id','vol_BTC','length','profit_perc','nodes','edges_weight','edges_age_s','hops','exchanges_involved','nof_exchanges_involved'])
        self.generateExportFilename()

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
                    self.df_results=self.df_results.append(pd.DataFrame([[
                        int(id),
                        float(self.vol_BTC[idx]),
                        length,np.exp(-1.0*length)*100-100,
                        ",".join(str(x) for x in nodes),
                        ",".join(str(x) for x in edges_weight),
                        ",".join(str(x) for x in edges_age_s),
                        hops,
                        ",".join(str(x) for x in exchanges_involved),
                        nof_exchanges_involved]],
                        columns=self.df_results.columns),
                        ignore_index=True)
                    
        except IndexError:
            print("*** Invalid orderbook ***")
        except NameError:
            print("*** NoneType error ***")
        except TypeError:
            print("*** TypeError error ***")
        except Exception as e:
            print("*** General error within the update loop error ***")

    def generateExportFilename(self,exchangeList=None):
        if exchangeList == None:
            self.exportFilename = "arbitrage_Vol=%s"%("-".join([str(i)+"BTC" for i in self.vol_BTC]))
        else:
            self.exportFilename = "arbitrage_Vol=%s_XC=%s"%("-".join([str(i)+"BTC" for i in self.vol_BTC]),'-'.join(exchangeList))

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
            self.update(
                exchangename=row[0],
                symbol = row[1],
                bids = row[2],
                asks = row[3],
                id = int(row[4]),
                timestamp = float(row[5])
                )
            #arbitrageGraph.plot_graph()
        db.close()
        return self.df_results

    def saveResultsCSV(self):
        self.df_results.to_csv("../results/"+self.exportFilename+".csv",index=False)

    def plot_graphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plot_graph(figid=(idx+1),vol_BTC=self.vol_BTC[idx])

def simFromDB(runLocalDB=True,vol_BTC=[1],exchangeList=None,limit=100):
    
    dbconfig = {}
    if runLocalDB == False:
        dbconfig["host"]="orderbook-2.cyifbgm0zwt0.eu-west-2.rds.amazonaws.com"
        dbconfig["user"]="admin"
        dbconfig["passwd"]="123Qwe123Qwe"
        dbconfig["db"]="orderbook"
        dbconfig["port"]=3306
    else:
        dbconfig["host"]="127.0.0.1"
        dbconfig["user"]="admin"
        dbconfig["passwd"]="admin"
        dbconfig["db"]="orderbook"
        dbconfig["port"]=33306

    orderbookAnalyser = OrderbookAnalyser(vol_BTC=vol_BTC)
    df_results=orderbookAnalyser.runSimFromDB(dbconfig=dbconfig,exchangeList=exchangeList,limit=limit)
    orderbookAnalyser.saveResultsCSV()
    return df_results

def simLive():
    orderbookAnalyser = OrderbookAnalyser(vol_BTC=[1])
    orderbookAnalyser.update("poloniex","BTC/USD",[],[],1,0)
    #orderbookAnalyser.update("poloniex","BTC/USD",[[1,2],[3,4]],[[2,3]],1,0)
    pass

if __name__ == "__main__":
    vol_BTC=[1,0.1,0.01]
    exchangeList = ['coinfloor','kraken','bitfinex','bittrex','gdax','bitstamp','coinbase','poloniex']
    limit = 10
    simFromDB(vol_BTC=vol_BTC,exchangeList=exchangeList,limit=limit)
    #simLive()