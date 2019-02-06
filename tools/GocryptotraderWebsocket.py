import asyncio
import websockets
import json
import logging
import sys
import dateutil.parser
import time

# Init logger
logger = logging.getLogger('testLogger')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]',
    datefmt="%Y-%m-%d %H:%M:%S"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


async def gocryptotraderWebSocket():
    async with websockets.connect('ws://18.185.134.222:9050/ws') as ws:
        async for msg in ws:
            try:
                message = json.loads(msg)
                if message['Event'] == 'orderbook_update':
                    symbol = message['Data']['pair']['first_currency']+"/" + message['Data']['pair']['second_currency']
                    payload = dict()
                    payload['exchange'] = message['exchange'].lower()
                    payload['symbol'] = symbol
                    payload['data'] = {}
                    payload['data']['asks'] = list(map(lambda entry: [float(entry['Price']), float(entry['Amount'])], message['Data']['asks']))
                    payload['data']['bids'] = list(map(lambda entry: [float(entry['Price']), float(entry['Amount'])], message['Data']['bids']))
                    payload['timestamp'] = time.mktime(dateutil.parser.parse(message['Data']['last_updated']).timetuple())
                    logger.info("Received " + symbol + " prices from "+message['exchange'].lower())
            except Exception as error:
                logger.warning("Error while parsing websocket data: " + type(error).__name__ + " " + str(error.args))

asyncio.get_event_loop().run_until_complete(gocryptotraderWebSocket())