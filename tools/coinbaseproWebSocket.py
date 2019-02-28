import cbpro
from decimal import *
import logging
import sys
import dateutil.parser
import time
from multiprocessing import Process, Event

# Init logger
logger = logging.getLogger('coinbaseproTestLogger')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]',
    datefmt="%Y-%m-%d %H:%M:%S"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


class CryptoArbOrderBook(cbpro.OrderBook):
    def __init__(self, maxEntryCount=10, timeLimiterSeconds=0.05,product_id='BTC-USD', log_to=None):
        self.maxEntryCount = maxEntryCount
        self.asksConsolidatedOld = []
        self.bidsConsolidatedOld = []
        self.timeLastRun = time.time()
        self.timeLimiterSeconds = timeLimiterSeconds
        return super().__init__(product_id=product_id, log_to=log_to)

    def on_message(self, message):
        if (time.time() - self.timeLastRun) < self.timeLimiterSeconds:
            return super().on_message(message)
        try:
            book = self.get_current_book()
            if len(book["asks"])>0 and len(book["bids"])>0:
                asksConsolidated = self.getConsolidatedOrderbook(book["asks"], reverse=False)
                bidsConsolidated = self.getConsolidatedOrderbook(book["bids"], reverse=True)
                print("asks:"+str(asksConsolidated)+", bids:"+str(bidsConsolidated))

                if self.asksConsolidatedOld != asksConsolidated or self.bidsConsolidatedOld != bidsConsolidated:
                    payload = {}
                    payload['exchange'] = "coinbasepro"
                    payload['symbol'] = message['product_id'].replace('-','/')
                    payload['data'] = {}
                    payload['data']['asks'] = asksConsolidated
                    payload['data']['bids'] = bidsConsolidated
                    payload['timestamp'] = time.mktime(dateutil.parser.parse(message['time']).timetuple())
                    logger.info("Received " + payload['symbol'] + " prices from coinbasepro")
                    self.asksConsolidatedOld = asksConsolidated
                    self.bidsConsolidatedOld = bidsConsolidated

                if book["asks"][0][0]<=book["bids"][-1][0]:
                    logger.error("Bid higher than ask")
        except Exception as err:
            logger.error("Error during message processing:" + str(err))
        finally:
            self.timeLastRun = time.time()
            return super().on_message(message)

    def getConsolidatedOrderbook(self, entries, reverse=False):
        orderbook = []
        
        size = Decimal(0)
        sizeAccumulator = 0

        if reverse:
            price = entries[-1][0]
            entries = reversed(entries)
        else:
            price = entries[0][0]

        for entry in entries:
            if entry[0] == price:
                size += entry[1]
            else:
                orderbook.append([float(price), float(size)])
                sizeAccumulator += size
                if len(orderbook) >= self.maxEntryCount:
                    break
                price = entry[0]
                size = entry[1]
        
        return orderbook
        
def CryptoArbOrderBookProcess(pair,stopProcessesEvent):
    orderbook=CryptoArbOrderBook(product_id=pair.replace('/', '-'))
    orderbook.start()
    stopProcessesEvent.wait()
    orderbook.close()

pairs = ['BCH/BTC', 'BTC/EUR', 'LTC/EUR', 'BTC/USD', 'BTC/EUR', 'ETH/USD','ETH/EUR', 'BCH/EUR', 'ETH/BTC', 'BCH/USD']

stopProcessesEvent = Event()
processes = [Process(target=CryptoArbOrderBookProcess, args=(pair,stopProcessesEvent)) for pair in pairs]

# start order books
for process in processes:
    process.daemon = True
    process.start()

input("Press Enter to stop")

stopProcessesEvent.set()
for process in processes:
    process.join()

logger.info("coinbaseproWebsocket exited normally. Bye.")


