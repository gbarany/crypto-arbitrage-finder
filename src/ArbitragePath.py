import numpy as np
import json
from OrderRequest import OrderRequest, OrderRequestList, OrderRequestType, SegmentedOrderRequestList
import logging
from functools import reduce

dealLogger = logging.getLogger('CryptoArbitrageDeals')

class ArbitragePath:
    def __init__(self,nodesList,timestamp,orderBookPriceList):

        self.nodesList = nodesList
        self.timestamp = timestamp
        self.orderBookPriceList = orderBookPriceList
        
        if orderBookPriceList is not None and orderBookPriceList:
            self.profit = (reduce((lambda x, y: x*y), [i.getPrice() for i in orderBookPriceList])-1)*100
        else:
            self.profit = None
    
    def __str__(self):
        return ",".join(str(x) for x in self.nodesList)

    def getAge(self):
        return list(map(lambda orderBookPrice:self.timestamp-orderBookPrice.timestamp,self.orderBookPriceList))

    def getPrice(self):
        return list(map(lambda orderBookPrice:orderBookPrice.getPrice(),self.orderBookPriceList))
    
    def getNofHops(self):
        return len(self.nodesList) - 1

    def getProfit(self):
        return self.profit

    def isProfitable(self):
        if self.profit == None:
            return False
        if self.profit <= 0:
            return False        
        return True

    def getVolumeBTC(self):
        volumeBTCs = list(map(lambda orderBookPrice:orderBookPrice.getVolumeBTC(),self.orderBookPriceList))
        assert volumeBTCs.count(volumeBTCs[0]) == len(volumeBTCs) # check that all prices in path were calculated based on the same volume
        return  volumeBTCs[0]
    
    def getExchangesInvolved(self):
        exchangesList = list(map(lambda node:node.getExchange(),self.nodesList))
        exchangesInvolved = sorted(set(exchangesList), key=str.lower)
        return exchangesInvolved

    def getNofExchangesInvolved(self):
        return len(self.getExchangesInvolved())


    def log(self):
        
        def toCSVStr(itemsList):
            return ",".join(str(x) for x in itemsList)

        logJSON = {
            'timestamp':str(self.timestamp),
            'vol_BTC': str(self.getVolumeBTC()),
            'profit_perc': str(0), # Todo: add arbitrageprofithere
            'nodes': toCSVStr(self.nodesList),
            'price':toCSVStr(self.getPrice()),
            'age': toCSVStr(self.getAge()),
            'nofHops': str(self.getNofHops()),
            'exchangesInvolved':toCSVStr(self.getExchangesInvolved()),
            'nofExchangesInvolved':str(self.getNofExchangesInvolved()),
        }

        logStr = ""
        for row in logJSON.values():
            logStr+="\""+row+"\","
        logStr = logStr[:-1]
        dealLogger.info(logStr)

    def toOrderList(self):
        orl = []
        
        #orl.profit = self.profit
        for idx_node, node in enumerate(self.nodesList[:-1]):
            base_exchange = node.getExchange()
            base_symbol = node.getSymbol()
            quote_exchange = self.nodesList[idx_node + 1].getExchange()
            quote_symbol = self.nodesList[idx_node + 1].getSymbol()
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

