import pytest
import sys
from GraphDB import GraphDB, Asset,TradingRelationship, AssetState
import time
import pprint
import time
from FWLiveParams import FWLiveParams
from ArbitrageGraphNeo import ArbitrageGraphNeo
from OrderBook import OrderBook, OrderBookPair
import time

class TestClass(object):

    def test_singleOderbookEntry(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(edgeTTL=edgeTTL,neo4j_mode=neo4j_mode,resetDBData=True,volumeBTCs=[1])
        
        orderBookPair = OrderBookPair(symbol='BTC/USD', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5000,feeRate= 0.002)
        
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', orderBookPair=orderBookPair,now=1)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['f84eed713a6d6a68fc62d7b432918a2c','adda2051ec08e4851837d4758c9cff04','8ebdbdd4fbd496a13f02113c97bad76c','8ebdbdd4fbd496a13f02113c97bad76c','416b158097469c70d18015dad3ec1eb1','29f4d99dfa375a836c897ad90f44c0da']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False

    def test_singleOderbookEntryMultipleVolumes(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(edgeTTL=edgeTTL,neo4j_mode=neo4j_mode,resetDBData=True,volumeBTCs=[1,1.5,2])
        
        orderBookPair = OrderBookPair(symbol='BTC/USD', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5000,feeRate= 0.002)
        
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', orderBookPair=orderBookPair,now=1)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['f84eed713a6d6a68fc62d7b432918a2c','c4122b504d51abd4d24f67ef8ea219a8','adda2051ec08e4851837d4758c9cff04','8ebdbdd4fbd496a13f02113c97bad76c','8ebdbdd4fbd496a13f02113c97bad76c','803337cfc27d15a71d027ea615b326ef','684f4503eb804139c1590f24ef67f32d','42615e21bdbc36a2d58344b933ef79b3','416b158097469c70d18015dad3ec1eb1','29f4d99dfa375a836c897ad90f44c0da']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False

    def test_twoOderbookEntries(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(edgeTTL=edgeTTL,neo4j_mode=neo4j_mode,resetDBData=True,volumeBTCs=[1])
        
        orderBookPair1 = OrderBookPair(symbol='BTC/USD', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5500,feeRate= 0.002)
        orderBookPair2 = OrderBookPair(symbol='BTC/USD', asks=[[4000,0.5], [5000,0.5]], bids=[[3000,0.5], [2000,0.5]],rateBTCxBase=1,rateBTCxQuote=4500,feeRate= 0.002)
        
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', orderBookPair=orderBookPair1,now=1)
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', orderBookPair=orderBookPair2,now=2)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['e11ba05df801943ccb8b19a277de61ec','dc0eda95a2aedf00a427971b5d1173c0','d45f9486a8a2918b6c43cdba56d40597','8ebdbdd4fbd496a13f02113c97bad76c','8ebdbdd4fbd496a13f02113c97bad76c','82d2845e0c3d23294b80b4dfa734662e','7a47652d70d57abef65ba3d7d75c367e','56f9646d82613a09ac6c0c3dd7992d7e','186354bdd7b13357a940eff550b5da1d','04ab022704fa04e01c96a528373444d7']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False
