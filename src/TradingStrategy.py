class TradingStrategy:
    MIN_PROFIT_LIMIT_PERCENTAGE = 0.5
    MAX_NOF_INTRAEXCHANGE_TRANSACTIONS = 3
    MAX_NOF_INTRAEXCHANGE_TRANSACTIONS_PER_EXCHANGE = 1
    MAX_NOF_TOTAL_TRANSACTIONS = 6
    MAX_NOF_EXCHANGES_INVOLVED = 3
    MAX_TRADING_VOLUME_BTC = 1.1
    MIN_TRADING_VOLUME_BTC = 0.01

    def __init__(self):
        pass

    @staticmethod
    def isDealApproved(path):
        return path.getProfit() >= TradingStrategy.MIN_PROFIT_LIMIT_PERCENTAGE and \
               path.getNofIntraexchangeTransactions() <= TradingStrategy.MAX_NOF_INTRAEXCHANGE_TRANSACTIONS and \
               path.getNofTotalTransactions() <= TradingStrategy.MAX_NOF_TOTAL_TRANSACTIONS and \
               path.getNofExchangesInvolved() <= TradingStrategy.MAX_NOF_EXCHANGES_INVOLVED and \
               path.getVolumeBTC() <= TradingStrategy.MAX_TRADING_VOLUME_BTC and \
               path.getVolumeBTC() >= TradingStrategy.MIN_TRADING_VOLUME_BTC and \
               path.getMaxIntraexchangeTransactionsPerExchange() <= TradingStrategy.MAX_NOF_INTRAEXCHANGE_TRANSACTIONS_PER_EXCHANGE