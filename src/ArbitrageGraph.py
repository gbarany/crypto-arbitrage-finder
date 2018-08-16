import bellmanford as bf
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
import itertools

class ArbitrageGraph:
    def __init__(self):
        self.gdict = {}
        self.glist = []
        self.G = nx.DiGraph()
        self.plt_ax = None
        self.negativepath = []

    def update_point(self,symbol,exchangename,fee_rate,l_ask,h_bid):   
        symbol_base  = (exchangename,symbol.split('/')[0])
        symbol_quote  = (exchangename,symbol.split('/')[1])

        key1 = (symbol_quote,symbol_base)
        key2 = (symbol_base,symbol_quote)

        def connectSameCurrenciesOnDifferentExchanges(node,uniqueNodes):
            if not node in uniqueNodes:
                for nodeIterator in uniqueNodes:
                    if nodeIterator[1]==node[1]:
                        self.gdict[(node,nodeIterator)] = float(0)
                        self.gdict[(nodeIterator,node)] = float(0)
        
        uniqueNodes = list(set(itertools.chain(*[[s[0],s[1]] for s in self.gdict.keys()])))
        connectSameCurrenciesOnDifferentExchanges(symbol_base,uniqueNodes)
        connectSameCurrenciesOnDifferentExchanges(symbol_quote,uniqueNodes)


        self.gdict[key1] = -1.0 * np.log(float((1-fee_rate)*1/l_ask))
        self.gdict[key2] = -1.0 * np.log(float((1-fee_rate)*h_bid))
        return self.update_graph()

    def nodeslist_to_edges(self,nodes):
        edges = []
        for i, node in enumerate(nodes[:-1]):
            source = node.split('-')
            target = nodes[(i+1)%len(nodes)].split('-')
            edges.append(self.gdict[((source[0],source[1]),(target[0],target[1]))])
        return edges

    def update_graph(self):
        self.glist = []
        for k, v in self.gdict.items():
            symbol_base = '-'.join(k[0])
            symbol_quote = '-'.join(k[1])
            self.glist.extend([[symbol_base, symbol_quote,v]])
        self.G = nx.DiGraph()
        self.G.add_weighted_edges_from(self.glist)
        length, nodes, negative_cycle = bf.negative_edge_cycle(self.G)
        self.negativepath = nodes
        #print("length:",length, ", nodes:",nodes,", negative_cycle:",negative_cycle)
        return length, nodes, negative_cycle

    def plot_graph(self):
        plt.clf()
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
