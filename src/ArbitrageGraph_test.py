import pytest  
import numpy as np
from ArbitrageGraph import ArbitrageGraph


class TestClass(object):

    def test_one(self):
        arbitrageGraph = ArbitrageGraph()
        p1=arbitrageGraph.updatePoint(symbol="BTC/USD",exchangename="kraken",fee_rate=0.0,l_ask=10000,h_bid=9000,timestamp=0)
        assert p1.isNegativeCycle == False
        
        p2=arbitrageGraph.updatePoint(symbol="ETH/USD",exchangename="kraken",fee_rate=0.0,l_ask=200,h_bid=100,timestamp=1)
        assert p2.isNegativeCycle == False
        
        p3=arbitrageGraph.updatePoint(symbol="BTC/ETH",exchangename="kraken",fee_rate=0.0,l_ask=5,h_bid=4,timestamp=2)
        assert p3.isNegativeCycle == True

        with pytest.raises(ValueError):
            path=arbitrageGraph.getPath(nodes=["BTC","XRP","ETH"],timestamp=4)

        with pytest.raises(ValueError):
            path=arbitrageGraph.getPath(nodes=["kraken-BTC","kraken-XRP","kraken-ETH"],timestamp=4)

        path=arbitrageGraph.getPath(nodes=["kraken-BTC","kraken-USD","kraken-ETH","kraken-BTC"],timestamp=4)
        assert path.edges_age_s == [4,3,2]
        assert path.edges_weight==[-np.log(9000),-np.log(1/200),-np.log(1/5)]
        assert path.hops==3
        assert path.exchanges_involved==['kraken']
        assert path.nof_exchanges_involved==1

    def test_TTLTest_one(self):
        arbitrageGraph = ArbitrageGraph(edgeTTL=5)
        arbitrageGraph.updatePoint(symbol="BTC/USD",exchangename="kraken",fee_rate=0.0,l_ask=10000,h_bid=9000,timestamp=0)
        arbitrageGraph.updatePoint(symbol="ETH/USD",exchangename="kraken",fee_rate=0.0,l_ask=200,h_bid=100,timestamp=1)
        arbitrageGraph.updatePoint(symbol="BTC/ETH",exchangename="kraken",fee_rate=0.0,l_ask=5,h_bid=4,timestamp=2)

        with pytest.raises(ValueError):
            arbitrageGraph.getPath(nodes=["kraken-BTC","kraken-USD","kraken-ETH","kraken-BTC"],timestamp=6)
        

    def test_TTLTest_two(self):
        arbitrageGraph = ArbitrageGraph(edgeTTL=5)
        arbitrageGraph.updatePoint(symbol="BTC/USD",exchangename="kraken",fee_rate=0.0,l_ask=10000,h_bid=9000,timestamp=0)
        arbitrageGraph.updatePoint(symbol="ETH/USD",exchangename="kraken",fee_rate=0.0,l_ask=200,h_bid=100,timestamp=3)
        arbitrageGraph.updatePoint(symbol="BTC/ETH",exchangename="kraken",fee_rate=0.0,l_ask=5,h_bid=4,timestamp=4)
        
        with pytest.raises(ValueError):
            arbitrageGraph.getPath(nodes=["kraken-BTC","kraken-USD","kraken-ETH","kraken-BTC"],timestamp=6)

        arbitrageGraph.updatePoint(symbol="BTC/USD",exchangename="kraken",fee_rate=0.0,l_ask=12000,h_bid=5000,timestamp=5)

        path=arbitrageGraph.getPath(nodes=["kraken-BTC","kraken-USD","kraken-ETH","kraken-BTC"],timestamp=6)
        assert path.edges_age_s == [1,3,2]
        assert path.edges_weight==[-np.log(5000),-np.log(1/200),-np.log(1/5)]
        assert path.hops==3
        assert path.exchanges_involved==['kraken']
        assert path.nof_exchanges_involved==1