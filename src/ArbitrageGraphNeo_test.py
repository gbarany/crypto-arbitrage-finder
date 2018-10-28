import pytest
import sys
from GraphDB import GraphDB, AssetState
import time
import pprint
import time
from FWLiveParams import FWLiveParams
from ArbitrageGraphNeo import ArbitrageGraphNeo
from OrderBook import OrderBook, OrderBookPair, Asset
import time

class TestClass(object):

    def test_singleOderbookEntry(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(neo4j_mode=neo4j_mode,resetDBData=True,volumeBTCs=[1])
        
        orderBookPair = OrderBookPair(timestamp=1,symbol='BTC/USD',  exchange='kraken', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5000,feeRate= 0.002,timeToLiveSec=edgeTTL)
        
        arbitrage_graph_neo.updatePoint(orderBookPair=orderBookPair)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']        
        assert any(x != y for x, y in zip(nodesHash, nodesHash_ref)) == False
        relsHash_ref = ['f84eed713a6d6a68fc62d7b432918a2c','f2143fbd287ac3920a6feff92dd96fc6','c296c2b01ed00cd435de390d43d8f40f','8ebdbdd4fbd496a13f02113c97bad76c','8ebdbdd4fbd496a13f02113c97bad76c','29f4d99dfa375a836c897ad90f44c0da']
        assert any(x != y for x, y in zip(relsHash, relsHash_ref)) == False

    def test_singleOderbookEntryMultipleVolumes(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(neo4j_mode=neo4j_mode,resetDBData=True,volumeBTCs=[1,1.5,2])
        
        orderBookPair = OrderBookPair(timestamp=1,symbol='BTC/USD', exchange='kraken',asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5000,feeRate= 0.002,timeToLiveSec=edgeTTL)
        
        arbitrage_graph_neo.updatePoint(orderBookPair=orderBookPair)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['f84eed713a6d6a68fc62d7b432918a2c','f2143fbd287ac3920a6feff92dd96fc6','c2e1661af197e1e563af634b21c636a4','c296c2b01ed00cd435de390d43d8f40f','8ebdbdd4fbd496a13f02113c97bad76c','8ebdbdd4fbd496a13f02113c97bad76c','507c019717d65c292c08f049c01a897e','29f4d99dfa375a836c897ad90f44c0da','1bd2c1fcb808b9edcd966827691a5046','084c7fc9ba737a8ce081882c24eaf1cf']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False

    def test_twoOderbookEntries(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(neo4j_mode=neo4j_mode,resetDBData=True,volumeBTCs=[1])
        
        orderBookPair1 = OrderBookPair(timestamp=1,symbol='BTC/USD', exchange='kraken', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5500,feeRate= 0.002,timeToLiveSec=edgeTTL)
        orderBookPair2 = OrderBookPair(timestamp=2,symbol='BTC/USD', exchange='kraken', asks=[[4000,0.5], [5000,0.5]], bids=[[3000,0.5], [2000,0.5]],rateBTCxBase=1,rateBTCxQuote=4500,feeRate= 0.002,timeToLiveSec=edgeTTL)
        
        arbitrage_graph_neo.updatePoint(orderBookPair=orderBookPair1)
        arbitrage_graph_neo.updatePoint(orderBookPair=orderBookPair2)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['dc0eda95a2aedf00a427971b5d1173c0','d45f9486a8a2918b6c43cdba56d40597','c8622fff62948fabdb193de41b380aed','96a201c1421d6ef1678434037a6f6fa6','8ebdbdd4fbd496a13f02113c97bad76c','8ebdbdd4fbd496a13f02113c97bad76c','82d2845e0c3d23294b80b4dfa734662e','4944083f677a04f2c405c10fd1f25ff8','372f5b3d01d1357ad69aadd06adf7f00','186354bdd7b13357a940eff550b5da1d']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False
