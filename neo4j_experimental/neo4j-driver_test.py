from neo4j.v1 import GraphDatabase
import time


class TradingRelationship:
    def __init__(self, baseExchange, baseSymbol, quotationExchange, quotationSymbol, rate):
        self.baseExchange = baseExchange
        self.baseSymbol = baseSymbol
        self.quotationExchange = quotationExchange
        self.quotationSymbol = quotationSymbol
        self.rate = rate

    def getBaseNodeID(self):
        return self.baseExchange+self.baseSymbol

    def getQuotationNodeID(self):
        return self.quotationExchange+self.quotationSymbol


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

    def createNode(self, symbol, exchange):
        with self._driver.session() as session:
            return session.write_transaction(self._createNode, symbol, exchange)

    @staticmethod
    def _createNode(tx, symbol, exchange):
        result = tx.run(
            "CREATE (node:CryptoCurrency:%s {name:$symbol,symbol:$symbol,exchange:$exchange}) "
            "RETURN id(node)" % (exchange),
            symbol=symbol,
            exchange=exchange)
        return result.single()[0]

    def addTradingRelationship(self, tradingRelationship):
        with self._driver.session() as session:
            session.write_transaction(self._addTradingRel, tradingRelationship)

    @staticmethod
    def _addTradingRel(tx, tradingRelationship):
        
        result = tx.run(
            "MATCH (base:CryptoCurrency),(quotation:CryptoCurrency) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "CREATE(base)-[:EXCHANGE {rate:$rate,created:$created}]->(quotation)",
            baseExchange=tradingRelationship.baseExchange,
            baseSymbol=tradingRelationship.baseSymbol,
            quotationExchange=tradingRelationship.quotationExchange,
            quotationSymbol=tradingRelationship.quotationSymbol,
            rate=tradingRelationship.rate,
            created=time.time())
        return result

    @staticmethod
    def _create_and_return_greeting(tx, message):
        result = tx.run("CREATE (a:Greeting) "
                        "SET a.message = $message "
                        "RETURN a.message + ', from node ' + id(a)", message=message)
        return result.single()[0]


uri = 'bolt://neo4j:neo@localhost:7687'
user = 'neo4j'
password = 'neo'

graphDB = GraphDB(uri=uri, user=user, password=password)
graphDB.resetDB()

graphDB.createNode(symbol='BTC', exchange='Kraken')
graphDB.createNode(symbol='BTC', exchange='Poloniex')
graphDB.createNode(symbol='ETH', exchange='Kraken')


graphDB.addTradingRelationship(
    TradingRelationship(
        baseExchange='Kraken',
        baseSymbol='BTC',
        quotationExchange='Kraken',
        quotationSymbol='ETH',
        rate=2)
)

graphDB.addTradingRelationship(
    TradingRelationship(
        baseExchange='Kraken',
        baseSymbol='BTC',
        quotationExchange='Poloniex',
        quotationSymbol='BTC',
        rate=1)
)

# graphDB.print_greeting('hello')
