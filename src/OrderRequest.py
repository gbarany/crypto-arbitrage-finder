import time
from enum import Enum
# from json import JSONEncoder
import jsonpickle

CCXT_ORDER_STATUS_OPEN = "open"
CCXT_ORDER_STATUS_CLOSED = "closed"
CCXT_ORDER_STATUS_CANCELED = "canceled"


class OrderRequestStatus(Enum):
    INITIAL = "STATUS_INITIAL"
    FAILED = "STATUS_FAILED"
    CREATED = "STATUS_CREATED"
    OPEN = "STATUS_OPEN"
    CLOSED = "STATUS_CLOSED"
    CANCELED = "STATUS_CANCELED"
    CREATING = "STATUS_CREATING"


class OrderRequestType(Enum):
    BUY = "BUY_ORDER"
    SELL = "SELL_ORDER"


class OrderRequest:

    def __init__(self, exchange_name: str, market: str, amount: float, price: float,
                 requestType: OrderRequestType) -> None:
        self.exchange_name: str = exchange_name
        self.exchange_name_std: str = exchange_name.lower().replace(" ", "")
        self.market: str = market
        self.amount: float = amount
        self.price: float = price
        self.type: OrderRequestType = requestType
        self.__status: OrderRequestStatus
        self.__statusLog: [] = []
        self.id = None
        self.order_from_ccxt = None

        self.timestamp = None
        self.datetime = None
        self.cost = None
        self.filled = None
        self.remaining = None

        self.setStatus(OrderRequestStatus.INITIAL)

    def setStatus(self, status: OrderRequestStatus):
        self.__status = status
        self.__logStatus(status)

    def getStatus(self) -> OrderRequestStatus:
        return self.__status

    def __logStatus(self, status: OrderRequestStatus):
        now = time.time()
        d = 0 if len(self.__statusLog) == 0 else now - self.__statusLog[-1]['time']
        self.__statusLog.append({
            'time': now,
            'dtime': d,
            'status': status
        })

    def getStatusLog(self):
        return self.__statusLog

    def setOrder(self, order_from_ccxt):
        status = order_from_ccxt['status']
        if status == 'open':
            self.setStatus(OrderRequestStatus.OPEN)
        elif status == 'closed':
            self.setStatus(OrderRequestStatus.CLOSED)
        elif status == 'canceled':
            self.setStatus(OrderRequestStatus.CANCELED)
        else:
            raise ValueError(f'Order from ccxt ({order_from_ccxt}) has invalid status: {status}')
        self.order_from_ccxt = order_from_ccxt

    def isAlive(self) -> bool:
        '''
            True: The order request is might be in the exchange
        '''
        return self.getStatus() not in [OrderRequestStatus.INITIAL, OrderRequestStatus.FAILED,
                                        OrderRequestStatus.CLOSED]

    def setCanceled(self):
        self.setStatus(OrderRequestStatus.CANCELED)

    def as_string(self) -> str:
        return jsonpickle.encode(self)


class OrderRequestList:

    def __init__(self, orderRequests: [OrderRequest]):
        self.__orderRequests: [OrderRequest] = orderRequests

    def getOrderRequests(self) -> [OrderRequest]:
        return self.__orderRequests


class SegmentedOrderRequestList:

    def __init__(self, orderRequestLists: [OrderRequestList]):
        self.__orderRequestsLists: [OrderRequestList] = orderRequestLists

    def getOrderRequestLists(self) -> [OrderRequestList]:
        return self.__orderRequestsLists

    def getOrderRequests(self) -> [OrderRequest]:
        ret: [OrderRequest] = []
        for l in self.__orderRequestsLists:
            ret += l.getOrderRequests()
        return ret

    def logStatusLogs(self):
        log = []
        for orderRequest in self.getOrderRequests():
            for logEntry in orderRequest.getStatusLog():
                log.append({
                    'id': orderRequest.id,
                    'status': logEntry['status'],
                    'time': logEntry['time'],
                    'dtime': logEntry['dtime']
                })
        return log