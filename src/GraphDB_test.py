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
                "MATCH (n)-[r:STATE]->(s) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount,amount:s.amount,stateRelFrom:r._from,stateRelTo:r._to} AS node"
            )
        ]
        assert len(result_validation) == 1
        assert result_validation[0]['amount'] == 0
        assert result_validation[0]['currentAmount'] == 0
        assert result_validation[0]['stateRelTo'] == sys.maxsize

        graphDB.setAssetState(Asset(exchange='Bitfinex', symbol='BTC'),AssetState(amount=2),now=time.time())
        result_validation2 = [
            record["node"] for record in graphDB.runCypher(
                "MATCH (n)-[r:STATE]->(s) WHERE n.exchange='Bitfinex' AND n.symbol='BTC' RETURN {id:id(n),currentAmount:n.currentAmount,amount:s.amount,stateRelFrom:r._from,stateRelTo:r._to} AS node"
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
                "MATCH (n)-[r:MARKETPRICE]->(s) RETURN {endNode:endNode(r).symbol,startNode:startNode(r).symbol,from:r._from,to:r._to,marketPrice:r.marketPrice} AS rel ORDER BY r.marketPrice DESC"
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
                "MATCH (n)-[r:MARKETPRICE]->(s) RETURN {endNode:endNode(r).symbol,startNode:startNode(r).symbol,from:r._from,to:r._to,marketPrice:r.marketPrice} AS rel ORDER BY r.marketPrice DESC"
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
        graphDB.setAssetMarketPrice(assetBaseSymbol='BTC', assetQuotationSymbol='USD',marketPrice=10000,now=3)

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
                "MATCH (n)-[r:STATE]->(s:StockState) WHERE id(n)=%d RETURN {to:r._to,amount:s.amount,name:s.name} AS data" % nodeid[0]
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
                "MATCH (a)-[r:EXCHANGE]->(b) WHERE a.exchange='Kraken' AND a.symbol='BTC' AND b.exchange='Bitfinex' AND a.symbol='BTC' RETURN {limitPrice:r.limitPrice,meanPrice:r.meanPrice,to:r._to} AS rel"
            )
        ]
        assert len(result_validation3) == 1    
        assert result_validation3[0]['limitPrice']==1
        assert result_validation3[0]['meanPrice']==1
        assert result_validation3[0]['to']==sys.maxsize

        result_validation4 = [
            record["rel"] for record in graphDB.runCypher(
                "MATCH (a)-[r:EXCHANGE]->(b) WHERE a.exchange='Bitfinex' AND a.symbol='BTC' AND b.exchange='Kraken' AND a.symbol='BTC' RETURN {limitPrice:r.limitPrice,meanPrice:r.meanPrice,to:r._to} AS rel"
            )
        ]
        assert len(result_validation4) == 1    
        assert result_validation4[0]['limitPrice']==1
        assert result_validation4[0]['meanPrice']==1
        assert result_validation4[0]['to']==sys.maxsize
    
    def test_arbitrage_test_with_three_nodes(self):
        volumeBTCs = [0.1,1]
        graphDB = GraphDB(resetDBData=True)
        graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),now=0)
        graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'),now=0.1)
        graphDB.createAssetNode(Asset(exchange='Kraken', symbol='ETH'),now=0.2)

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                orderbook=OrderBook(symbol='BTC/ETH',orderbook=[[2,1]],rateBTCxBase=1,rateBTCxQuote=2,feeRate=0),
                timeToLiveSec=5),now=0.3,volumeBTCs=volumeBTCs)

        graphDB.addTradingRelationship(
            TradingRelationship(
                baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                orderbook=OrderBook(symbol='ETH/BTC',orderbook='[[0.6,1000]]',rateBTCxBase=1/0.6,rateBTCxQuote=1,feeRate=0),
                timeToLiveSec=5),now=0.4,volumeBTCs=volumeBTCs)

        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=0.5,volumeBTCs=volumeBTCs )
        assert len(arbitrage_cycles) == 2   
        assert (arbitrage_cycles[0]['volumeBTC']) == 0.1
        for i in range(2):
            assert (arbitrage_cycles[i]['assets'][0]['amount'],arbitrage_cycles[0]['assets'][0]['exchange'],arbitrage_cycles[0]['assets'][0]['symbol']) == (0,'Kraken','BTC')
            assert (arbitrage_cycles[i]['assets'][1]['amount'],arbitrage_cycles[0]['assets'][1]['exchange'],arbitrage_cycles[0]['assets'][1]['symbol']) == (0,'Kraken','ETH')
            assert (arbitrage_cycles[i]['assets'][2]['amount'],arbitrage_cycles[0]['assets'][2]['exchange'],arbitrage_cycles[0]['assets'][2]['symbol']) == (0,'Kraken','BTC')
            assert (arbitrage_cycles[i]['profit']) == (2.0*0.6)*100-100
            assert (arbitrage_cycles[i]['path'][0]['meanPrice']) == 2
            assert (arbitrage_cycles[i]['path'][1]['meanPrice']) == 0.6        


        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=1.1,now=1.5,volumeBTCs=volumeBTCs)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=0.5,now=2.1,volumeBTCs=volumeBTCs)

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
                    orderbook=OrderBook(symbol='BTC/ETH',orderbook='[[1,1]]',rateBTCxBase=1,rateBTCxQuote=1,feeRate=0.002),
                    timeToLiveSec=4),now=1)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    orderbook=OrderBook(symbol='BTC/ETH',orderbook='[[2,1]]',rateBTCxBase=1,rateBTCxQuote=2,feeRate=0.002),
                    timeToLiveSec=2),now=2)
            
            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Kraken', symbol='ETH'),
                    orderbook=OrderBook(symbol='BTC/ETH',orderbook='[[3,1]]',rateBTCxBase=1,rateBTCxQuote=3,feeRate=0.002),
                    timeToLiveSec=5),now=3)

            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='ETH'),
                    quotationAsset=Asset(exchange='Kraken', symbol='BTC'),
                    orderbook=OrderBook(symbol='ETH/BTC',orderbook='[[4,1]]',rateBTCxBase=1/4,rateBTCxQuote=1,feeRate=0.002),
                    timeToLiveSec=3),now=3)

            ###################################################################
            # Add extra-exchange relationship
            # 
            graphDB.addTradingRelationship(
                TradingRelationship(
                    baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                    quotationAsset=Asset(exchange='Poloniex', symbol='BTC'),
                    orderbook=OrderBook(symbol='BTC/BTC',orderbook='[[1,1]]',rateBTCxBase=1,rateBTCxQuote=1,feeRate=0.002),
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
            nodesHash = graphDB.getNodesPropertyHash()
            # RUN this to recalculate reference hashes: pprint.pformat(result_validation_hash).replace('\n','').replace(' ','')
            nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','a19a688ef054e56101317f7dac3dda6e','9887c14ada99b8c72b7996a460afda1e','905ed9c758ce981d7ea0fb1bef55873c','89586e3b288ac93f329280eb9f025d18','7b54e3841e6574caaf429917c88e2bac','17032c1a5da060b45d736930551267b7','0f67e27fbf10b058924b76dce3774945']

            pairs = zip(nodesHash, nodesHash_ref)
            assert any(x != y for x, y in pairs) == False

            ###################################################################
            # validate the properties of all relationships by hash
            #
            relsHash = graphDB.getRelsPropertyHash()

            relsHash_ref=['ed7127753c7561aff65aa934c3ec0b08','dfc283f9c1abdcf0149686398f22b42b','dd7d2733c82633e5a2b92d69b917ad0f','d10dd681cd3c15d953fd5ddf4e35730e','cd114e0f17696cf539dedd2f71acd881','cd114e0f17696cf539dedd2f71acd881','cd114e0f17696cf539dedd2f71acd881','ca279cb0e9016bc582a76fb36c6fb678','b7ce49bb20b4d32d31a1861e48b7c6c2','ab575c242a6e2111badc21dee2409fc3','9189f2f8081734c378a924a7fc818f63','909c239aa4101a8394cf96f8b7bd216f','9062679b13a5bf1e9a3896aae1a3fe48','8ebdbdd4fbd496a13f02113c97bad76c','7bf967d53beda3653c66b4b013c8ef2e','7bf967d53beda3653c66b4b013c8ef2e','7a519a3f90b4f903841bca9690f6c189','6d4c16b4fe29860e9d59307e5813ecf9','3ab3d46ae90b2899ca7e48b8d454e6e8','37a062864b4cdcc4fec3faa0030f9e86','11a2fb79dcb1a216a3a062aa90e44e95','1130f54c147f2e6b8f0fab0620c150ca','0d27de7eb5fd078e734a027283db52f8']
            pairs = zip(relsHash, relsHash_ref)
            assert any(x != y for x, y in pairs) == False

            price_validation = graphDB.getLatestExchangePrices(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),now=5
                )
            assert price_validation[0]['meanPriceNet'] == 3*(1-0.002)
            assert price_validation[0]['meanPrice'] == 3
            assert price_validation[0]['limitPrice'] == 3