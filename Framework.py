import asyncio
import ccxt.async as ccxt
import numpy as np
import bellmanford as bf
import networkx as nx
import matplotlib.pyplot as plt
from ArbitrageGraph import ArbitrageGraph
import time

async def poll(exchange,symbols):
    i = 0    
    while True:
        symbol = symbols[i % len(symbols)]
        yield (symbol, await exchange.fetch_order_book(symbol, limit=2))
        i += 1
        await asyncio.sleep(exchange.rateLimit / 1000)


async def main(exchange,symbols,arbitrageGraph):
    async for (symbol, order_book) in poll(exchange,symbols):
        print("Received",symbol, "from",exchange.name)
        #print(symbol, order_book)
        length, nodes, negative_cycle = arbitrageGraph.update_point(
            symbol,
            exchange.name,
            exchange.fees['trading']['taker'],
            order_book['asks'][0][0],
            order_book['bids'][0][0],
            time.time())
        if negative_cycle == True:
            edges=arbitrageGraph.nodeslist_to_edges(nodes)
            print("length:",length,"ratio",np.exp(-length),'nodes',nodes,'edges',edges)
        arbitrageGraph.plot_graph()

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
    exchanges["coinfloor"].fees['trading']['taker']=0.003

    arbitrageGraph = ArbitrageGraph(edgeTTL=5)
    #arbitrageGraph.addInterExchangeLines(symbols)

    for exchange in exchanges.keys():
        asyncio.ensure_future(main(exchanges[exchange],symbols[exchange],arbitrageGraph))

    loop = asyncio.get_event_loop()
    loop.run_forever()