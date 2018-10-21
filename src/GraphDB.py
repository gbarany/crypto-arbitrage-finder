from neo4j.v1 import GraphDatabase
import sys
from InitLogger import logger

class AssetState:
    def __init__(self, amount):
        self.amount = amount


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

    @staticmethod
    def getRuntime(result):
        return 'Neo4J query runtime:%dms'%result.summary().result_available_after

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
        result = tx.run("CREATE INDEX ON :AssetStock(exchange, name)")
        #result = tx.run("CREATE CONSTRAINT ON (asset:AssetStock) ASSERT (asset.exchange, asset.symbol) IS NODE KEY")
        return result

    def createAssetNode(self, asset,volumeBTCs,now):
        with self._driver.session() as session:
            return session.write_transaction(self._createAssetNode, asset,volumeBTCs,now)

    @staticmethod
    def _createAssetNode(tx, asset,volumeBTCs,now):
        result = tx.run(
            "MERGE (node:AssetStock:%s {name:$symbol,symbol:$symbol,exchange:$exchange}) "
            "ON CREATE SET node.currentAmount=$amount "
            "WITH node "
            "MERGE (node)-[s:STATE {_to:$forever}]->(state:StockState {name:'State',amount:$amount}) "
            "ON CREATE SET s._from=$now "
            "RETURN id(node) as node" % (asset.exchange),
            symbol=asset.symbol,
            exchange=asset.exchange,
            now=now,
            amount=0,
            meanPrice=1,
            limitPrice=1,
            forever=sys.maxsize)
        
        logger.info(GraphDB.getRuntime(result))

        nodeids =  [record["node"] for record in result]
        
        result = tx.run(
                    "MATCH (node:AssetStock) "
                    "WHERE id(node) = $nodeid "
                    "MATCH (b:AssetStock) "
                    "WHERE b.symbol=$symbol AND NOT node=b "
                    "WITH node,b, $volumeBTCs as volumes "
                    "FOREACH (volume in volumes | "
                    "MERGE (node)-[r:EXCHANGE {volumeBTC:volume}]->(b) "
                    "ON CREATE SET r._from=$now, r._to=$forever, r.meanPrice=$meanPrice, r.meanPriceNet=$meanPriceNet, r.limitPrice=$limitPrice "
                    ") "
                    "WITH node,b, volumes "
                    "FOREACH (volume in volumes | "
                    "MERGE (b)-[r:EXCHANGE {volumeBTC:volume}]->(node) "
                    "ON CREATE SET  r._from=$now, r._to=$forever, r.meanPrice=$meanPrice, r.meanPriceNet=$meanPriceNet, r.limitPrice=$limitPrice "
                    ") "
                    "RETURN id(node) as node",
                    symbol=asset.symbol,                    
                    now=now,
                    meanPrice=1,
                    meanPriceNet=1,
                    limitPrice=1,
                    nodeid=nodeids[0],
                    volumeBTCs=volumeBTCs,
                    forever=sys.maxsize)
        logger.info(GraphDB.getRuntime(result))

        return nodeids

    def getNodesPropertyHash(self):
        with self._driver.session() as session:
            return session.write_transaction(self._getNodesPropertyHash)

    @staticmethod
    def _getNodesPropertyHash(tx):
        hash = [record["hash"] for record in tx.run(
            "MATCH (n) "
            "WITH n " 
            "ORDER BY n.symbol, n.exchange " 
            "WITH collect(properties(n)) AS propresult, n " 
            "RETURN apoc.util.md5(propresult) as hash, propresult, id(n) as nodeid " 
            "ORDER BY hash DESC ")]
        return hash

    def getRelsPropertyHash(self):
        with self._driver.session() as session:
            return session.write_transaction(self._getRelsPropertyHash)

    @staticmethod
    def _getRelsPropertyHash(tx):
        hash = [record["hash"] for record in tx.run(
                "MATCH (n)-[r]->(k) "
                "WITH r "
                "ORDER BY r.uuid "
                "WITH collect(properties(r)) AS propresult,r "
                "RETURN apoc.util.md5(propresult) as hash, propresult, startNode(r) as startNode, endNode(r) as endNode, r "
                "ORDER BY hash DESC ")]
        return hash


    def setAssetMarketPrice(self, assetBaseSymbol, assetQuotationSymbol, marketPrice,now):
        with self._driver.session() as session:
            session.write_transaction(self._setAssetMarketPrice, assetBaseSymbol, assetQuotationSymbol, marketPrice,now)

    @staticmethod
    def _setAssetMarketPrice(tx, assetBaseSymbol, assetQuotationSymbol, marketPrice,now):
        # create nodes if not existing yet and archive old relationship
        result = tx.run(
            "MATCH (assetBase:Asset)-[rel:MARKETPRICE]->(assetQuotation:Asset) "
            "WHERE assetBase.symbol = $assetBaseSymbol AND assetQuotation.symbol = $assetQuotationSymbol AND rel._to > $now "
            "SET rel._to = $now "
            "WITH assetBase, assetQuotation "
            "MATCH (assetQuotation:Asset)-[rel:MARKETPRICE]->(assetBase:Asset) "
            "SET rel._to = $now ",
            assetBaseSymbol=assetBaseSymbol,
            assetQuotationSymbol=assetQuotationSymbol,
            to=sys.maxsize,
            marketPrice=marketPrice,
            now=now)
        logger.info(GraphDB.getRuntime(result))

        result = tx.run(
            "MERGE (assetBaseNew:Asset {symbol:$assetBaseSymbol}) "
            "MERGE (assetQuotationNew:Asset {symbol:$assetQuotationSymbol})  "
            "MERGE (assetBaseNew)-[:MARKETPRICE {_from:$now, _to:$to,marketPrice:$marketPrice}]->(assetQuotationNew) "
            "MERGE (assetQuotationNew)-[:MARKETPRICE {_from:$now, _to:$to,marketPrice:$marketPriceRebased}]->(assetBaseNew) ",
            assetBaseSymbol=assetBaseSymbol,
            assetQuotationSymbol=assetQuotationSymbol,
            to=sys.maxsize,
            marketPrice=marketPrice,
            marketPriceRebased=1/marketPrice,
            now=now)
        logger.info(GraphDB.getRuntime(result))

        return result

    def setAssetState(self, asset, assetState,now):
        with self._driver.session() as session:
            session.write_transaction(self._setAssetState, asset, assetState,now)

    @staticmethod
    def _setAssetState(tx, asset, assetState,now):
        # GraphDB._createAssetNode(tx,asset)

        # create nodes if not existing yet and archive old relationship

        result = tx.run(
            "MATCH (asset:AssetStock)-[s:STATE]->(assetState:StockState) "
            "WHERE asset.exchange = $assetExchange AND asset.symbol = $assetSymbol AND s._to > $now "
            "SET s._to = $now ",
            assetExchange=asset.getExchange(),
            assetSymbol=asset.getSymbol(),
            now=now)
        logger.info(GraphDB.getRuntime(result))
        # create new relationship
        result = tx.run(
            "MATCH (asset:AssetStock) "
            "WHERE asset.exchange = $assetExchange AND asset.symbol = $assetSymbol "
            "CREATE (asset)-[s:STATE {_from:$timeFrom,_to:$timeTo}]->(state:StockState {name:'State',amount:$amount})"
            "SET asset.currentAmount=$amount ",
            assetExchange=asset.getExchange(),
            assetSymbol=asset.getSymbol(),
            timeTo=sys.maxsize,
            timeFrom=now,
            amount=assetState.amount)

        logger.info(GraphDB.getRuntime(result))
        return result

    def addTradingRelationship(self, orderBook,volumeBTCs=[1]):
        with self._driver.session() as session:
            session.write_transaction(self._addTradingRel, orderBook,volumeBTCs)

    @staticmethod
    def _addTradingRel(tx, orderBook,volumeBTCs):
        
        now = orderBook.getTimestamp()
        GraphDB._createAssetNode(tx, orderBook.getBaseAsset(),volumeBTCs,now)
        GraphDB._createAssetNode(tx, orderBook.getQuoteAsset(),volumeBTCs,now)

        # create nodes if not existing yet and archive old relationship
        result = tx.run(
            "MATCH (base:AssetStock)-[r:EXCHANGE|ORDERBOOK]->(quotation:AssetStock) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol AND r._to >= $now "
            "SET r._to = $now ",
            baseExchange=orderBook.getBaseAsset().getExchange(),
            baseSymbol=orderBook.getBaseAsset().getSymbol(),
            quotationExchange=orderBook.getQuoteAsset().getExchange(),
            quotationSymbol=orderBook.getQuoteAsset().getSymbol(),
            now=now)
        logger.info(GraphDB.getRuntime(result))
        # create new trading relationship
        for volumeBTC in volumeBTCs:
            orderBookPrice = orderBook.getPriceByBTCVolume(volumeBTC=volumeBTC)
            
            result = tx.run(
                "MATCH (base:AssetStock),(quotation:AssetStock) "
                "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
                "CREATE(base)-[:EXCHANGE {volumeBTC:$volumeBTC,volumeBase:$volumeBase,feeAmountBase:$feeAmountBase,feeAmountBTC:$feeAmountBTC,feeRate:$feeRate,meanPrice:$meanPrice,meanPriceNet:$meanPriceNet,limitPrice:$limitPrice,_from:$timeFrom,_to:$timeTo}]->(quotation)",
                baseExchange=orderBook.getBaseAsset().getExchange(),
                baseSymbol=orderBook.getBaseAsset().getSymbol(),
                quotationExchange=orderBook.getQuoteAsset().getExchange(),
                quotationSymbol=orderBook.getQuoteAsset().getSymbol(),
                meanPrice=orderBookPrice.meanPrice,
                meanPriceNet = orderBookPrice.meanPriceNet,
                limitPrice=orderBookPrice.limitPrice,
                feeRate=orderBookPrice.feeRate,
                feeAmountBase=orderBookPrice.feeAmountBase,
                feeAmountBTC=orderBookPrice.feeAmountBTC,
                volumeBase=orderBookPrice.volumeBase,
                volumeBTC=orderBookPrice.volumeBTC,
                timeTo=now + orderBook.timeToLiveSec,
                timeFrom=now)
            logger.info(GraphDB.getRuntime(result))
        # create new orderbook relationship
        result = tx.run(
            "MATCH (base:AssetStock),(quotation:AssetStock) "
            "WHERE base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "CREATE(base)-[:ORDERBOOK {rateBTCxBase:$rateBTCxBase,rateBTCxQuote:$rateBTCxQuote,feeRate:$feeRate,orderbook:$orderbook,_from:$timeFrom,_to:$timeTo}]->(quotation)",
            baseExchange=orderBook.getBaseAsset().getExchange(),
            baseSymbol=orderBook.getBaseAsset().getSymbol(),
            quotationExchange=orderBook.getQuoteAsset().getExchange(),
            quotationSymbol=orderBook.getQuoteAsset().getSymbol(),
            orderbook=orderBook.getOrderbookStr(),
            rateBTCxBase=orderBook.rateBTCxBase,
            rateBTCxQuote=orderBook.rateBTCxQuote,
            feeRate=orderBookPrice.feeRate,
            timeTo=now + orderBook.timeToLiveSec,
            timeFrom=now)
        logger.info(GraphDB.getRuntime(result))
        return result


    def getLatestExchangePrices(self, baseAsset, quotationAsset, now):
        with self._driver.session() as session:
            return session.write_transaction(self._getLatestExchangePrices, baseAsset, quotationAsset,now)

    @staticmethod
    def _getLatestExchangePrices(tx, baseAsset, quotationAsset, now):

        result = tx.run(
            "MATCH (base:AssetStock)-[r:EXCHANGE]->(quotation:AssetStock) "
            "WHERE r._to>=$now AND base.exchange = $baseExchange AND base.symbol = $baseSymbol AND quotation.exchange = $quotationExchange AND quotation.symbol = $quotationSymbol "
            "RETURN r.meanPrice AS meanPrice, r.limitPrice AS limitPrice, r.meanPriceNet as meanPriceNet "
            "ORDER BY r._to DESC "
            "LIMIT 1",
            baseExchange=baseAsset.getExchange(),
            now=now,
            baseSymbol=baseAsset.getSymbol(),
            quotationExchange=quotationAsset.getExchange(),
            quotationSymbol=quotationAsset.getSymbol())
        logger.info(GraphDB.getRuntime(result))
        try:
            return [{'meanPriceNet': record["meanPriceNet"],'meanPrice': record["meanPrice"],'limitPrice':record["limitPrice"]} for record in result]
        except Exception:
            return []

    def getArbitrageCycle(self, asset, match_lookback_sec,now,volumeBTCs=[1]):
        with self._driver.session() as session:
            return session.write_transaction(self._getArbitrageCycle, asset,match_lookback_sec,now,volumeBTCs)

    @staticmethod
    def _getArbitrageCycle(tx, asset, match_lookback_sec,now,volumeBTCs):
        arbitrage_deals = []
        for volumeBTC in volumeBTCs:
            result = tx.run(
                "MATCH path = (c:AssetStock)-[r:EXCHANGE*1..4 {volumeBTC:$volumeBTC}]->(c) "
                "WHERE c.symbol = $symbol AND  c.exchange = $exchange AND ALL (a in r WHERE a._to>=$now) "
                "UNWIND NODES(path) AS n "
                "WITH path, SIZE(COLLECT(DISTINCT n)) AS testLength, c, r "
                "WHERE testLength = LENGTH(path) "
                "WITH path AS x, nodes(path)[0] as c, relationships(path) as r, $startVal as startVal "
                "WITH x, REDUCE(s = startVal, e IN r | s * e.meanPriceNet) AS endVal, startVal, COLLECT(nodes(x)) as elems "
                "WHERE endVal > startVal "
                "RETURN {volumeBTC:$volumeBTC,path:EXTRACT(r IN relationships(x) | {meanPrice:r.meanPrice,meanPriceNet:r.meanPriceNet,start_node:id(startNode(r)),end_node:id(endNode(r))}), profit:endVal - startVal, assets:EXTRACT(n IN NODES(x) | {exchange:n.exchange,symbol:n.name,amount:n.currentAmount,nodeid:id(n)})} AS ArbitrageDeal, {profit:endVal - startVal} AS Profit "
                "ORDER BY Profit DESC "
                "LIMIT 5",
                startVal=100,
                symbol=asset.getSymbol(),
                exchange=asset.getExchange(),
                volumeBTC=volumeBTC,
                now=now)
            logger.info(GraphDB.getRuntime(result))
            arbitrage_deals.extend([record["ArbitrageDeal"] for record in result])

        for arbitrage_deal in arbitrage_deals:            
            cypher_match = []
            cypher_match_set = []
            cypher_create_set = []
            cypher_match2 = []
            cypher_match3 = []
            for idx,x in enumerate(arbitrage_deal['assets']):
                nodename=chr(ord('a') + idx)
                
                cypher_match.append("("+nodename+":AssetStock {symbol:'"+str(x['symbol'])+"',exchange:'"+str(x['exchange'])+"'})")
                cypher_match2.append("("+nodename+":AssetStock {symbol:'"+str(x['symbol'])+"',exchange:'"+str(x['exchange'])+"'})")
                cypher_match3.append("("+nodename+")")

                # setting relationship properties
                if idx < (len(arbitrage_deal['assets'])-1):
                    cypher_match.append("-[r"+str(idx)+":ARBITRAGE]->")
                    cypher_match3.append("-[r"+str(idx)+":ARBITRAGE]->")
                    cypher_match_set.append("r"+str(idx)+"._to=$now")
                    
                    cypher_create_set.append("r"+str(idx)+"._to=$now")
                    cypher_create_set.append("r"+str(idx)+"._from=$now")
                    cypher_create_set.append("r"+str(idx)+".uuid=uuid")
                    cypher_create_set.append("r"+str(idx)+".volumeBTC=$volumeBTC")
                    cypher_create_set.append("r"+str(idx)+".meanPrice=%f"%(arbitrage_deal['path'][idx]['meanPrice']))
                    cypher_create_set.append("r"+str(idx)+".meanPriceNet=%f"%(arbitrage_deal['path'][idx]['meanPriceNet']))
                    
            cypher_cmd  = ' MATCH path = '+''.join(cypher_match)
            cypher_cmd += " WHERE ALL (a in rels(path) WHERE ($now-a._to)<=$match_lookback_sec ) AND ALL (a in rels(path) WHERE (a.volumeBTC)=$volumeBTC) "
            cypher_cmd += " SET " + ','.join(cypher_match_set)
            cypher_cmd += " RETURN count(*) AS nof_matches"
            result = tx.run(cypher_cmd,now=now,match_lookback_sec=match_lookback_sec,volumeBTC=arbitrage_deal['volumeBTC'])
            nof_matches = result.single()['nof_matches']
            
            if nof_matches == 0: # new arbitrage deal to be created
                cypher_cmd  = ' WITH randomUUID() as uuid'
                cypher_cmd += ' MATCH '+','.join(cypher_match2)
                cypher_cmd += ' CREATE '+''.join(cypher_match3)
                cypher_cmd += " SET " + ','.join(cypher_create_set)
                #cypher_cmd += " CREATE (arb:ArbitrageDeal {uuid:uuid,volumeBTC:$volumeBTC})"
                result = tx.run(cypher_cmd,now=now,volumeBTC=arbitrage_deal['volumeBTC'])
                logger.info(GraphDB.getRuntime(result))
            print(cypher_cmd)
        return arbitrage_deals