from neo4j.v1 import GraphDatabase
import time
import sys
from InitLogger import logger


class Asset:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol

    def getExchange(self):
        return self.exchange

    def getSymbol(self):
        return self.symbol


class AssetState:
    def __init__(self, amount):
        self.amount = amount


class TradingRelationship:
    def __init__(self, baseAsset, quotationAsset, rate, fee, timeToLiveSec):
        self.baseAsset = baseAsset
        self.quotationAsset = quotationAsset
        self.rate = rate
        self.fee = fee
        self.timeToLiveSec = timeToLiveSec

    def getBaseAsset(self):
        return self.baseAsset

    def getQuotationAsset(self):
        return self.quotationAsset

    def getBaseNodeID(self):
        return self.baseAsset.exchange + self.baseAsset.symbol

    def getQuotationNodeID(self):
        return self.quotationAsset.exchange + self.quotationAsset.symbol


class GraphDB(object):
    def __init__(self,
                 uri='bolt://localhost:7687',
                 user='neo4j',
                 password='neo',
                 resetDBData=False):
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
        except Exception:
            self._driver = None
            logger.error(
                "Couldn't connect to Neo4j database, saving to database will be disabled"
            )

        if resetDBData is True:
            self.resetDBData()
            self.createDBSchema()

    def close(self):
        self._driver.close()

    def resetDBData(self):
        with self._driver.session() as session:
            session.write_transaction(self._resetDBData)

    @staticmethod
    def _resetDBData(tx):
        result = tx.run("MATCH (n) DETACH DELETE n")
        return result

    def runCypher(self, cypherCode):
        with self._driver.session() as session:
            return session.write_transaction(self._runCypher, cypherCode)

    @staticmethod
    def _runCypher(tx, cypherCode):
        result = tx.run(cypherCode)
        return result

    def createDBSchema(self):
        with self._driver.session() as session:
            return session.write_transaction(self._createDBSchema)

    @staticmethod
    def _createDBSchema(tx):
        result = tx.run("CREATE INDEX ON :Asset(exchange, name)")
        return result

    def createAssetNode(self, asset):
        with self._driver.session() as session:
            return session.write_transaction(self._createAssetNode, asset)

    @staticmethod
    def _createAssetNode(tx, asset):
        result = tx.run(
            "MERGE (node:Asset:%s {name:$symbol,symbol:$symbol,exchange:$exchange}) "
            "ON CREATE SET node.currentAmount=$amount "
            "WITH node "
            "MERGE (node)-[s:STATE {to:$forever}]->(state:AssetState {name:'State',amount:$amount}) "
            "ON CREATE SET s.from=$now "
            "WITH node "
            "MATCH (b:Asset)"
            "WHERE b.symbol=$symbol AND NOT node=b "
            "WITH node,b "
            "MERGE (node)-[r:EXCHANGE]->(b) "
            "ON CREATE SET r.from=$now, r.to=$forever, r.rate=1 "
            "RETURN id(node) as node" % (asset.exchange),
            symbol=asset.symbol,
            exchange=asset.exchange,
            now=time.time(),
            amount=0,
            forever=sys.maxsize)
        return result

    def setAssetState(self, asset, assetState):
        with self._driver.session() as session:
            session.write_transaction(self._setAssetState, asset, assetState)

    @staticmethod
    def _setAssetState(tx, asset, assetState):
        now = time.time()

        # GraphDB._createAssetNode(tx,asset)

        # create nodes if not existing yet and archive old relationship

        result = tx.run(
            "MATCH (asset:Asset)-[s:STATE]->(assetState:AssetState) "
            "WHERE asset.exchange = $assetExchange AND asset.symbol = $assetSymbol AND s.to > $now "
            "SET s.to = $now ",
            assetExchange=asset.getExchange(),
            assetSymbol=asset.getSymbol(),
            now=now)

        # create new relationship
        result = tx.run(
            "MATCH (asset:Asset) "
            "WHERE asset.exchange = $assetExchange AND asset.symbol = $assetSymbol "
            "CREATE (asset)-[s:STATE {from:$time_from,to:$time_to}]->(state:AssetState {name:'State',amount:$amount})"
            "SET asset.currentAmount=$amount ",
            assetExchange=asset.getExchange(),
            assetSymbol=asset.getSymbol(),
            time_to=sys.maxsize,
            time_from=now,
            amount=assetState.amount)
        return result

    def addTradingRelationship(self, tradingRelationship):
        with self._driver.session() as session:
            session.write_transaction(self._addTradingRel, tradingRelationship)

    @staticmethod
    def _addTradingRel(tx, tradingRelationship):
        now = time.time()

        GraphDB._createAssetNode(tx, tradingRelationship.getBaseAsset())
        GraphDB._createAssetNode(tx, tradingRelationship.getQuotationAsset())

        # create nodes if not existing yet and archive old relationship
        result = tx.run(
            "MATCH (base:Asset)-[r:EXCHANGE]->(quotation:Asset) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol AND r.to > $now "
            "SET r.to = $now ",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().
            getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().
            getSymbol(),
            now=now)

        # create new relationship
        result = tx.run(
            "MATCH (base:Asset),(quotation:Asset) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "CREATE(base)-[:EXCHANGE {rate:$rate,from:$time_from,to:$time_to}]->(quotation)",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().
            getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().
            getSymbol(),
            rate=tradingRelationship.rate,
            fee=tradingRelationship.fee,
            time_to=now + tradingRelationship.timeToLiveSec,
            time_from=now)
        return result

    @staticmethod
    def _create_and_return_greeting(tx, message):
        result = tx.run(
            "CREATE (a:Greeting) "
            "SET a.message = $message "
            "RETURN a.message + ', from node ' + id(a)",
            message=message)
        return result.single()[0]

    def getLatestTradingRate(self, baseAsset, quotationAsset):
        with self._driver.session() as session:
            return session.write_transaction(self._agetLatestTradingRate,
                                             baseAsset, quotationAsset)

    @staticmethod
    def _agetLatestTradingRate(tx, baseAsset, quotationAsset):

        result = tx.run(
            "MATCH (base:Asset)-[r:EXCHANGE]->(quotation:Asset) "
            "WHERE r.to>=$now AND base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "RETURN r.rate "
            "ORDER BY r.created DESC "
            "LIMIT 1",
            baseExchange=baseAsset.getExchange(),
            now=time.time(),
            baseSymbol=baseAsset.getSymbol(),
            quotationExchange=quotationAsset.getExchange(),
            quotationSymbol=quotationAsset.getSymbol())
        try:
            return result.single()[0]
        except Exception:
            return []

    def getArbitrageCycle(self, asset):
        with self._driver.session() as session:
            return session.write_transaction(self._getArbitrageCycle, asset)

    @staticmethod
    def _getArbitrageCycle(tx, asset):

        result = tx.run(
            "MATCH path = (c:Asset)-[r:EXCHANGE*1..4]->(c) "
            "WHERE c.symbol = $symbol AND  c.exchange = $exchange AND NONE (a in r WHERE a.to<$now) "
            "UNWIND NODES(path) AS n "
            "WITH path, SIZE(COLLECT(DISTINCT n)) AS testLength, c, r "
            "WHERE testLength = LENGTH(path) "
            "WITH path AS x, nodes(path)[0] as c, relationships(path) as r, $startVal as startVal "
            "WITH x, REDUCE(s = startVal, e IN r | s * e.rate) AS endVal, startVal "
            "WHERE endVal > startVal "
            "RETURN {rates:EXTRACT(r IN relationships(x) | {rate:r.rate}), profit:endVal - startVal, assets:EXTRACT(n IN NODES(x) | {exchange:n.exchange,symbol:n.name,amount:n.currentAmount})} AS ArbitrageDeal, {profit:endVal - startVal} AS Profit "
            "ORDER BY Profit DESC "
            "LIMIT 5",
            startVal=100,
            symbol=asset.getSymbol(),
            exchange=asset.getExchange(),
            now=time.time())
        return [record["ArbitrageDeal"] for record in result]


