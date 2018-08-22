import asyncio
import ccxt.async_support as ccxt
import numpy as np
import matplotlib.pyplot as plt
import time
from OrderbookAnalyser import OrderbookAnalyser
import threading
async def poll(exchange,symbols):
    i = 0    
    while True:
        symbol = symbols[i % len(symbols)]
        yield (symbol, await exchange.fetch_order_book(symbol, limit=20))
        i += 1
        await asyncio.sleep(exchange.rateLimit / 1000)


async def main(exchange,symbols,orderbookAnalyser):
    id = 0
    async for (symbol, order_book) in poll(exchange,symbols):
        print("Received",symbol, "from",exchange.name)
        orderbookAnalyser.update(
                exchangename=exchange.name,
                symbol = symbol,
                bids = order_book['bids'],
                asks = order_book['asks'],
                id = id,
                timestamp = time.time()
                )
        id += 1
        orderbookAnalyser.plot_graphs()

if __name__ == "__main__":
    
    fig1 = plt.figure(1)
    plt.plot(1,2)
    plt.ion()
    plt.show()
    plt.pause(0.001)

    exchanges = {}
    symbols = {}
    
    exchanges["Poloniex"]=ccxt.poloniex({'enableRateLimit': True})
    symbols["Poloniex"] = ['BTC/USDT','BCH/BTC', 'DASH/BTC','ETC/BTC','ETH/BTC']

    exchanges["Bitfinex"]=ccxt.bitfinex({'enableRateLimit': True})
    symbols["Bitfinex"] = ['BTC/USDT','BCH/BTC', 'DASH/BTC', 'ETC/BTC','ETH/BTC']

    exchanges["Kraken"]=ccxt.kraken({'enableRateLimit': True})
    symbols["Kraken"] = ['BTC/USD','BCH/BTC', 'DASH/BTC', 'ETC/BTC','ETH/BTC']
    
    exchanges["coinfloor"]=ccxt.coinfloor({'enableRateLimit': True})
    symbols["coinfloor"] = ['BTC/USD']

    exchanges["Bitstamp"]=ccxt.bitstamp({'enableRateLimit': True})
    symbols["Bitstamp"] = ['BTC/USD','BCH/BTC', 'ETH/BTC']

    exchanges["Gdax"]=ccxt.gdax({'enableRateLimit': True})
    symbols["Gdax"] = ['BTC/USD','BCH/BTC', 'ETC/BTC','ETH/BTC']

    orderbookAnalyser = OrderbookAnalyser(vol_BTC=[1,0.1,0.01],edgeTTL=7,priceTTL=60)

    for exchange in exchanges.keys():
        asyncio.ensure_future(main(exchanges[exchange],symbols[exchange],orderbookAnalyser))

    def stop_loop():
        input('Press <enter> to stop')
        loop.call_soon_threadsafe(loop.stop)

    loop = asyncio.get_event_loop()
    threading.Thread(target=stop_loop).start()
    loop.run_forever()
    
    orderbookAnalyser.generateExportFilename(list(exchanges.keys()))
    orderbookAnalyser.saveResultsCSV()