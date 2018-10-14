from FWLiveParams import FWLiveParams
from GraphDB import GraphDB, Asset, TradingRelationship
from InitLogger import logger


class ArbitrageGraphNeo:
    def __init__(self,
                 volumeBTCs,
                 edgeTTL=5,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled,resetDBData=False):

        self.edgeTTL = edgeTTL
        self.volumeBTCs=volumeBTCs

        if neo4j_mode == FWLiveParams.neo4j_mode_aws_cloud:
            self.graphDB = GraphDB(
                uri=FWLiveParams.neo4j_mode_aws_cloud_details['uri'],
                user=FWLiveParams.neo4j_mode_aws_cloud_details['user'],
                password=FWLiveParams.neo4j_mode_aws_cloud_details['password'],
                resetDBData=resetDBData)
        elif neo4j_mode == FWLiveParams.neo4j_mode_localhost:
            self.graphDB = GraphDB(
                uri=FWLiveParams.neo4j_mode_localhost_details['uri'],
                user=FWLiveParams.neo4j_mode_localhost_details['user'],
                password=FWLiveParams.neo4j_mode_localhost_details['password'],
                resetDBData=resetDBData)
        else:
            self.graphDB = None

    def updatePoint(self,symbol, exchange, orderBookPair,now):
        if self.graphDB is None:
            logger.warn('GraphDB is not initialized')
            return

        symbolsplit = symbol.split('/')
        if len(symbolsplit) != 2:
            logger.warn('Symbol %s is invalid parameter'%symbol)
            return

        symbol_base = symbolsplit[0]
        symbol_quote = symbolsplit[1]
        
        self.graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange=exchange, symbol=symbol_quote),
                quotationAsset=Asset(exchange=exchange, symbol=symbol_base),
                orderbook = orderBookPair.getRebasedAsksOrderbook(),
                timeToLiveSec=self.edgeTTL),now=now,
                volumeBTCs=self.volumeBTCs)

        self.graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange=exchange, symbol=symbol_base),
                quotationAsset=Asset(exchange=exchange, symbol=symbol_quote),
                orderbook=orderBookPair.getBidsOrderbook(),
                timeToLiveSec=self.edgeTTL),now=now,
                volumeBTCs=self.volumeBTCs)

        r = self.graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=now)
        logger.info('graphDB arb cycle: ' + str(r))
