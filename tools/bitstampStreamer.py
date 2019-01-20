import pysher
import time
import json
import logging
import sys
from functools import partial

# Init logger
logger = logging.getLogger('oandaTestLogger')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]',
    datefmt="%Y-%m-%d %H:%M:%S"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


# Init pusher
pusher = pysher.Pusher(key="de504dc5763aeef9ff52")

def  orderbookHandler(symbols,dataraw):
    data = json.loads(dataraw)
    symbolBase = symbols.upper()[0:3]
    symbolQuote = symbols.upper()[3:]
    payload = {}
    payload['exchange'] = "bitstamp"
    payload['symbol'] = symbolBase + "/" + symbolQuote
    payload['data'] = {}
    payload['data']['asks'] = list(map(lambda entry:[float(entry[0]),float(entry[1])],data['asks']))
    payload['data']['bids'] = list(map(lambda entry:[float(entry[0]),float(entry[1])],data['bids']))
    payload['timestamp'] = float(data['microtimestamp'])/1e6
    logger.info("Received " + symbolBase+"/"+ symbolQuote + " prices from Bitstamp")


def connectHandler(data):
    pairs = ['BTC/EUR', 'ETH/BTC', 'BTC/USD', 'ETH/USD', 'BCH/EUR', 'BCH/BTC',
            'LTC/EUR', 'ETH/EUR', 'XRP/BTC', 'LTC/BTC']

    # subscribe to all the relevant channels
    for pair in pairs:
        pair = pair.lower().replace('/','')
        if pair == 'btcusd':
            channel = pusher.subscribe('order_book')
        else:
            channel = pusher.subscribe('order_book_'+pair)
        channel.bind('data', partial(orderbookHandler,pair))

pusher.connection.bind('pusher:connection_established', connectHandler)
pusher.connect()

# exit app when key pressed
input()