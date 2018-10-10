from FWLiveParams import FWLiveParams
from GraphDB import GraphDB, Asset, TradingRelationship
from InitLogger import logger


class ArbitrageGraphNeo:
    def __init__(self,
                 edgeTTL=5,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled,resetDBData=False):

        self.edgeTTL = edgeTTL
        if neo4j_mode == FWLiveParams.neo4j_mode_aws_cloud:
            self.graphDB = GraphDB(
                uri='bolt://3.120.197.59:7687',
                user='neo4j',
                password='i-0b4b0106c20014f75',
                resetDBData=resetDBData)
        elif neo4j_mode == FWLiveParams.neo4j_mode_localhost:
            self.graphDB = GraphDB(
                uri='bolt://localhost:7687',
                user='neo4j',
                password='neo',
                resetDBData=resetDBData)
        else:
            self.graphDB = None

    def updatePoint(self,symbol, exchange, feeRate, orderBookPair,now):
        if self.graphDB is None:
            logger.warn('GraphDB is not initialized')
            return

        symbolsplit = symbol.split('/')
        if len(symbolsplit) != 2:
            logger.warn('Symbol %s is invalid parameter'%symbol)
            return

        symbol_base = symbolsplit[0]
        symbol_quote = symbolsplit[1]

        #askPrice = orderbook.get_ask_price_by_BTC_volume(vol_BTC=1)
        #bidPrice = orderbook.get_bid_price_by_BTC_volume(vol_BTC=1)
        
        self.graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange=exchange, symbol=symbol_quote),
                quotationAsset=Asset(exchange=exchange, symbol=symbol_base),
                #mean_price=1/askPrice.meanprice,
                #limit_price=1/askPrice.limitprice,
                #orderbook=orderbook.get_asks_in_base_str(),
                orderbook = orderBookPair.getRebasedAsksOrderbook(),
                feeRate=feeRate,
                timeToLiveSec=self.edgeTTL),now=now)

        self.graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange=exchange, symbol=symbol_base),
                quotationAsset=Asset(exchange=exchange, symbol=symbol_quote),
                #mean_price=bidPrice.meanprice,
                #limit_price=bidPrice.limitprice,
                #orderbook=orderbook.get_bids_str(),
                orderbook=orderBookPair.getBidsOrderbook(),
                feeRate=feeRate,
                timeToLiveSec=self.edgeTTL),now=now)

        r = self.graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=now)
        logger.info('graphDB arb cycle: ' + str(r))
