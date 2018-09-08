class Trade:
    STATUS_INITIAL = "STATUS_INITIAL"
    STATUS_CREATED = "STATUS_CREATED"
    STATUS_EXECUTED = "STATUS_EXECUTED "
    STATUS_FAILED = "STATUS_FAILED"

    BUY_ORDER = "BUY_ORDER"
    SELL_ORDER = "SELL_ORDER"

    def __init__(self,exchangeName,symbol,amount,price,tradetype):
        self.exchangeName=exchangeName
        self.exchangeNameStd=exchangeName.lower().replace(" ","")        
        self.symbol=symbol
        self.amount=amount
        self.price=price
        self.tradetype=tradetype
        self.status = Trade.STATUS_INITIAL
        self.id = None

        self.timestamp = None
        self.datetime = None
        self.cost = None
        self.filled = None
        self.remaining = None