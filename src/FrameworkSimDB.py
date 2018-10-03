#!/usr/bin/python

import sys, getopt
import signal
from OrderbookAnalyser import OrderbookAnalyser
from InitLogger import logger
from tqdm import tqdm
import MySQLdb as MySQLdb


def getSQLQuery(exchangeList, limit):
    sql = """
        SELECT exchange, pair, bids, asks, id, orderbook_time 
        FROM orderbook"""
    if exchangeList:
        sql += " WHERE exchange IN %s" % (
            "('" + "','".join(exchangeList) + "')")

    sql += " ORDER BY ID"
    if limit:
        sql += " LIMIT %d" % limit

    sql += ";"
    return sql


def runSimFromDB(orderbookAnalyser, dbconfig, exchangeList=None, limit=None):
    orderbookAnalyser.generateExportFilename(exchangeList)
    sql = getSQLQuery(exchangeList=exchangeList, limit=limit)
    db = MySQLdb.connect(
        host=dbconfig["host"],
        user=dbconfig["user"],
        passwd=dbconfig["passwd"],
        db=dbconfig["db"],
        port=dbconfig["port"])
    cursor = db.cursor()
    nof_rows = cursor.execute(sql)
    logger.info("Rows fetched:" + str(nof_rows))

    for row in tqdm(cursor):
        if orderbookAnalyser.isRunning:
            orderbookAnalyser.update(
                exchangename=row[0],
                symbol=row[1],
                bids=row[2],
                asks=row[3],
                id=int(row[4]),
                timestamp=float(row[5]))
            #arbitrageGraph.plotGraph()
        else:
            break
    db.close()
    return orderbookAnalyser.df_results


def simFromDB(runLocalDB=True,
              vol_BTC=[1],
              exchangeList=None,
              limit=100,
              resultsdir="./"):

    dbconfig = {}
    if runLocalDB == False:
        dbconfig[
            "host"] = "orderbook-2.cyifbgm0zwt0.eu-west-2.rds.amazonaws.com"
        dbconfig["user"] = "admin"
        dbconfig["passwd"] = "123Qwe123Qwe"
        dbconfig["db"] = "orderbook"
        dbconfig["port"] = 3306
    else:
        dbconfig["host"] = "127.0.0.1"
        dbconfig["user"] = "admin"
        dbconfig["passwd"] = "admin"
        dbconfig["db"] = "orderbook"
        dbconfig["port"] = 33306

    orderbookAnalyser = OrderbookAnalyser(
        vol_BTC=vol_BTC,
        resultsdir=resultsdir,
        tradeLogFilename='tradelog_simdb.csv')

    def sigterm(x, y):
        print('\n[FrameworkSimDB] SIGTERM received, time to leave.\n')
        orderbookAnalyser.terminate()

    # Register the signal to the handler
    signal.signal(signal.SIGTERM, sigterm)  # Used by this script

    df_results = runSimFromDB(
        orderbookAnalyser=orderbookAnalyser,
        dbconfig=dbconfig,
        exchangeList=exchangeList,
        limit=limit)
    orderbookAnalyser.save()
    return df_results


def main(argv):
    resultsdir = './'
    runLocalDB = False
    limit = None
    vol_BTC = [1, 0.1, 0.01]

    try:
        opts, _ = getopt.getopt(argv, "lri",
                                ["localdb", "resultsdir=", "limit="])
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
    exchangeList = [
        'coinfloor', 'kraken', 'bitfinex', 'bittrex', 'gdax', 'bitstamp',
        'coinbase', 'poloniex'
    ]
    simFromDB(
        vol_BTC=vol_BTC,
        exchangeList=exchangeList,
        limit=limit,
        resultsdir=resultsdir,
        runLocalDB=runLocalDB)


if __name__ == "__main__":
    main(sys.argv[1:])