if __name__ == "__main__":
    # graphDB = GraphDB(resetDBData=True)
    graphDB = GraphDB(
        uri='bolt://3.120.197.59:7687',
        user='neo4j',
        password='i-0b4b0106c20014f75')

    graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'))

    graphDB.addTradingRelationship(
        TradingRelationship(
            baseAsset=Asset(exchange='Kraken', symbol='BTC'),
            quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
            rate=1,
            fee=0.002,
            timeToLiveSec=4))

    graphDB.addTradingRelationship(
        TradingRelationship(
            baseAsset=Asset(exchange='Kraken', symbol='BTC'),
            quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
            rate=2,
            fee=0.002,
            timeToLiveSec=2))
    graphDB.addTradingRelationship(
        TradingRelationship(
            baseAsset=Asset(exchange='Kraken', symbol='BTC'),
            quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
            rate=3,
            fee=0.002,
            timeToLiveSec=5))

    graphDB.addTradingRelationship(
        TradingRelationship(
            baseAsset=Asset(exchange='Kraken', symbol='ETH'),
            quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
            rate=4,
            fee=0.002,
            timeToLiveSec=3))

    graphDB.addTradingRelationship(
        TradingRelationship(
            baseAsset=Asset(exchange='Kraken', symbol='BTC'),
            quotationAsset=Asset(exchange='Poloniex', symbol='BTC'),
            rate=1,
            fee=0.002,
            timeToLiveSec=3))

    graphDB.setAssetState(
        asset=Asset(exchange='Kraken', symbol='BTC'),
        assetState=AssetState(amount=1))

    time.sleep(1)

    graphDB.setAssetState(
        asset=Asset(exchange='Kraken', symbol='BTC'),
        assetState=AssetState(amount=2))

    time.sleep(1)

    graphDB.setAssetState(
        asset=Asset(exchange='Kraken', symbol='BTC'),
        assetState=AssetState(amount=3))

    r = graphDB.getLatestTradingRate(
        baseAsset=Asset(exchange='Kraken', symbol='BTC'),
        quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
    )

    print(r)

    r = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'))
    print(r)
    print(time.time())

    # graphDB.print_greeting('hello')
