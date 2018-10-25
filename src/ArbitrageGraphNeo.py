from FWLiveParams import FWLiveParams
from GraphDB import GraphDB
from OrderBook import Asset
from InitLogger import logger


class ArbitrageGraphNeo:
    def __init__(self,volumeBTCs,neo4j_mode=FWLiveParams.neo4j_mode_disabled,resetDBData=False):

        self.volumeBTCs=volumeBTCs

        if neo4j_mode == FWLiveParams.neo4j_mode_aws_cloud:
            cred=FWLiveParams.getNeo4jCredentials()
            self.graphDB = GraphDB(
                uri=cred['uri'],
                user=cred['user'],
                password=cred['password'],
                resetDBData=resetDBData)
        elif neo4j_mode == FWLiveParams.neo4j_mode_localhost:
            self.graphDB = GraphDB(
                uri=FWLiveParams.neo4j_mode_localhost_details['uri'],
                user=FWLiveParams.neo4j_mode_localhost_details['user'],
                password=FWLiveParams.neo4j_mode_localhost_details['password'],
                resetDBData=resetDBData)
        else:
            self.graphDB = None

    def updatePoint(self,orderBookPair,volumeBTCs=[1]):
        if self.graphDB is None:
            logger.warn('GraphDB is not initialized')
            return

        now = orderBookPair.getTimestamp()
        
        self.graphDB.addTradingRelationship(orderBook=orderBookPair.getRebasedAsksOrderbook(),volumeBTCs=self.volumeBTCs)

        self.graphDB.addTradingRelationship(orderBook=orderBookPair.bids,volumeBTCs=self.volumeBTCs)

        path = self.graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=now,volumeBTCs=volumeBTCs)

        logger.info('Neo4j arb cycle: ' + str(path))
        return path