import time
from enum import Enum
import json
import jsonpickle
from Database import Database
from datetime import datetime

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
    """ The order should be canceled """
    shouldAbort: bool

    def __init__(self, exchange_name: str, market: str, volumeBase: float, limitPrice: float, meanPrice: float,
                 requestType: OrderRequestType) -> None:
        self.exchange_name: str = exchange_name
        self.exchange_name_std: str = exchange_name.lower().replace(" ", "")
        self.market: str = market
        self.volumeBase: float = volumeBase
        self.limitPrice: float = limitPrice
        self.meanPrice: float = meanPrice
        self.type: OrderRequestType = requestType

        self.__statusLog: [] = []
        self.id = None
        self.order_from_ccxt = None

        self.timestamp = None
        self.datetime = None
        self.cost = None
        self.filled = None
        self.remaining = None

        self.shouldAbort = False
        self.__status: OrderRequestStatus = OrderRequestStatus.INITIAL
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

    def updateOrderStatusFromCCXT(self, order_from_ccxt):
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

    def isPending(self) -> bool:
        '''
            True: The order request is might be in the exchange
        '''
        return self.getStatus() in [OrderRequestStatus.CREATING, OrderRequestStatus.CREATED, OrderRequestStatus.OPEN]

    def setCanceled(self):
        self.setStatus(OrderRequestStatus.CANCELED)

    def toString(self) -> str:
        obj = {
            'id': self.id,
            'exchange_name': self.exchange_name,
            'market': self.market,
            'volumeBase': self.volumeBase,
            'limitPrice': self.limitPrice,
            'meanPrice': self.meanPrice,
            'type': self.type.value,
            'status': self.__status.value,
        }
        if self.shouldAbort:
            obj['shouldAbort'] = self.shouldAbort
        return jsonpickle.encode(obj)

    def __str__(self):
        return self.toString()

    def saveToDb(self, db, uuid):
        query = "INSERT INTO `arbitrage`" \
                "(uuid, exchange_id, exchange_name, volumeBase, limitPrice, symbol, meanPrice, shouldAbort, status, `type`, json)" \
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s, %s,%s,%s)"
        args = (
            uuid,
            self.id,
            self.exchange_name,
            self.volumeBase,
            self.limitPrice,
            self.market,
            self.meanPrice,
            1 if self.shouldAbort else 0,
            self.__status.value,
            self.type.value,
            self.toString()
        )

        cursor = db.cursor()
        cursor.execute(query, args)
        if cursor.lastrowid:
            if cursor.lastrowid % 100 == 0:
                print('last insert id', cursor.lastrowid)

        db.commit()


class OrderRequestList:

    def __init__(self, orderRequests: [OrderRequest]):
        self.__orderRequests: [OrderRequest] = orderRequests

    def getOrderRequests(self) -> [OrderRequest]:
        return self.__orderRequests


class SegmentedOrderRequestList:

    def __init__(self, uuid: str, orderRequestLists: [OrderRequestList]):
        self.uuid: str = uuid
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
                    'exchange_name': orderRequest.exchange_name,
                    'exchange_id': orderRequest.id,
                    'status': logEntry['status'].value,
                    'time': logEntry['time'],
                    'dtime': logEntry['dtime']
                })
        return log

    def statusLogToString(self):
        log = self.logStatusLogs()
        ret = ""
        for l in log:
            ret = ret + f"{l}\n"
        return ret

    def sorlToString(self):
        r = f'uuid: {self.uuid}\n'
        for orderRequest in self.getOrderRequests():
            r = r + orderRequest.toString() + "\n"
        return r

    def saveToDB(self):
        db = Database.initDBFromAWSParameterStore()

        query = "INSERT INTO `uuid`" \
                "(uuid, txt)" \
                "VALUES(%s,%s)"
        args = (
            self.uuid,
            f"{self.sorlToString()}\n\n{self.statusLogToString()}"
        )
        cursor = db.cursor()
        cursor.execute(query, args)

        db.commit()

        for orderRequest in self.getOrderRequests():
            orderRequest.saveToDb(db, self.uuid)

        self.__saveHistoryToDB(db)
        db.close()

    def __saveHistoryToDB(self, db):
        log = self.logStatusLogs()

        for l in log:
            query = "INSERT INTO `arbitrage_history`" \
                    "(uuid, exchange_name, exchange_id, status, `time`, dtime)" \
                    "VALUES(%s,%s,%s,%s,%s,%s)"
            args = (
                self.uuid,
                l['exchange_name'],
                l['exchange_id'],
                l['status'],
                datetime.fromtimestamp(l['time']).strftime('%Y-%m-%d %H:%M:%S'),
                l['dtime']
            )
            cursor = db.cursor()
            cursor.execute(query, args)

        db.commit()
