import cbpro
import sys
import time
import datetime as dt
import dateutil.parser
import logging

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

## OrdebookConverter

class OrderBookConverter(cbpro.OrderBook):

    def __init__(self, product_id=None,orderbookLimit=100):
        super(OrderBookConverter, self).__init__(product_id=product_id)
        self.orderbookLimit=orderbookLimit
        self.asks = None
        self.bids = None

    def on_message(self, message):
        super(OrderBookConverter, self).on_message(message)


        orderbookSnapshot = self.get_current_book()
        asks_new = list(map(lambda entry:[float(entry[0]),float(entry[1])],orderbookSnapshot['asks'][0:self.orderbookLimit]))
        bids_new = list(map(lambda entry:[float(entry[0]),float(entry[1])],reversed(orderbookSnapshot['bids'][-self.orderbookLimit:])))

        # send update only if there's a change in the relevant part of the orderbook
        if asks_new!=self.asks or bids_new!=self.bids:
            self.asks = asks_new
            self.bids = bids_new
            symbol = message['product_id'].replace('-','/')
            payload = {}
            payload['exchange'] = "coinbasepro"
            payload['symbol'] = symbol
            payload['data'] = {}
            payload['data']['asks'] = asks_new
            payload['data']['bids'] = bids_new
            payload['timestamp'] = time.mktime(dateutil.parser.parse(message['time']).timetuple())
            logger.info("Received " + symbol + " prices from coinbasepro : " + str(asks_new[0][0]))

symbols = ['BTC-USD','ETH-USD']
order_books = []
for symbol in symbols:
    order_book = OrderBookConverter(product_id=symbol)
    order_book.start()
    order_books.append(order_book)

try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    for order_book in order_books:
        order_book.close()


if order_book.error:
    sys.exit(1)
else:
    sys.exit(0)