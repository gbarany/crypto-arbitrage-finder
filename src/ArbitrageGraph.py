import bellmanford as bf
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import itertools
from ArbitrageGraphPath import ArbitrageGraphPath
from GraphDB import GraphDB, Asset, TradingRelationship
from InitLogger import logger

class ArbitrageGraphEdge:
    def __init__(self,timestamp=None,meanprice=0.0,limitprice=0.0,feeRate=0,vol_BASE=0):
        self.timestamp = timestamp
        self.meanprice = meanprice
        self.limitprice = limitprice
        self.feeRate = feeRate
        self.vol_BASE = vol_BASE

    def getLogWeight(self):
        return -1.0 * np.log((1-self.feeRate)*self.meanprice)

class ArbitrageGraph:
    def __init__(self,edgeTTL=5):
        self.gdict = {}
        self.glist = []
        self.G = nx.DiGraph()
        self.plt_ax = None
        self.negativepath = []
        self.edgeTTL = edgeTTL
        self.graphDB = GraphDB()
        
    def updatePoint(self,symbol,exchangename,feeRate,askPrice,bidPrice,timestamp):
        symbolsplit = symbol.split('/')
        if len(symbolsplit)!=2:
            return 0,[],None

        symbol_base  = (exchangename,symbolsplit[0])
        symbol_quote  = (exchangename,symbolsplit[1])

     
        key1 = (symbol_quote,symbol_base)
        key2 = (symbol_base,symbol_quote)

        def connectSameCurrenciesOnDifferentExchanges(node,uniqueNodes):
            if not node in uniqueNodes:
                for nodeIterator in uniqueNodes:
                    if nodeIterator[1]==node[1]:
                        self.gdict[(node,nodeIterator)] = ArbitrageGraphEdge()
                        self.gdict[(nodeIterator,node)] = ArbitrageGraphEdge()
        
        uniqueNodes = list(set(itertools.chain(*[[s[0],s[1]] for s in self.gdict.keys()])))
        connectSameCurrenciesOnDifferentExchanges(symbol_base,uniqueNodes)
        connectSameCurrenciesOnDifferentExchanges(symbol_quote,uniqueNodes)

        if askPrice.meanprice != None:
            self.gdict[key1] = ArbitrageGraphEdge(timestamp=timestamp,meanprice=1/askPrice.meanprice, limitprice=1/askPrice.limitprice,feeRate=feeRate,vol_BASE=askPrice.vol_BASE*askPrice.meanprice)
        if bidPrice.meanprice != None:
            self.gdict[key2] = ArbitrageGraphEdge(timestamp=timestamp,meanprice=bidPrice.meanprice, limitprice=bidPrice.limitprice,feeRate=feeRate,vol_BASE=bidPrice.vol_BASE)

        self.graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange=key1[0][0], symbol=key1[0][1]),
                    quotationAsset=Asset(exchange=key1[1][0], symbol=key1[1][1]),
                    rate=1,
                    timeToLiveSec=4)
            )
        r = self.graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'))
        logger.info('graphDB arb cycle: '+str(r))
        return self.updateGraph(timestamp=timestamp)

    def updateGraph(self,timestamp):
        self.glist = []
        now = timestamp
        for k, v in self.gdict.items():
            symbol_base = '-'.join(k[0])
            symbol_quote = '-'.join(k[1])
            ts = v.timestamp
            edge = v.getLogWeight()
            if  ts is not None:
                if (now-ts) < self.edgeTTL:
                    self.glist.extend([[symbol_base, symbol_quote,edge]])
            else:
                self.glist.extend([[symbol_base, symbol_quote,edge]])

        if len(self.glist)==0:
            return 0,[],None

        self.G = nx.DiGraph()
        self.G.add_weighted_edges_from(self.glist)
        length, nodes, isNegativeCycle = bf.negative_edge_cycle(self.G)
        self.negativepath = nodes
        
        return ArbitrageGraphPath(
            gdict=self.gdict,
            nodes=nodes,
            timestamp=timestamp,
            edgeTTL_s=self.edgeTTL,
            isNegativeCycle=isNegativeCycle,
            length=length)

    def getPath(self,nodes,timestamp):
        return ArbitrageGraphPath(
            gdict=self.gdict,
            nodes=nodes,
            timestamp=timestamp,
            edgeTTL_s=self.edgeTTL)

    def plotGraph(self,figid=1,vol_BTC=None):
        plt.figure(figid)
        plt.clf()
        plt.title("Throughput Volume %2.3fBTC"%vol_BTC)

        pos=nx.circular_layout(self.G)
        edges = self.G.edges()
        colors = []
        weights = []
        if self.negativepath!=None:
            for u,v in edges:
                try:
                    idx1 = self.negativepath.index(u)
                except:
                    idx1=-1

                idx2 = np.min([idx1+1,len(self.negativepath)-1])
                if idx1!=-1 and self.negativepath[idx2]==v:
                    colors.append('r')
                    weights.append(6)
                else:
                    colors.append('k')
                    weights.append(1)
        else:
            for u,v in edges:
                colors.append('k')
                weights.append(1)

        nx.draw_networkx(self.G,edge_color=colors,ax=plt.gca(),pos=pos,with_labels=True,width=weights)
        labels = nx.get_edge_attributes(self.G,'weight')
        for key in labels.keys():
            labels[key]=round(labels[key],4)
        nx.draw_networkx_edge_labels(self.G,pos=pos,edge_labels=labels,label_pos=0.3,alpha=0.2,font_size=8)
        plt.draw()
        plt.pause(0.001)
