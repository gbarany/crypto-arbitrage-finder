import pytest
import sys
from GraphDB import GraphDB, Asset,TradingRelationship, AssetState
import time
import pprint
import hashlib
import json
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
                "MATCH (a)-[r:EXCHANGE]->(b) WHERE a.exchange='Kraken' AND a.symbol='BTC' AND b.exchange='Bitfinex' AND a.symbol='BTC' RETURN {limit_price:r.limit_price,mean_price:r.mean_price,to:r.to} AS rel"
            )
        ]
        assert len(result_validation3) == 1    
        assert result_validation3[0]['limit_price']==1
        assert result_validation3[0]['mean_price']==1
        assert result_validation3[0]['to']==sys.maxsize

        result_validation4 = [
            record["rel"] for record in graphDB.runCypher(
                "MATCH (a)-[r:EXCHANGE]->(b) WHERE a.exchange='Bitfinex' AND a.symbol='BTC' AND b.exchange='Kraken' AND a.symbol='BTC' RETURN {limit_price:r.limit_price,mean_price:r.mean_price,to:r.to} AS rel"
            )
        ]
        assert len(result_validation4) == 1    
        assert result_validation4[0]['limit_price']==1
        assert result_validation4[0]['mean_price']==1
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
                mean_price=2,
                limit_price=2,
                orderbook='[[2,1]]',
                fee=0,
                timeToLiveSec=5),now=time.time())

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                mean_price=0.6,
                limit_price=0.6,
                orderbook='[[0.6,1]]',
                fee=0,
                timeToLiveSec=5),now=time.time())
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=time.time())
        assert len(arbitrage_cycles) == 1    
        assert (arbitrage_cycles[0]['assets'][0]['amount'],arbitrage_cycles[0]['assets'][0]['exchange'],arbitrage_cycles[0]['assets'][0]['symbol']) == (0,'Kraken','BTC')
        assert (arbitrage_cycles[0]['assets'][1]['amount'],arbitrage_cycles[0]['assets'][1]['exchange'],arbitrage_cycles[0]['assets'][1]['symbol']) == (0,'Kraken','ETH')
        assert (arbitrage_cycles[0]['assets'][2]['amount'],arbitrage_cycles[0]['assets'][2]['exchange'],arbitrage_cycles[0]['assets'][2]['symbol']) == (0,'Kraken','BTC')
        assert (arbitrage_cycles[0]['profit']) == (2.0*0.6)*100-100
        assert (arbitrage_cycles[0]['path'][0]['mean_price']) == 2
        assert (arbitrage_cycles[0]['path'][1]['mean_price']) == 0.6        

        time.sleep(1)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=1.1,now=time.time())
        time.sleep(0.6)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=0.5,now=time.time())

    def test_arbitrage_test_with_four_nodes(self):
        with GraphDB(resetDBData=True) as graphDB:        
            graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=0)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    mean_price=1,
                    limit_price=1,
                    orderbook='[[1,1]]',
                    fee=0.002,
                    timeToLiveSec=4),now=1)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    mean_price=2,
                    limit_price=2,
                    orderbook='[[2,1]]',
                    fee=0.002,
                    timeToLiveSec=2),now=1)
            
            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    mean_price=3,
                    limit_price=3,
                    orderbook='[[3,1]]',
                    fee=0.002,
                    timeToLiveSec=5),now=2)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                    quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                    mean_price=4,
                    limit_price=4,
                    orderbook='[[4,1]]',
                    fee=0.002,
                    timeToLiveSec=3),now=2)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Poloniex', symbol='BTC'),
                    mean_price=1,
                    limit_price=1,
                    orderbook='[[1,1]]',
                    fee=0.002,
                    timeToLiveSec=3),now=3)

            graphDB.setAssetState(
                asset=Asset(exchange='Kraken', symbol='BTC'),
                assetState=AssetState(amount=1),now=4)

            time.sleep(1)

            graphDB.setAssetState(
                asset=Asset(exchange='Kraken', symbol='BTC'),
                assetState=AssetState(amount=2),now=4.1)

            time.sleep(1)

            graphDB.setAssetState(
                asset=Asset(exchange='Kraken', symbol='BTC'),
                assetState=AssetState(amount=3),now=4.2)
            
            ###################################################################
            # validate the properties of all nodes by hash
            #
            result_validation_hash = [record["hash"] for record in graphDB.runCypher(
                "MATCH (n) "
                "WITH n " 
                "ORDER BY n.symbol, n.exchange " 
                "WITH collect(properties(n)) AS propresult, n " 
                "RETURN apoc.util.md5(propresult) as hash, propresult, id(n) as nodeid " 
                "ORDER BY hash DESC ")]
            # RUN this to recalculate reference hashes: pprint.pformat(result_validation_hash).replace('\n','').replace(' ','')
            reference_hash = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','a19a688ef054e56101317f7dac3dda6e','9887c14ada99b8c72b7996a460afda1e','905ed9c758ce981d7ea0fb1bef55873c','89586e3b288ac93f329280eb9f025d18','7b54e3841e6574caaf429917c88e2bac','17032c1a5da060b45d736930551267b7','0f67e27fbf10b058924b76dce3774945']
            pairs = zip(result_validation_hash, reference_hash)
            assert any(x != y for x, y in pairs) == False

            ###################################################################
            # validate the properties of all relationships by hash
            #
            result_validation_hash = [record["hash"] for record in graphDB.runCypher(
                "MATCH (n)-[r]->(k) "
                "WITH r "
                "ORDER BY r.uuid "
                "WITH collect(properties(r)) AS propresult,r "
                "RETURN apoc.util.md5(propresult) as hash, propresult, startNode(r) as startNode, endNode(r) as endNode, r "
                "ORDER BY hash DESC ")]

            reference_hash=['ec10fcbdfa1e7ca674f2a0b9d601cda9','da4da11df103c6f26a51ebd2fb34aa67','d6563434efcee33c6ac3ad9ebe0787f5','c0b4427029541c7684e98427cbd96879','b7d4604016369997ce690aace8046853','b320728309742c4eb21d41f21a03bd71','b08833550d8ade29e79e6b4920039041','a63104dcec0c22e268c284214b122379','a63104dcec0c22e268c284214b122379','a49053d9a38a3224ab83d1776d552f93','88b96342b6de4f381d5f71963abd7588','6d2a632e8fab0dc7d0f21368563e53af','6d2a632e8fab0dc7d0f21368563e53af','6d2a632e8fab0dc7d0f21368563e53af','4c9e92370a8ad1abad2fe220ff403b25','4471bedca0fc544d95028ed73970c9c3','3a8069803372183aafc781ce9ac7a625','39d74f889ff2798f991fcc1e07a8dcfd','39b9b007f53dd928c53167eb5aa16689','3810b20f1ee0cbfd2f7bcba1d7b6ca9e','26da9c8253d4dd61209cf748f841b8e1','21fc5c91d41e4a8d55f013688e5ff2c5','01c6e0568879cdc039cf52aebe15cb4f']
            pairs = zip(result_validation_hash, reference_hash)
            assert any(x != y for x, y in pairs) == False

            r = graphDB.get_latest_prices(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),now=time.time()
            )

            print(r)
        
            r = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=time.time())
            print(r)
            print(time.time())
