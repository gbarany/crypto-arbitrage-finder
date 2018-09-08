#!/usr/bin/python

import sys, getopt
import signal
from OrderbookAnalyser import OrderbookAnalyser
from InitLogger import logger


def simFromDB(runLocalDB=True,vol_BTC=[1],exchangeList=None,limit=100,resultsdir="./"):
    
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

    orderbookAnalyser = OrderbookAnalyser(
        vol_BTC=vol_BTC,
        resultsdir=resultsdir,
        tradeLogFilename='tradelog_simdb.csv')
        
    def sigterm(x, y):
        print('\n[FrameworkSimDB] SIGTERM received, time to leave.\n')
        orderbookAnalyser.terminate()

    # Register the signal to the handler
    signal.signal(signal.SIGTERM, sigterm)  # Used by this script

    df_results=orderbookAnalyser.runSimFromDB(dbconfig=dbconfig,exchangeList=exchangeList,limit=limit)
    orderbookAnalyser.save()
    return df_results

def main(argv):
    resultsdir = './'
    runLocalDB = False
    limit = None
    vol_BTC=[1,0.1,0.01]

    try:
        opts, _ = getopt.getopt(argv,"lri",["localdb","resultsdir=","limit="])
    except getopt.GetoptError:
        print('Invalid parameter.')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-l", "--localdb"):
            runLocalDB = True
        if opt in ("-r", "--resultsdir"):
            resultsdir = arg
        if opt in ("-i", "--limit"):
            limit = int(arg)
    exchangeList = ['coinfloor','kraken','bitfinex','bittrex','gdax','bitstamp','coinbase','poloniex']
    simFromDB(vol_BTC=vol_BTC,exchangeList=exchangeList,limit=limit,resultsdir=resultsdir,runLocalDB=runLocalDB)
    
if __name__ == "__main__":
    main(sys.argv[1:])