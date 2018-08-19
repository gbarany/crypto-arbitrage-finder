from tqdm import tqdm
import MySQLdb as MySQLdb
import numpy as np
from ArbitrageGraph import ArbitrageGraph
from ExchangeFeeStore import ExchangeFeeStore
from OrderBook import OrderBook
from PriceStore import PriceStore
import pandas as pd


class OrderbookAnalyser:
    def __init__(self,host,user,passwd,db,port):
        self.host=host
        self.user = user
        self.passwd = passwd
        self.db = db
        self.port = port
        self.arbitrageGraph = ArbitrageGraph(edgeTTL=5)
        self.exchangeFeeStore = ExchangeFeeStore()
        self.priceStore = PriceStore(priceTTL=60)

    def getSQLQuery(self,exchangeList,limit):
        sql="""
        SELECT exchange, pair, bids, asks, id, orderbook_time 
        FROM orderbook WHERE exchange 
        IN %s
        ORDER BY ID""" % ("('"+"','".join(exchangeList)+"')")
        if limit:
            sql += " LIMIT %d"%limit
        
        sql += ";"
        return sql

    def runSim(self,exchangeList,limit=None,vol_BTC=1):
        sql = self.getSQLQuery(exchangeList=exchangeList,limit=limit)
        db = MySQLdb.connect(
            host=self.host,
            user=self.user,
            passwd=self.passwd,
            db=self.db,
            port=self.port)
        cursor = db.cursor()
        nof_rows=cursor.execute(sql)
        print("Rows fetched:",nof_rows)
        
        columns = ['id','length','profit_perc','nodes','edges_weight','edges_age_s','hops','exchanges_involved','nof_exchanges_involved']
        df = pd.DataFrame(columns=columns)

        for row in tqdm(cursor):
            exchangename = row[0]
            symbol = row[1]
            bids_str = row[2]
            asks_str = row[3]
            id_str = int(row[4])
            timestamp = float(row[5])
            self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks_str,bids=bids_str,timestamp=timestamp)

            try:
                orderBook = OrderBook(symbol=symbol,asks=asks_str,bids=bids_str)
                rate_BTC_to_BASE = self.priceStore.getMeanPrice(symbol_base_ref='BTC',symbol_quote_ref=symbol.split('/')[0],timestamp=timestamp)                

                if rate_BTC_to_BASE == None:
                    continue
                vol_BASE = vol_BTC*rate_BTC_to_BASE

                askPrice=orderBook.getAskPrice(vol=vol_BASE)
                bidPrice=orderBook.getBidPrice(vol=vol_BASE)
                
                length, nodes, negative_cycle = self.arbitrageGraph.update_point(
                    symbol,
                    exchangename,
                    self.exchangeFeeStore.getTakerFee(exchangename,symbol),
                    askPrice,
                    bidPrice,
                    timestamp)
                
                if negative_cycle == True:
                    edges_weight, edges_age_s, hops, exchanges_involved, nof_exchanges_involved=self.arbitrageGraph.nodeslist_to_edges(nodes,timestamp)
                    df=df.append(pd.DataFrame([[
                        int(id_str),
                        length,np.exp(-1.0*length)*100-100,
                        ",".join(str(x) for x in nodes),
                        ",".join(str(x) for x in edges_weight),
                        ",".join(str(x) for x in edges_age_s),
                        hops,
                        ",".join(str(x) for x in exchanges_involved),
                        nof_exchanges_involved]],
                        columns=columns),
                        ignore_index=True)
                    
                #arbitrageGraph.plot_graph()
            except IndexError:
                print("*** Invalid orderbook ***")
            except NameError:
                print("*** NoneType error ***")
            except TypeError:
                print("*** TypeError error ***")

        db.close()
        return df

if __name__ == "__main__":
    runLocal = True

    if runLocal == False:
        host="orderbook.cyifbgm0zwt0.eu-west-2.rds.amazonaws.com"
        user="admin"
        passwd="123Qwe123Qwe"
        db="orderbook"
        port=3306
    else:
        host="127.0.0.1"
        user="admin"
        passwd="admin"
        db="orderbook"
        port=33306

    orderbookAnalyser = OrderbookAnalyser(host,user,passwd,db,port)

    exchangeList = ['coinfloor','kraken','bitfinex','bittrex','gdax','bitstamp','coinbase','poloniex']
    df=orderbookAnalyser.runSim(exchangeList=exchangeList,limit=1000,vol_BTC=0.0016)
    df.to_csv("arbitrage.csv",index=False)