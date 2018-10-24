import pandas as pd
import numpy as np

from OrderRequest import OrderRequest, OrderRequestList, OrderRequestType, SegmentedOrderRequestList
class TradeList(list):
    def __init__(self, iterable):
        super().__init__(iterable)
        self.profit = None
        

class ArbitrageGraphPath:
    def __init__(self,
                 gdict,
                 nodes,
                 timestamp,
                 isNegativeCycle=None,
                 length=None):
        edges_weight = []
        edges_volumeBase = []
        edges_weight_log = []
        edges_weight_limit = []
        edges_age_s = []
        edges_volumeQuote = []
        exchanges_involved = []
        hops = 0
        nof_exchanges_involved = 0

        if nodes != None:
            for i, node in enumerate(nodes[:-1]):
                source = node.split('-')
                target = nodes[(i + 1) % len(nodes)].split('-')

                if len(source) != 2 or len(target) != 2:
                    raise ValueError("Nodes list format error.")

                exchanges_involved.append(source[0])
                exchanges_involved.append(target[0])

                if not ((source[0], source[1]),
                        (target[0], target[1])) in gdict.keys():
                    raise ValueError("Path non-existent in graph")

                v = gdict[((source[0], source[1]), (target[0], target[1]))]
                if v.timestamp is not None:
                    if timestamp - v.timestamp > v.timeToLive:
                        raise ValueError("Path used to exist but TTL expired")
                    edges_age_s.append(timestamp - v.timestamp)
                else:
                    edges_age_s.append(0)
                edges_weight_log.append(v.getLogPrice())
                edges_weight.append(v.getPrice())
                edges_weight_limit.append(v.limitPrice)
                edges_volumeBase.append(v.volumeBase)
                edges_volumeQuote.append(v.volumeQuote)
            exchanges_involved = sorted(set(exchanges_involved), key=str.lower)
            nof_exchanges_involved = len(exchanges_involved)
            hops = len(nodes) - 1

        self.edges_weight_log = edges_weight_log
        self.edges_weight = edges_weight
        self.edges_age_s = edges_age_s
        self.edges_weight_limit = edges_weight_limit
        self.edges_volumeBase = edges_volumeBase
        self.edges_volumeQuote = edges_volumeQuote

        self.hops = hops
        self.exchanges_involved = exchanges_involved
        self.nof_exchanges_involved = nof_exchanges_involved
        self.isNegativeCycle = isNegativeCycle
        self.length = length        
        self.profit = np.exp(-1.0 * self.length) * 1 - 1 if self.length is not None else None
        self.nodes = nodes

    def toDataFrameLog(self, id, timestamp, vol_BTC, df_columns):
        df_new = pd.DataFrame([[
            int(id), timestamp,
            float(vol_BTC), self.length,
            np.exp(-1.0 * self.length) * 100 - 100,
            ",".join(str(x) for x in self.nodes),
            ",".join(str(x) for x in self.edges_weight),
            ",".join(str(x) for x in self.edges_age_s), 
            self.hops, ",".join(str(x) for x in self.exchanges_involved), 
            self.nof_exchanges_involved
        ]],columns=df_columns)
        return df_new

    def toOrderList(self):
        orl = []
        
        #orl.profit = self.profit
        for idx_node, node in enumerate(self.nodes[:-1]):
            base_exchange = node.split('-')[0]
            base_symbol = node.split('-')[1]
            quote_exchange = self.nodes[idx_node + 1].split('-')[0]
            quote_symbol = self.nodes[idx_node + 1].split('-')[1]
            if base_exchange == quote_exchange:
                A = base_symbol
                B = quote_symbol

                if A == 'EUR' or A == 'USD' or A == 'GBP':
                    tradesymbols = B + "/" + A
                    limitPrice = 1 / self.edges_weight_limit[idx_node]
                    tradetype = OrderRequestType.BUY
                    volume = self.edges_volumeQuote[idx_node]
                elif A == 'BTC' and B != 'EUR' and B != 'USD' and B != 'GBP':
                    tradesymbols = B + "/" + A
                    limitPrice = 1 / self.edges_weight_limit[idx_node]
                    tradetype = OrderRequestType.BUY
                    volume = self.edges_volumeQuote[idx_node]
                elif A == 'ETH' and B != 'EUR' and B != 'USD' and B != 'GBP' and B != 'BTC':
                    tradesymbols = B + "/" + A
                    limitPrice = 1 / self.edges_weight_limit[idx_node]
                    tradetype = OrderRequestType.BUY
                    volume = self.edges_volumeQuote[idx_node]
                else:
                    tradesymbols = A + "/" + B
                    limitPrice = self.edges_weight_limit[idx_node]
                    tradetype = OrderRequestType.SELL
                    volume = self.edges_volumeBase[idx_node]

                orl.append(OrderRequest(
                        exchange_name=base_exchange,
                        market=tradesymbols,
                        amount=volume,
                        price=limitPrice,
                        requestType=tradetype))
        return OrderRequestList(orl)

    @staticmethod
    def isOrderListSingleExchange(orderRequestList):
        exchange_name = orderRequestList[0].exchange_name
        for orderRequest in orderRequestList:
            if orderRequest.exchange_name != exchange_name:
                return False
        return True

    def toSegmentedOrderList(self):
        orderList = self.toOrderList().getOrderRequests()
        if len(orderList) == 0:
            raise ValueError("Trade list is empty, there are no trades to execute")

        if ArbitrageGraphPath.isOrderListSingleExchange(orderList) == True:
            return SegmentedOrderRequestList([orderList])

        segmentedOrderList = []
        orderListCurrentSegment = []

        for idx, order in enumerate(orderList[:-1]):
            nextOrder = orderList[idx + 1]            
            if order.exchange_name == nextOrder.exchange_name:
                orderListCurrentSegment.append(order)
            else:
                orderListCurrentSegment.append(order)
                segmentedOrderList.append(OrderRequestList(orderListCurrentSegment))
                orderListCurrentSegment = []

        order = orderList[-1]
        orderListCurrentSegment.append(order)
        segmentedOrderList.append(OrderRequestList(orderListCurrentSegment))
        
        # Merge last segment and the first segment?
        if segmentedOrderList[0].getOrderRequests()[0].exchange_name == segmentedOrderList[-1].getOrderRequests()[-1].exchange_name: 
            mergedOrderList = segmentedOrderList[-1].getOrderRequests()
            mergedOrderList.extend(segmentedOrderList[0].getOrderRequests())
            del segmentedOrderList[0]
            del segmentedOrderList[-1]
            segmentedOrderList = [OrderRequestList(mergedOrderList)] + segmentedOrderList

        return SegmentedOrderRequestList(segmentedOrderList)

