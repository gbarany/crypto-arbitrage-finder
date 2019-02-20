import logging
import sys

###################
## Init app logger
logger = logging.getLogger('CryptoArbitrageApp')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('./results/CryptoArbitrageApp.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]',
    datefmt="%Y-%m-%d %H:%M:%S"
)
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)

#########################
## Init arbitrage deals
dealLogger = logging.getLogger('CryptoArbitrageDeals')
dealLogger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('./results/CryptoArbitrageDeals.csv',mode='w')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s,%(message)s',datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
dealLogger.addHandler(fh)
dealLogger.addHandler(ch)
dealLogger.info('timestamp,vol_BTC,profit_perc,nodes,price,age,nofTotalTransactions,nofIntraexchangeTransactions,exchangesInvolved,nofExchangesInvolved,tradingStrategyApproved,limitPrice,uuid')

###################
## Init trader logger
logger = logging.getLogger('Trader')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('./results/Trader.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]',
    datefmt="%Y-%m-%d %H:%M:%S"
)
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)