import pytest
import sys
from GraphDB import GraphDB, Asset,TradingRelationship
import time

class TestClass(object):

    def test_create_single_asset_node(self):
        graphDB = GraphDB(resetDBData=True)
        nodeid =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'))

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
        nodeid1 =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'))
        nodeid2 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'))

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
        nodeid1 =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'))
        nodeid2 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'))
        nodeid3 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='ETH'))

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                mean_price=2,
                limit_price=2,
                orderbook='[[2,1]]',
                fee=0,
                timeToLiveSec=5))

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                mean_price=0.6,
                limit_price=0.6,
                orderbook='[[0.6,1]]',
                fee=0,
                timeToLiveSec=5))
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5)
        assert len(arbitrage_cycles) == 1    
        assert (arbitrage_cycles[0]['assets'][0]['amount'],arbitrage_cycles[0]['assets'][0]['exchange'],arbitrage_cycles[0]['assets'][0]['symbol']) == (0,'Kraken','BTC')
        assert (arbitrage_cycles[0]['assets'][1]['amount'],arbitrage_cycles[0]['assets'][1]['exchange'],arbitrage_cycles[0]['assets'][1]['symbol']) == (0,'Kraken','ETH')
        assert (arbitrage_cycles[0]['assets'][2]['amount'],arbitrage_cycles[0]['assets'][2]['exchange'],arbitrage_cycles[0]['assets'][2]['symbol']) == (0,'Kraken','BTC')
        assert (arbitrage_cycles[0]['profit']) == (2.0*0.6)*100-100
        assert (arbitrage_cycles[0]['path'][0]['mean_price']) == 2
        assert (arbitrage_cycles[0]['path'][1]['mean_price']) == 0.6        

        time.sleep(1)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=1.1)
        time.sleep(0.6)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=0.5)
