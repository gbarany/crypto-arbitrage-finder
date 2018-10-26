import pandas as pd
import numpy as np

from OrderRequest import OrderRequest, OrderRequestList, OrderRequestType, SegmentedOrderRequestList

class ArbitragePath:
    def __init__(self,nodes,timestamp,orderBookPriceList,isNegativeCycle):

        self.nodes = nodes
        self.timestamp = timestamp
        self.orderBookPriceList = orderBookPriceList
        self.isNegativeCycle = isNegativeCycle

    def getAge(self):
        return list(map(lambda orderBookPrice:self.timestamp-orderBookPrice.timestamp,self.orderBookPriceList))

    def getPrice(self):
        return list(map(lambda orderBookPrice:orderBookPrice.getPrice(),self.orderBookPriceList))
    
    def getNofHops(self):
        return len(self.nodes) - 1
    
    def getExchangesInvolved(self):
        exchangesList = list(map(lambda node:node.split('-')[0],self.nodes))
        exchangesInvolved = sorted(set(exchangesList), key=str.lower)
        return exchangesInvolved

    def getNofExchangesInvolved(self):
        return len(self.getExchangesInvolved())


    def toDataFrameLog(self, id, timestamp, vol_BTC, df_columns):
        # TODO: fix this
        df_new = pd.DataFrame([])
        '''
        df_new = pd.DataFrame([[
            int(id), timestamp,
            float(vol_BTC),
            np.exp(-1.0 * self.length) * 100 - 100,
            ",".join(str(x) for x in self.nodes),
            ",".join(str(x) for x in self.edges_weight),
            ",".join(str(x) for x in self.edges_age_s), 
            self.hops, ",".join(str(x) for x in self.exchanges_involved), 
            self.nof_exchanges_involved
        ]],columns=df_columns)'''
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
                    limitPrice = 1 / self.orderBookPriceList[idx_node].getLimitPrice()
                    tradetype = OrderRequestType.BUY
                    volume = self.orderBookPriceList[idx_node].getVolumeQuote()
                elif A == 'BTC' and B != 'EUR' and B != 'USD' and B != 'GBP':
                    tradesymbols = B + "/" + A
                    limitPrice = 1 / self.orderBookPriceList[idx_node].getLimitPrice()
                    tradetype = OrderRequestType.BUY
                    volume = self.orderBookPriceList[idx_node].getVolumeQuote()
                elif A == 'ETH' and B != 'EUR' and B != 'USD' and B != 'GBP' and B != 'BTC':
                    tradesymbols = B + "/" + A
                    limitPrice = 1 / self.orderBookPriceList[idx_node].getLimitPrice()
                    tradetype = OrderRequestType.BUY
                    volume = self.orderBookPriceList[idx_node].getVolumeQuote()
                else:
                    tradesymbols = A + "/" + B
                    limitPrice = self.orderBookPriceList[idx_node].getLimitPrice()
                    tradetype = OrderRequestType.SELL
                    volume = self.orderBookPriceList[idx_node].getVolumeBase()

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

        if ArbitragePath.isOrderListSingleExchange(orderList) == True:
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

