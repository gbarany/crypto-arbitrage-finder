from FWLiveParams import FWLiveParams
from GraphDB import GraphDB, Asset, TradingRelationship
from InitLogger import logger

class ArbitrageGraphNeo:
    def __init__(self,
                 edgeTTL=5,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled):

        self.edgeTTL = edgeTTL
        if neo4j_mode == FWLiveParams.neo4j_mode_aws_cloud:
            self.graphDB = GraphDB(
                uri='bolt://3.120.197.59:7687',
                user='neo4j',
                password='i-0b4b0106c20014f75')
        elif neo4j_mode == FWLiveParams.neo4j_mode_localhost:
            self.graphDB = GraphDB(
                uri='bolt://localhost:7687',
                user='neo4j',
                password='neo')
        else:
            self.graphDB = None

    def updatePoint(self,symbol, exchange_name, fee_rate, orderbook):
        if self.graphDB is None:
            return

        symbolsplit = symbol.split('/')
        if len(symbolsplit) != 2:
            return

        symbol_base = symbolsplit[0]
        symbol_quote = symbolsplit[1]

        askPrice = orderbook.get_ask_price_by_BTC_volume(vol_BTC=1)
        bidPrice = orderbook.get_bid_price_by_BTC_volume(vol_BTC=1)

        self.graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange=exchange_name, symbol=symbol_quote),
                quotationAsset=Asset(exchange=exchange_name, symbol=symbol_base),
                mean_price=1/askPrice.meanprice,
                limit_price=1/askPrice.limitprice,
                orderbook=orderbook.get_asks_in_base_str(),
                fee=fee_rate,
                timeToLiveSec=self.edgeTTL))

        self.graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange=exchange_name, symbol=symbol_base),
                quotationAsset=Asset(exchange=exchange_name, symbol=symbol_quote),
                mean_price=bidPrice.meanprice,
                limit_price=bidPrice.limitprice,
                orderbook=orderbook.get_bids_str(),
                fee=fee_rate,
                timeToLiveSec=self.edgeTTL))

        r = self.graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'))
        logger.info('graphDB arb cycle: ' + str(r))
