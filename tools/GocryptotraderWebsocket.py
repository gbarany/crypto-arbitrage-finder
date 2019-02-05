import asyncio
import pathlib
import ssl
import websockets
import json
import logging
import sys

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
    async with websockets.connect('wss://18.185.134.222:9050') as ws:
        async for message in ws:
            try:
                msg = json.loads(message)
                symbol = msg['recipient'].split('.')[2].upper()
                symbol = symbol[0:3]+"/"+symbol[3:]
                payload = {}
                payload['exchange'] = "gocryptotrader"
                payload['symbol'] = symbol
                payload['data'] = {}
                payload['data']['asks'] = list(map(lambda entry:entry[0:2],msg['payload']['asks']))
                payload['data']['bids'] = list(map(lambda entry:entry[0:2],msg['payload']['bids']))
                payload['timestamp'] = msg['timestamp']/1e9
                logger.info("Received " + symbol +  " prices from gocryptotrader")
            except Exception as error:
                logger.warn("Error while parsing gocryptotrader websocket data: "+ type(error).__name__ + " " + str(error.args))

asyncio.get_event_loop().run_until_complete(gocryptotraderWebSocket())