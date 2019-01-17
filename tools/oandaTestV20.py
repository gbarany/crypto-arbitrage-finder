import asyncio
import aiohttp
import json

async def pollForex(symbols, authkey):
    i = 0
    while True:
        symbol = symbols[i % len(symbols)]
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        url="https://api-fxpractice.oanda.com/v3/accounts/101-004-8785730-001/pricing",
                        headers={'Authorization': ('Bearer ' + authkey)},
                        params='instruments=' + symbol) as resp:
                    yield (await resp.json())
        except Exception as error:
            print("Fetch forex rates from Oanda: " + type(error).__name__ + " " + str(error.args))
            
        i += 1
        await asyncio.sleep(1)

async def forexPoller(symbols, authkey, orderbookAnalyser):
    async for ticker in pollForex(symbols=symbols, authkey=authkey):
        symbolBase = ticker['prices'][0]['instrument'].split("_")[0]
        symbolQuote = ticker['prices'][0]['instrument'].split("_")[1]
        asks = ticker['prices'][0]['asks']
        bids = ticker['prices'][0]['bids']
        print("Received " + symbolBase+"/"+ symbolQuote +
                    " prices from Oanda. Ask: " + str(asks) + ", Bid: " + str(bids))
        #orderbookAnalyser.updateForexPrice(ticker['prices'][0])

with open('./cred/oanda.json') as file:
    authkeys = json.load(file)
    asyncio.ensure_future(
        forexPoller(
            symbols=['EUR_USD', 'GBP_USD'],
            authkey=authkeys['practice'],
            orderbookAnalyser=None))
    loop = asyncio.get_event_loop()      
    loop.run_forever()
