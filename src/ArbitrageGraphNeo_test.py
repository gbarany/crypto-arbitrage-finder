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
        arbitrage_graph_neo = ArbitrageGraphNeo(edgeTTL=edgeTTL,neo4j_mode=neo4j_mode,resetDBData=True)
        
        orderBookPair = OrderBookPair(symbol='BTC/USD', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5000)
        
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', feeRate= 0.002, orderBookPair=orderBookPair,now=1)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['e3fcf50ed9584411871a0840c9de1b49','b749b5c8c7c3c3aca074484a913cdd97','99818c5ae290457fc425f1e5cd095832','96bf91c8f53617498bf884510f86067d','4471bedca0fc544d95028ed73970c9c3','4471bedca0fc544d95028ed73970c9c3']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False


    def test_twoOderbookEntries(self):
        edgeTTL=5
        neo4j_mode = FWLiveParams.neo4j_mode_localhost
        arbitrage_graph_neo = ArbitrageGraphNeo(edgeTTL=edgeTTL,neo4j_mode=neo4j_mode,resetDBData=True)
        
        orderBookPair1 = OrderBookPair(symbol='BTC/USD', asks=[[5000,1], [6000,2]], bids=[[4000,1], [3000,2]],rateBTCxBase=1,rateBTCxQuote=5500)
        orderBookPair2 = OrderBookPair(symbol='BTC/USD', asks=[[4000,0.5], [5000,0.5]], bids=[[3000,0.5], [2000,0.5]],rateBTCxBase=1,rateBTCxQuote=4500)
        
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', feeRate= 0.002, orderBookPair=orderBookPair1,now=1)
        arbitrage_graph_neo.updatePoint(symbol='BTC/USD', exchange='kraken', feeRate= 0.002, orderBookPair=orderBookPair2,now=2)
        
        nodesHash = arbitrage_graph_neo.graphDB.getNodesPropertyHash()
        relsHash = arbitrage_graph_neo.graphDB.getRelsPropertyHash()

        nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','c13703b55511885f7efea8341cf455cc','51422cecfdd980679b2119651b326258']
        relsHash_ref = ['f2de8c5b94734abac66e55119406d075','cccddf9a43eae12aecc167a0b0fabc81','bed170122c0461fa963aad3e2527b541','b8d1a718dab006642810e7aeee0b023e','8491c1c9c0c813d6eda6d91c4e3dfa8e','819e15737713c1c45ba04e1d6e95401d','4471bedca0fc544d95028ed73970c9c3','4471bedca0fc544d95028ed73970c9c3','18ffb5971054109194cd05faec59c950','0e4e4028e90c3e7db48fa9b8a38f9a2a']
        assert any(x != y for x, y in zip(nodesHash+relsHash, nodesHash_ref+relsHash_ref)) == False
