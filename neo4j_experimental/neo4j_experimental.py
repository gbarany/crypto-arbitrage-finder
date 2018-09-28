from neo4j.v1 import GraphDatabase
import time


class Asset:
    def __init__(self, exchange, symbol):
        self.exchange = exchange
        self.symbol = symbol

    def getExchange(self):
        return self.exchange

    def getSymbol(self):
        return self.symbol


class TradingRelationship:
    def __init__(self, baseAsset, quotationAsset, rate,timeToLiveSec):
        self.baseAsset = baseAsset
        self.quotationAsset = quotationAsset
        self.rate = rate
        self.timeToLiveSec = timeToLiveSec

    def getBaseAsset(self):
        return self.baseAsset

    def getQuotationAsset(self):
        return self.quotationAsset

    def getBaseNodeID(self):
        return self.baseAsset.exchange+self.baseAsset.symbol

    def getQuotationNodeID(self):
        return self.quotationAsset.exchange+self.quotationAsset.symbol


class GraphDB(object):

    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def print_greeting(self, message):
        with self._driver.session() as session:
            greeting = session.write_transaction(
                self._create_and_return_greeting, message)
            print(greeting)

    def resetDB(self):
        with self._driver.session() as session:
            session.write_transaction(self._resetDB)

    @staticmethod
    def _resetDB(tx):
        result = tx.run("MATCH (n) DETACH DELETE n")
        return result

    def createDBSchema(self):
        with self._driver.session() as session:
            session.write_transaction(self._createDBSchema)

    @staticmethod
    def _createDBSchema(tx):
        result = tx.run("CREATE INDEX ON :CryptoCurrency(exchange, name)")
        return result

    def createNode(self, asset):
        with self._driver.session() as session:
            return session.write_transaction(self._createNode, asset)

    @staticmethod
    def _createNode(tx, asset):
        result = tx.run(
            "CREATE (node:CryptoCurrency:%s {name:$symbol,symbol:$symbol,exchange:$exchange}) "
            "RETURN id(node)" % (asset.exchange),
            symbol=asset.symbol,
            exchange=asset.exchange)
        return result.single()[0]

    def addTradingRelationship(self, tradingRelationship):
        with self._driver.session() as session:
            session.write_transaction(self._addTradingRel, tradingRelationship)

    @staticmethod
    def _addTradingRel(tx, tradingRelationship):
        now = time.time()

        result = tx.run(
            "MATCH (base:CryptoCurrency)-[r:EXCHANGE]->(quotation:CryptoCurrency) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol AND r.to > $now "
            "SET r.to = $now ",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().getSymbol(),
            now=now)

        result = tx.run(
            "MATCH (base:CryptoCurrency),(quotation:CryptoCurrency) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "CREATE(base)-[:EXCHANGE {rate:$rate,from:$time_from,to:$time_to}]->(quotation)",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().getSymbol(),
            rate=tradingRelationship.rate,
            time_to=now+tradingRelationship.timeToLiveSec,
            time_from=now)
        return result

    @staticmethod
    def _create_and_return_greeting(tx, message):
        result = tx.run("CREATE (a:Greeting) "
                        "SET a.message = $message "
                        "RETURN a.message + ', from node ' + id(a)", message=message)
        return result.single()[0]

    def getLatestTradingRate(self, baseAsset, quotationAsset):
        with self._driver.session() as session:
            return session.write_transaction(self._agetLatestTradingRate, baseAsset, quotationAsset)

    @staticmethod
    def _agetLatestTradingRate(tx, baseAsset, quotationAsset):

        result = tx.run(
            "MATCH (base:CryptoCurrency)-[r:EXCHANGE]->(quotation:CryptoCurrency) "
            "WHERE r.to>=$now AND base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "RETURN r.rate "
            "ORDER BY r.created DESC "
            "LIMIT 1",
            baseExchange=baseAsset.getExchange(),
            now = time.time(),
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
            "MATCH path = (c:CryptoCurrency)-[r:EXCHANGE*1..4]->(c) "
            "WHERE c.symbol = $symbol AND  c.exchange = $exchange AND NONE (a in r WHERE a.to<$now) "
            "UNWIND NODES(path) AS n "
            "WITH path, SIZE(COLLECT(DISTINCT n)) AS testLength, c, r "
            "WHERE testLength = LENGTH(path) "
            "WITH path AS x, nodes(path)[0] as c, relationships(path) as r, $startVal as startVal "
            "WITH x, REDUCE(s = startVal, e IN r | s * e.rate) AS endVal, startVal "
            "WHERE endVal > startVal "
            "RETURN EXTRACT(n IN NODES(x) | labels(n)[0]+n.name) AS Exchanges, endVal - startVal AS Profit "
            "ORDER BY Profit DESC "
            "LIMIT 5",
            startVal=100,
            symbol=asset.getSymbol(),
            exchange=asset.getExchange(),
            now=time.time())
        return [(record["Exchanges"],record["Profit"]) for record in result]


uri = 'bolt://neo4j:neo@localhost:7687'
user = 'neo4j'
password = 'neo'

graphDB = GraphDB(uri=uri, user=user, password=password)
graphDB.resetDB()
graphDB.createDBSchema()

graphDB.createNode(Asset(symbol='BTC', exchange='Kraken'))
graphDB.createNode(Asset(symbol='BTC', exchange='Poloniex'))
graphDB.createNode(Asset(symbol='ETH', exchange='Kraken'))


graphDB.addTradingRelationship(
    TradingRelationship(
        baseAsset=Asset(exchange='Kraken', symbol='BTC'),
        quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
        rate=1,
        timeToLiveSec=4)
)

graphDB.addTradingRelationship(
    TradingRelationship(
        baseAsset=Asset(exchange='Kraken', symbol='BTC'),
        quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
        rate=2,
        timeToLiveSec=2)
)
graphDB.addTradingRelationship(
    TradingRelationship(
        baseAsset=Asset(exchange='Kraken', symbol='BTC'),
        quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
        rate=3,
        timeToLiveSec=1)
)

graphDB.addTradingRelationship(
    TradingRelationship(
        baseAsset=Asset(exchange='Kraken', symbol='ETH'),
        quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
        rate=4,
        timeToLiveSec=3)
)

graphDB.addTradingRelationship(
    TradingRelationship(
        baseAsset=Asset(exchange='Kraken', symbol='BTC'),
        quotationAsset=Asset(exchange='Poloniex', symbol='BTC'),
        rate=1,
        timeToLiveSec=3)
)

graphDB.addTradingRelationship(
    TradingRelationship(
        baseAsset=Asset(exchange='Poloniex', symbol='BTC'),
        quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
        rate=20,
        timeToLiveSec=3)
)

#time.sleep(2)

r = graphDB.getLatestTradingRate(
    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
)

print(r)

r = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'))
print(r)
print(time.time())
# graphDB.print_greeting('hello')
