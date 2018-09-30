import pytest  
from GraphDB import GraphDB, Asset

#@pytest.fixture(scope="class")
#def getGraphDB():
#    graphDB = GraphDB(resetDBData=True)
#    return FeeStore()

class TestClass(object):

    def _createAssetNode(self):
        graphDB = GraphDB(resetDBData=True)
        result = [record["node"] for record in graphDB.createAssetNode(Asset(exchange='Bitfinex',symbol='BTC'))]
        result_validation = [record["node"] for record in graphDB.runCypher("MATCH (n) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN id(n) AS node")]
        
        assert len(result_validation) == 1
        assert result[0] == result_validation[0]


if __name__ == "__main__":
    tc=TestClass()
    tc._createAssetNode()