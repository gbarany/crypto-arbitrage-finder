import bellmanford as bf
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import itertools
from ArbitragePath import ArbitragePath
from OrderBook import OrderBookPrice, Asset
from FWLiveParams import FWLiveParams


class ArbitrageGraph:
    def __init__(self):

        self.gdict = {}
        self.glist = []
        self.G = nx.DiGraph()
        self.plt_ax = None
        self.negativepath = []

    def updatePoint(self, orderBookPair, volumeBTC):
        askOrderbookPrice = orderBookPair.asks.getPriceByBTCVolume(volumeBTC=volumeBTC)
        askOrderbookPriceRebased = orderBookPair.asks.getRebasedOrderbook().getPriceByBTCVolume(volumeBTC=volumeBTC)
        bidOrderbookPrice = orderBookPair.bids.getPriceByBTCVolume(volumeBTC=volumeBTC)


        symbol_base = (orderBookPair.getExchange(), orderBookPair.getSymbolBase())
        symbol_quote = (orderBookPair.getExchange(), orderBookPair.getSymbolQuote())

        key1 = (symbol_quote, symbol_base)
        key2 = (symbol_base, symbol_quote)

        def connectSameCurrenciesOnDifferentExchanges(node, uniqueNodes):
            if node not in uniqueNodes:
                for nodeIterator in uniqueNodes:
                    if nodeIterator[1] == node[1]:
                        self.gdict[(node, nodeIterator)] = OrderBookPrice(timestamp=None,meanPrice=1, limitPrice=1, volumeBase=None,volumeBTC=None,feeRate=0)
                        self.gdict[(nodeIterator, node)] = OrderBookPrice(timestamp=None,meanPrice=1, limitPrice=1, volumeBase=None,volumeBTC=None,feeRate=0)

        uniqueNodes = list(
            set(itertools.chain(*[[s[0], s[1]] for s in self.gdict.keys()])))
        connectSameCurrenciesOnDifferentExchanges(symbol_base, uniqueNodes)
        connectSameCurrenciesOnDifferentExchanges(symbol_quote, uniqueNodes)

        if askOrderbookPrice.meanPrice is not None:
            self.gdict[key1] = askOrderbookPriceRebased
        if bidOrderbookPrice.meanPrice is not None:
            self.gdict[key2] = bidOrderbookPrice

    def getArbitrageDeal(self, timestamp):
        self.glist = []
        now = timestamp
        for k, v in self.gdict.items():
            symbol_base = '-'.join(k[0])
            symbol_quote = '-'.join(k[1])
            ts = v.timestamp
            edge = v.getLogPrice()
            edgeTTL = v.getTimeToLive()
            if ts is not None:
                if (now - ts) < edgeTTL:
                    self.glist.extend([[symbol_base, symbol_quote, edge]])
            else:
                self.glist.extend([[symbol_base, symbol_quote, edge]])

        if len(self.glist) == 0:
            return 0, [], None

        self.G = nx.DiGraph()
        self.G.add_weighted_edges_from(self.glist)
        _, nodes, _ = bf.negative_edge_cycle(self.G)
        self.negativepath = nodes

        return self.getPath(nodes=nodes,timestamp=timestamp)

    def getPath(self, nodes, timestamp):
        ## fetch information for the node path
        orderBookPriceList = []
        nodesList = []
        if nodes != None:
            for i, node in enumerate(nodes[:-1]):
                source = node.split('-')
                target = nodes[(i + 1) % len(nodes)].split('-')
                
                if len(source) != 2 or len(target) != 2:
                    raise ValueError("Nodes list format error.")
                
                if not ((source[0], source[1]),(target[0], target[1])) in self.gdict.keys():
                    raise ValueError("Path non-existent in graph")
                
                nodesList.append(Asset(exchange=source[0],symbol=source[1]))
                orderBookPrice = self.gdict[((source[0], source[1]), (target[0], target[1]))]
                if orderBookPrice.timestamp is not None:
                    if timestamp - orderBookPrice.timestamp > orderBookPrice.timeToLive:
                        raise ValueError("Path used to exist but TTL expired")

                orderBookPriceList.append(orderBookPrice)
            # add the last node that closes the cycle
            nodesList.append(Asset(exchange=nodes[-1].split('-')[0],symbol=nodes[-1].split('-')[1]))

        return ArbitragePath(
            nodesList=nodesList,
            timestamp=timestamp,
            orderBookPriceList=orderBookPriceList)

    def plotGraph(self, figid=1, vol_BTC=None):
        plt.figure(figid)
        plt.clf()
        plt.title("Throughput Volume %2.3fBTC" % vol_BTC)

        pos = nx.circular_layout(self.G)
        edges = self.G.edges()
        colors = []
        weights = []
        if self.negativepath is not None:
            for u, v in edges:
                try:
                    idx1 = self.negativepath.index(u)
                except:
                    idx1 = -1

                idx2 = np.min([idx1 + 1, len(self.negativepath) - 1])
                if idx1 != -1 and self.negativepath[idx2] == v:
                    colors.append('r')
                    weights.append(6)
                else:
                    colors.append('k')
                    weights.append(1)
        else:
            for u, v in edges:
                colors.append('k')
                weights.append(1)

        nx.draw_networkx(
            self.G,
            edge_color=colors,
            ax=plt.gca(),
            pos=pos,
            with_labels=True,
            width=weights)
        labels = nx.get_edge_attributes(self.G, 'weight')
        for key in labels.keys():
            labels[key] = round(labels[key], 4)
        nx.draw_networkx_edge_labels(
            self.G,
            pos=pos,
            edge_labels=labels,
            label_pos=0.3,
            alpha=0.2,
            font_size=8)
        plt.draw()
        plt.pause(0.001)
