from neo4j.v1 import GraphDatabase
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
    def __init__(self, baseAsset, quotationAsset, mean_price, limit_price, orderbook, fee, timeToLiveSec):
        self.baseAsset = baseAsset
        self.quotationAsset = quotationAsset
        self.mean_price = mean_price
        self.limit_price = limit_price
        self.orderbook = orderbook
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
    
    def __enter__(self):
        return self
        
    def __exit__(self,exc_type, exc_value, traceback):
        self.close()

    def close(self):
        if self._driver is not None:
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
        #result = tx.run("CREATE CONSTRAINT ON (asset:Asset) ASSERT (asset.exchange, asset.symbol) IS NODE KEY")
        return result

    def createAssetNode(self, asset,now):
        with self._driver.session() as session:
            return session.write_transaction(self._createAssetNode, asset,now)

    @staticmethod
    def _createAssetNode(tx, asset,now):
        result = tx.run(
            "MERGE (node:Asset:%s {name:$symbol,symbol:$symbol,exchange:$exchange}) "
            "ON CREATE SET node.currentAmount=$amount "
            "WITH node "
            "MERGE (node)-[s:STATE {to:$forever}]->(state:AssetState {name:'State',amount:$amount}) "
            "ON CREATE SET s.from=$now "
            "RETURN id(node) as node" % (asset.exchange),
            symbol=asset.symbol,
            exchange=asset.exchange,
            now=now,
            amount=0,
            mean_price=1,
            limit_price=1,
            forever=sys.maxsize)
        nodeids =  [record["node"] for record in result]

        result = tx.run(
                    "MATCH (node:Asset) "
                    "WHERE id(node) = $nodeid "
                    "MATCH (b:Asset) "
                    "WHERE b.symbol=$symbol AND NOT node=b "
                    "WITH node,b "
                    "MERGE (node)-[r:EXCHANGE]->(b) "
                    "ON CREATE SET r.from=$now, r.to=$forever, r.mean_price=$mean_price, r.limit_price=$limit_price "
                    "WITH node,b "
                    "MERGE (b)-[r:EXCHANGE]->(node) "
                    "ON CREATE SET r.from=$now, r.to=$forever, r.mean_price=$mean_price, r.limit_price=$limit_price "
                    "RETURN id(node) as node",
                    symbol=asset.symbol,                    
                    now=now,
                    mean_price=1,
                    limit_price=1,
                    nodeid=nodeids[0],
                    forever=sys.maxsize)
        return nodeids

    def setAssetState(self, asset, assetState,now):
        with self._driver.session() as session:
            session.write_transaction(self._setAssetState, asset, assetState,now)

    @staticmethod
    def _setAssetState(tx, asset, assetState,now):
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

    def addTradingRelationship(self, tradingRelationship,now):
        with self._driver.session() as session:
            session.write_transaction(self._addTradingRel, tradingRelationship,now)

    @staticmethod
    def _addTradingRel(tx, tradingRelationship,now):

        GraphDB._createAssetNode(tx, tradingRelationship.getBaseAsset(),now)
        GraphDB._createAssetNode(tx, tradingRelationship.getQuotationAsset(),now)

        # create nodes if not existing yet and archive old relationship
        result = tx.run(
            "MATCH (base:Asset)-[r:EXCHANGE|ORDERBOOK]->(quotation:Asset) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol AND r.to >= $now "
            "SET r.to = $now ",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().
            getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().
            getSymbol(),
            now=now)

        # create new trading relationship
        result = tx.run(
            "MATCH (base:Asset),(quotation:Asset) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "CREATE(base)-[:EXCHANGE {mean_price:$mean_price,limit_price:$limit_price,from:$time_from,to:$time_to}]->(quotation)",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().getSymbol(),
            mean_price=tradingRelationship.mean_price,
            limit_price=tradingRelationship.limit_price,
            fee=tradingRelationship.fee,
            time_to=now + tradingRelationship.timeToLiveSec,
            time_from=now)

        # create new orderbook relationship
        result = tx.run(
            "MATCH (base:Asset),(quotation:Asset) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "CREATE(base)-[:ORDERBOOK {orderbook:$orderbook,from:$time_from,to:$time_to}]->(quotation)",
            baseExchange=tradingRelationship.getBaseAsset().getExchange(),
            baseSymbol=tradingRelationship.getBaseAsset().getSymbol(),
            quotationExchange=tradingRelationship.getQuotationAsset().getExchange(),
            quotationSymbol=tradingRelationship.getQuotationAsset().getSymbol(),
            orderbook=tradingRelationship.orderbook,
            fee=tradingRelationship.fee,
            time_to=now + tradingRelationship.timeToLiveSec,
            time_from=now)

        return result


    def get_latest_prices(self, baseAsset, quotationAsset, now):
        with self._driver.session() as session:
            session.write_transaction(self._get_latest_prices, baseAsset, quotationAsset,now)

    @staticmethod
    def _get_latest_prices(tx, baseAsset, quotationAsset, now):

        result = tx.run(
            "MATCH (base:Asset)-[r:EXCHANGE]->(quotation:Asset) "
            "WHERE r.to>=$now AND base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "RETURN r.mean_price, r.limit_price "
            "ORDER BY r.created DESC "
            "LIMIT 1",
            baseExchange=baseAsset.getExchange(),
            now=now,
            baseSymbol=baseAsset.getSymbol(),
            quotationExchange=quotationAsset.getExchange(),
            quotationSymbol=quotationAsset.getSymbol())
        try:
            return [{'market_price': record["market_price"],'limit_price':record["limit_price"]} for record in result]
        except Exception:
            return []

    def getArbitrageCycle(self, asset, match_lookback_sec,now):
        with self._driver.session() as session:
            return session.write_transaction(self._getArbitrageCycle, asset,match_lookback_sec,now)

    @staticmethod
    def _getArbitrageCycle(tx, asset, match_lookback_sec,now):
        result = tx.run(
            "MATCH path = (c:Asset)-[r:EXCHANGE*1..4]->(c) "
            "WHERE c.symbol = $symbol AND  c.exchange = $exchange AND NONE (a in r WHERE a.to<$now) "
            "UNWIND NODES(path) AS n "
            "WITH path, SIZE(COLLECT(DISTINCT n)) AS testLength, c, r "
            "WHERE testLength = LENGTH(path) "
            "WITH path AS x, nodes(path)[0] as c, relationships(path) as r, $startVal as startVal "
            "WITH x, REDUCE(s = startVal, e IN r | s * e.mean_price) AS endVal, startVal, COLLECT(nodes(x)) as elems "
            "WHERE endVal > startVal "
            "RETURN {path:EXTRACT(r IN relationships(x) | {mean_price:r.mean_price,start_node:id(startNode(r)),end_node:id(endNode(r))}), profit:endVal - startVal, assets:EXTRACT(n IN NODES(x) | {exchange:n.exchange,symbol:n.name,amount:n.currentAmount,nodeid:id(n)})} AS ArbitrageDeal, {profit:endVal - startVal} AS Profit "
            "ORDER BY Profit DESC "
            "LIMIT 5",
            startVal=100,
            symbol=asset.getSymbol(),
            exchange=asset.getExchange(),
            now=now)

        arbitrage_deals = [record["ArbitrageDeal"] for record in result]

        for arbitrage_deal in arbitrage_deals:            
            cypher_match = []
            cypher_match_set = []
            cypher_create_set = []
            cypher_match2 = []
            cypher_match3 = []
            for idx,x in enumerate(arbitrage_deal['assets']):
                nodename=chr(ord('a') + idx)
                
                cypher_match.append("("+nodename+":Asset {symbol:'"+str(x['symbol'])+"',exchange:'"+str(x['exchange'])+"'})")
                cypher_match2.append("("+nodename+":Asset {symbol:'"+str(x['symbol'])+"',exchange:'"+str(x['exchange'])+"'})")
                cypher_match3.append("("+nodename+")")

                # setting relationship properties
                if idx < (len(arbitrage_deal['assets'])-1):
                    cypher_match.append("-[r"+str(idx)+":ARBITRAGE]->")
                    cypher_match3.append("-[r"+str(idx)+":ARBITRAGE]->")
                    cypher_match_set.append("r"+str(idx)+".to=$now")
                    
                    cypher_create_set.append("r"+str(idx)+".to=$now")
                    cypher_create_set.append("r"+str(idx)+".from=$now")
                    cypher_create_set.append("r"+str(idx)+".uuid=uuid")
                    
            cypher_cmd  = ' MATCH path = '+''.join(cypher_match)
            cypher_cmd += " WHERE ALL (a in rels(path) WHERE ($now-a.to)<=$match_lookback_sec ) "
            cypher_cmd += " SET " + ','.join(cypher_match_set)
            cypher_cmd += " RETURN count(*) AS nof_matches"
            result = tx.run(cypher_cmd,now=now,match_lookback_sec=match_lookback_sec)
            nof_matches = result.single()['nof_matches']
            
            if nof_matches == 0: # new arbitrage deal to be created
                cypher_cmd  = ' WITH randomUUID() as uuid'
                cypher_cmd += ' MATCH '+','.join(cypher_match2)
                cypher_cmd += ' CREATE '+''.join(cypher_match3)
                cypher_cmd += " SET " + ','.join(cypher_create_set)
                result = tx.run(cypher_cmd,now=now)
                
            print(cypher_cmd)
        return arbitrage_deals