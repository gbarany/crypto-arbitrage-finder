import pandas as pd
import numpy as np

from Trade import Trade

class ArbitrageGraphPath:
    def __init__(self,gdict,nodes,timestamp,edgeTTL_s,isNegativeCycle=None,length=None):
        edges_weight = []
        edges_vol_BASE = []
        edges_weight_log = []
        edges_weight_limit = []
        edges_age_s = []
        exchanges_involved = []
        hops = 0
        nof_exchanges_involved = 0

        if nodes != None:
            for i, node in enumerate(nodes[:-1]):
                source = node.split('-')
                target = nodes[(i+1)%len(nodes)].split('-')
                
                if len(source)!=2 or len(target)!=2:
                    raise ValueError("Nodes list format error.")

                exchanges_involved.append(source[0])
                exchanges_involved.append(target[0])

                if not ((source[0],source[1]),(target[0],target[1])) in gdict.keys():
                    raise ValueError("Path non-existent in graph")

                v=gdict[((source[0],source[1]),(target[0],target[1]))]
                if v.timestamp is not None:
                    if timestamp-v.timestamp>edgeTTL_s:
                        raise ValueError("Path used to exist but TTL expired")
                    edges_age_s.append(timestamp-v.timestamp)
                else:
                    edges_age_s.append(0)
                edges_weight_log.append(v.getLogWeight())
                edges_weight.append(v.meanprice)
                edges_weight_limit.append(v.limitprice)
                edges_vol_BASE.append(v.vol_BASE)
            exchanges_involved = sorted(set(exchanges_involved),key=str.lower)
            nof_exchanges_involved = len(exchanges_involved)
            hops = len(nodes)-1

        self.edges_weight_log=edges_weight_log
        self.edges_weight=edges_weight
        self.edges_age_s=edges_age_s
        self.edges_weight_limit=edges_weight_limit
        self.edges_vol_BASE=edges_vol_BASE
        self.hops=hops
        self.exchanges_involved=exchanges_involved
        self.nof_exchanges_involved=nof_exchanges_involved
        self.isNegativeCycle = isNegativeCycle
        self.length = length
        self.nodes = nodes
    
    def toDataFrameLog(self,id,timestamp,vol_BTC,df_columns):
        df_new = pd.DataFrame([[
            int(id),
            timestamp,
            float(vol_BTC),
            self.length,
            np.exp(-1.0*self.length)*100-100,
            ",".join(str(x) for x in self.nodes),
            ",".join(str(x) for x in self.edges_weight),
            ",".join(str(x) for x in self.edges_age_s),
            self.hops,
            ",".join(str(x) for x in self.exchanges_involved),
            self.nof_exchanges_involved]],
            columns=df_columns)
        return df_new
        
    def toTradeList(self):
        tradelist = []                        
        for idx_node,node in enumerate(self.nodes[:-1]):
            base_exchange = node.split('-')[0]
            base_symbol = node.split('-')[1]
            quote_exchange = self.nodes[idx_node+1].split('-')[0]
            quote_symbol = self.nodes[idx_node+1].split('-')[1]
            if base_exchange == quote_exchange:
                A = base_symbol
                B = quote_symbol
                
                if A == 'EUR' or A =='USD' or A =='GBP':
                    tradesymbols = B+"/"+A
                    limitprice = 1/self.edges_weight_limit[idx_node]
                    tradetype = Trade.BUY_ORDER
                    volume = self.edges_vol_BASE[idx_node]*self.edges_weight[idx_node]
                elif A == 'BTC' and B!='EUR' and B!='USD' and B!='GBP':
                    tradesymbols = B+"/"+A
                    limitprice = 1/self.edges_weight_limit[idx_node]
                    tradetype = Trade.BUY_ORDER
                    volume = self.edges_vol_BASE[idx_node]*self.edges_weight[idx_node]
                elif A == 'ETH' and B!='EUR' and B!='USD' and B!='GBP' and B!='BTC' :
                    tradesymbols = B+"/"+A
                    limitprice = 1/self.edges_weight_limit[idx_node]
                    tradetype = Trade.BUY_ORDER
                    volume = self.edges_vol_BASE[idx_node]*self.edges_weight[idx_node]
                else:
                    tradesymbols = A+"/"+B
                    limitprice = self.edges_weight_limit[idx_node]
                    tradetype = Trade.SELL_ORDER
                    volume = self.edges_vol_BASE[idx_node]
                
                tradelist.append(Trade(base_exchange,tradesymbols,volume,limitprice,tradetype))
        return tradelist