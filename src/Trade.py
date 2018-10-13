from enum import Enum


class TradeStatus(Enum):
    INITIAL = "STATUS_INITIAL"
    CREATED = "STATUS_CREATED"
    EXECUTED = "STATUS_EXECUTED "
    FAILED = "STATUS_FAILED"


class TradeType(Enum):
    BUY = "BUY_ORDER"
    SELL = "SELL_ORDER"


class Trade:
    STATUS_INITIAL = "STATUS_INITIAL"
    STATUS_CREATED = "STATUS_CREATED"
    STATUS_EXECUTED = "STATUS_EXECUTED "
    STATUS_FAILED = "STATUS_FAILED"

    BUY_ORDER = "BUY_ORDER"
    SELL_ORDER = "SELL_ORDER"

    def __init__(self, exchange, market, amount, price,
                 trade_type: TradeType):
        self.exchangeName = exchange
        self.exchangeNameStd = exchange.lower().replace(" ", "")
        self.market = market
        self.amount = amount
        self.price = price
        self.trade_type: TradeType = trade_type
        self.status: TradeStatus = TradeStatus.INITIAL
        self.id = None

        self.timestamp = None
        self.datetime = None
        self.cost = None
        self.filled = None
        self.remaining = None
