class ArbitrageGraphPath:
    def __init__(self,gdict,nodes,timestamp_now,edgeTTL_s):
        edges_weight = []
        edges_age_s = []
        hops = len(nodes)-1
        exchanges_involved = []

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
            if v[0] is not None:
                if timestamp_now-v[0]>edgeTTL_s:
                    raise ValueError("Path used to exist but TTL expired")
                edges_age_s.append(timestamp_now-v[0])
            else:
                edges_age_s.append(0)
            edges_weight.append(v[1])

        exchanges_involved = sorted(set(exchanges_involved),key=str.lower)
        nof_exchanges_involved = len(exchanges_involved)
        
        self.edges_weight=edges_weight
        self.edges_age_s=edges_age_s
        self.hops=hops
        self.exchanges_involved=exchanges_involved
        self.nof_exchanges_involved=nof_exchanges_involved