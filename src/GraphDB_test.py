import pytest
import sys
from GraphDB import GraphDB, Asset


class TestClass(object):
    def create_single_asset_node(self):
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

    def create_two_asset_nodes_on_two_exchanges(self):
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
    
    def arbitrage_test_with_three_nodes(self):
        graphDB = GraphDB(resetDBData=True)
        nodeid1 =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'))
        nodeid2 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'))
        nodeid2 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='ETH'))

if __name__ == "__main__":
    tc = TestClass()
    tc.create_single_asset_node()
    tc.create_two_asset_nodes_on_two_exchanges()
    tc.arbitrage_test_with_three_nodes()
