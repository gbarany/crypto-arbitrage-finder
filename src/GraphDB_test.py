import pytest
import sys
from GraphDB import GraphDB, Asset,TradingRelationship, AssetState
from OrderBook import OrderBook
import time
import pprint
import time

class TestClass(object):

    def test_setAssetState(self):
        graphDB = GraphDB(resetDBData=True)
        graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=time.time())

        result_validation = [
            record["node"] for record in graphDB.runCypher(
                "MATCH (n)-[r:STATE]->(s) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount,amount:s.amount,stateRelFrom:r.from,stateRelTo:r.to} AS node"
            )
        ]
        assert len(result_validation) == 1
        assert result_validation[0]['amount'] == 0
        assert result_validation[0]['currentAmount'] == 0
        assert result_validation[0]['stateRelTo'] == sys.maxsize

        graphDB.setAssetState(Asset(exchange='Bitfinex', symbol='BTC'),AssetState(amount=2),now=time.time())
        result_validation2 = [
            record["node"] for record in graphDB.runCypher(
                "MATCH (n)-[r:STATE]->(s) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount,amount:s.amount,stateRelFrom:r.from,stateRelTo:r.to} AS node"
            )
        ]
        assert len(result_validation2) == 2
        assert result_validation2[1]['stateRelTo'] == result_validation2[0]['stateRelFrom']
        assert result_validation2[0]['amount'] == 2
        assert result_validation2[1]['amount'] == 0
 
    def test_setAssetMarketPrice(self):
        graphDB = GraphDB(resetDBData=True)
        graphDB.setAssetMarketPrice(assetBaseSymbol='BTC', assetQuotationSymbol='USD',marketPrice=5000,now=1)

        result_validation = [
            record["rel"] for record in graphDB.runCypher(
                "MATCH (n)-[r:MARKETPRICE]->(s) RETURN {endNode:endNode(r).symbol,startNode:startNode(r).symbol,from:r.from,to:r.to,marketPrice:r.marketPrice} AS rel ORDER BY r.marketPrice DESC"
            )
        ]
        assert len(result_validation) == 2
        assert result_validation[0]['startNode'] == 'BTC'
        assert result_validation[0]['endNode'] == 'USD'
        assert result_validation[0]['from'] == 1
        assert result_validation[0]['to'] == sys.maxsize
        assert result_validation[0]['marketPrice'] == 5000

        assert result_validation[1]['startNode'] == 'USD'
        assert result_validation[1]['endNode'] == 'BTC'
        assert result_validation[1]['from'] == 1
        assert result_validation[1]['to'] == sys.maxsize
        assert result_validation[1]['marketPrice'] == 1/5000

        graphDB.setAssetMarketPrice(assetBaseSymbol='BTC', assetQuotationSymbol='USD',marketPrice=8000,now=2)

        result_validation2 = [
            record["rel"] for record in graphDB.runCypher(
                "MATCH (n)-[r:MARKETPRICE]->(s) RETURN {endNode:endNode(r).symbol,startNode:startNode(r).symbol,from:r.from,to:r.to,marketPrice:r.marketPrice} AS rel ORDER BY r.marketPrice DESC"
            )
        ]
        assert len(result_validation2) == 4
        
        assert result_validation2[3]['startNode'] == 'USD'
        assert result_validation2[3]['endNode'] == 'BTC'
        assert result_validation2[3]['from'] == 2
        assert result_validation2[3]['to'] == sys.maxsize
        assert result_validation2[3]['marketPrice'] == 1/8000
        
        assert result_validation2[2]['startNode'] == 'USD'
        assert result_validation2[2]['endNode'] == 'BTC'
        assert result_validation2[2]['from'] == 1
        assert result_validation2[2]['to'] == 2
        assert result_validation2[2]['marketPrice'] == 1/5000
        
        assert result_validation2[0]['startNode'] == 'BTC'
        assert result_validation2[0]['endNode'] == 'USD'        
        assert result_validation2[0]['from'] == 2
        assert result_validation2[0]['to'] == sys.maxsize
        assert result_validation2[0]['marketPrice'] == 8000

        assert result_validation2[1]['startNode'] == 'BTC'
        assert result_validation2[1]['endNode'] == 'USD'
        assert result_validation2[1]['from'] == 1
        assert result_validation2[1]['to'] == 2
        assert result_validation2[1]['marketPrice'] == 5000

    def test_create_single_asset_node(self):
        graphDB = GraphDB(resetDBData=True)
        nodeid =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=time.time())

        result_validation = [
            record["node"] for record in graphDB.runCypher(
                "MATCH (n) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount} AS node"
            )
        ]

        assert len(nodeid) == 1
        assert len(result_validation) == 1
        assert nodeid[0] == result_validation[0]['id']
        assert result_validation[0]['currentAmount'] == 0
        
        # validate that state node creation
        result_validation2 = [
            record["data"] for record in graphDB.runCypher(
                "MATCH (n)-[r:STATE]->(s:AssetState) WHERE id(n)=%d RETURN {to:r.to,amount:s.amount,name:s.name} AS data" % nodeid[0]
            )
        ]
        assert len(result_validation2) == 1
        assert result_validation2[0]['to'] == sys.maxsize
        assert result_validation2[0]['amount'] == 0
        assert result_validation2[0]['name'] == 'State'

    def test_create_two_asset_nodes_on_two_exchanges(self):
        graphDB = GraphDB(resetDBData=True)
        nodeid1 =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=time.time())
        nodeid2 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'),now=time.time())

        result_validation1 = [
            record["node"] for record in graphDB.runCypher(
                "MATCH (n) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount} AS node"
            )
        ]
        assert len(result_validation1) == 1
        assert nodeid1[0] == result_validation1[0]['id']

        result_validation2 = [
            record["node"] for record in graphDB.runCypher(
                "MATCH (n) WHERE n.exchange='Kraken' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount} AS node"
            )
        ]
        assert len(result_validation2) == 1
        assert nodeid2[0] == result_validation2[0]['id']

        result_validation3 = [
            record["rel"] for record in graphDB.runCypher(
                "MATCH (a)-[r:EXCHANGE]->(b) WHERE a.exchange='Kraken' AND a.symbol='BTC' AND b.exchange='Bitfinex' AND a.symbol='BTC' RETURN {limitPrice:r.limitPrice,meanPrice:r.meanPrice,to:r.to} AS rel"
            )
        ]
        assert len(result_validation3) == 1    
        assert result_validation3[0]['limitPrice']==1
        assert result_validation3[0]['meanPrice']==1
        assert result_validation3[0]['to']==sys.maxsize

        result_validation4 = [
            record["rel"] for record in graphDB.runCypher(
                "MATCH (a)-[r:EXCHANGE]->(b) WHERE a.exchange='Bitfinex' AND a.symbol='BTC' AND b.exchange='Kraken' AND a.symbol='BTC' RETURN {limitPrice:r.limitPrice,meanPrice:r.meanPrice,to:r.to} AS rel"
            )
        ]
        assert len(result_validation4) == 1    
        assert result_validation4[0]['limitPrice']==1
        assert result_validation4[0]['meanPrice']==1
        assert result_validation4[0]['to']==sys.maxsize
    
    def test_arbitrage_test_with_three_nodes(self):
        graphDB = GraphDB(resetDBData=True)
        graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=time.time())
        graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'),now=time.time())
        graphDB.createAssetNode(Asset(exchange='Kraken', symbol='ETH'),now=time.time())

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                orderbook=OrderBook(symbol='BTC/ETH',orderbook=[[2,1]],rateBTCxBase=1),
                feeRate=0,
                timeToLiveSec=5),now=time.time())

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                orderbook=OrderBook(symbol='ETH/BTC',orderbook='[[0.6,1000]]',rateBTCxBase=1/0.6),
                feeRate=0,
                timeToLiveSec=5),now=time.time())

        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=time.time())
        assert len(arbitrage_cycles) == 1    
        assert (arbitrage_cycles[0]['assets'][0]['amount'],arbitrage_cycles[0]['assets'][0]['exchange'],arbitrage_cycles[0]['assets'][0]['symbol']) == (0,'Kraken','BTC')
        assert (arbitrage_cycles[0]['assets'][1]['amount'],arbitrage_cycles[0]['assets'][1]['exchange'],arbitrage_cycles[0]['assets'][1]['symbol']) == (0,'Kraken','ETH')
        assert (arbitrage_cycles[0]['assets'][2]['amount'],arbitrage_cycles[0]['assets'][2]['exchange'],arbitrage_cycles[0]['assets'][2]['symbol']) == (0,'Kraken','BTC')
        assert (arbitrage_cycles[0]['profit']) == (2.0*0.6)*100-100
        assert (arbitrage_cycles[0]['path'][0]['meanPrice']) == 2
        assert (arbitrage_cycles[0]['path'][1]['meanPrice']) == 0.6        

        time.sleep(1)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=1.1,now=time.time())
        time.sleep(0.6)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=0.5,now=time.time())

    def test_arbitrage_test_with_four_nodes(self):
        with GraphDB(resetDBData=True) as graphDB:        
            graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=0)

            ###################################################################
            # Update trade relationship multiple (3x) times to verify that
            # relationships are properly end-dated and new relationships are created
            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    orderbook=OrderBook(symbol='BTC/ETH',orderbook='[[1,1]]',rateBTCxBase=1),
                    feeRate=0.002,
                    timeToLiveSec=4),now=1)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    orderbook=OrderBook(symbol='BTC/ETH',orderbook='[[2,1]]',rateBTCxBase=1),
                    feeRate=0.002,
                    timeToLiveSec=2),now=2)
            
            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    orderbook=OrderBook(symbol='BTC/ETH',orderbook='[[3,1]]',rateBTCxBase=1),
                    feeRate=0.002,
                    timeToLiveSec=5),now=3)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                    quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                    orderbook=OrderBook(symbol='ETH/BTC',orderbook='[[4,1]]',rateBTCxBase=1/4),
                    feeRate=0.002,
                    timeToLiveSec=3),now=3)

            ###################################################################
            # Add extra-exchange relationship
            # 
            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Poloniex', symbol='BTC'),
                    orderbook=OrderBook(symbol='BTC/BTC',orderbook='[[1,1]]',rateBTCxBase=1),
                    feeRate=0.002,
                    timeToLiveSec=3),now=3)

            ###################################################################
            # Update trade relationship multiple (3x) times to verify that
            # state are properly end-dated and new states are created
            graphDB.setAssetState(
                asset=Asset(exchange='Kraken', symbol='BTC'),
                assetState=AssetState(amount=1),now=4)

            graphDB.setAssetState(
                asset=Asset(exchange='Kraken', symbol='BTC'),
                assetState=AssetState(amount=2),now=4.1)

            graphDB.setAssetState(
                asset=Asset(exchange='Kraken', symbol='BTC'),
                assetState=AssetState(amount=3),now=4.2)
            
            ###################################################################
            # validate the properties of all nodes by hash
            #
            result_validation_hash = graphDB.getNodesPropertyHash()
            # RUN this to recalculate reference hashes: pprint.pformat(result_validation_hash).replace('\n','').replace(' ','')
            reference_hash = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','a19a688ef054e56101317f7dac3dda6e','9887c14ada99b8c72b7996a460afda1e','905ed9c758ce981d7ea0fb1bef55873c','89586e3b288ac93f329280eb9f025d18','7b54e3841e6574caaf429917c88e2bac','17032c1a5da060b45d736930551267b7','0f67e27fbf10b058924b76dce3774945']
            pairs = zip(result_validation_hash, reference_hash)
            assert any(x != y for x, y in pairs) == False

            ###################################################################
            # validate the properties of all relationships by hash
            #
            result_validation_hash = graphDB.getRelsPropertyHash()

            reference_hash=['fd6e1f185a35a2042c64b97f834656f7','ec10fcbdfa1e7ca674f2a0b9d601cda9','c4d43e1375bc396312ffb36791b34715','c0b4427029541c7684e98427cbd96879','b7d4604016369997ce690aace8046853','b08833550d8ade29e79e6b4920039041','a63104dcec0c22e268c284214b122379','a63104dcec0c22e268c284214b122379','a49053d9a38a3224ab83d1776d552f93','6d2a632e8fab0dc7d0f21368563e53af','6d2a632e8fab0dc7d0f21368563e53af','6d2a632e8fab0dc7d0f21368563e53af','637a2b7cba2bc723468ec71cfe0d3be7','5143198f9b34006e9e12056ffb9dc8ae','4c9e92370a8ad1abad2fe220ff403b25','4471bedca0fc544d95028ed73970c9c3','3b0019a126cfd32991c9b7d65f335daa','39b9b007f53dd928c53167eb5aa16689','3810b20f1ee0cbfd2f7bcba1d7b6ca9e','29682f4faed9afeed822943c1db4589f','1f9348d04b9de6cf012f2d5fef334679','100a8e68fef0f5755c02100f6073430e','01c6e0568879cdc039cf52aebe15cb4f']
            pairs = zip(result_validation_hash, reference_hash)
            assert any(x != y for x, y in pairs) == False

            r = graphDB.get_latest_prices(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),now=time.time()
            )