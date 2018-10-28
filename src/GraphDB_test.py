import pytest
import sys
from GraphDB import GraphDB, AssetState
from OrderBook import OrderBook, Asset
import time
import pprint
import time

class TestClass(object):

    def test_setAssetState(self):
        graphDB = GraphDB(resetDBData=True)
        volumeBTCs=[1]
        graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),volumeBTCs=volumeBTCs,now=time.time())

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
        volumeBTCs=[1]
        nodeid =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),volumeBTCs=volumeBTCs,now=time.time())

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
        volumeBTCs = [1]
        nodeid1 =  graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),volumeBTCs=volumeBTCs,now=time.time())
        nodeid2 =  graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'),volumeBTCs=volumeBTCs,now=time.time())

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
    
    def test_arbitrage_test_with_three_nodes_intraexchange_deal(self):
        volumeBTCs = [0.1,1]
        graphDB = GraphDB(resetDBData=True)
        graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),volumeBTCs=volumeBTCs,now=0)
        graphDB.createAssetNode(Asset(exchange='Kraken', symbol='BTC'),volumeBTCs=volumeBTCs,now=0.1)
        graphDB.createAssetNode(Asset(exchange='Kraken', symbol='ETH'),volumeBTCs=volumeBTCs,now=0.2)

        graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='BTC/ETH',orderbook=[[2,1]],rateBTCxBase=1,rateBTCxQuote=2,feeRate=0,timeToLiveSec=5,timestamp=0.3),volumeBTCs=volumeBTCs)

        graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='ETH/BTC',orderbook='[[0.6,1000]]',rateBTCxBase=1/0.6,rateBTCxQuote=1,feeRate=0,timeToLiveSec=5,timestamp=0.4),volumeBTCs=volumeBTCs)

        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=0.5,volumeBTCs=volumeBTCs )
        assert len(arbitrage_cycles) == 2   
        for i in range(2):
            assert arbitrage_cycles[i].getVolumeBTC() == volumeBTCs[i]
            assert (arbitrage_cycles[i].nodesList[0].exchange,arbitrage_cycles[i].nodesList[0].symbol) == ('Kraken','BTC')
            assert (arbitrage_cycles[i].nodesList[1].exchange,arbitrage_cycles[i].nodesList[1].symbol) == ('Kraken','ETH')
            assert (arbitrage_cycles[i].nodesList[2].exchange,arbitrage_cycles[i].nodesList[2].symbol) == ('Kraken','BTC')
            assert arbitrage_cycles[i].getProfit() == pytest.approx((2.0*0.6)*100-100)
            assert arbitrage_cycles[i].orderBookPriceList[0].meanPrice == 2.0
            assert arbitrage_cycles[i].orderBookPriceList[1].meanPrice== 0.6        

        # TODO: need to validate these too
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=1.1,now=1.5,volumeBTCs=volumeBTCs)
        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=0.5,now=2.1,volumeBTCs=volumeBTCs)
        

    def test_arbitrage_test_with_four_nodes_extraexchange_deal(self):
        volumeBTCs = [0.1,1]
        graphDB = GraphDB(resetDBData=True)

        graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='BTC/ETH',orderbook=[[1/0.06,1]],rateBTCxBase=1,rateBTCxQuote=1/0.06,feeRate=0,timeToLiveSec=5,timestamp=0.3),volumeBTCs=volumeBTCs)
        graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='ETH/BTC',orderbook=[[0.05,1/0.06]],rateBTCxBase=1/0.06,rateBTCxQuote=1,feeRate=0,timeToLiveSec=5,timestamp=0.3),volumeBTCs=volumeBTCs)

        graphDB.addTradingRelationship(OrderBook(exchange='Binance',symbol='BTC/ETH',orderbook=[[1/0.04,1]],rateBTCxBase=1,rateBTCxQuote=1/0.06,feeRate=0,timeToLiveSec=5,timestamp=0.3),volumeBTCs=volumeBTCs)
        graphDB.addTradingRelationship(OrderBook(exchange='Binance',symbol='ETH/BTC',orderbook=[[0.03,1/0.06]],rateBTCxBase=1/0.06,rateBTCxQuote=1,feeRate=0,timeToLiveSec=5,timestamp=0.3),volumeBTCs=volumeBTCs)

        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=5,now=0.5,volumeBTCs=volumeBTCs )
        assert len(arbitrage_cycles) == 2   
        for i in range(2):
            assert arbitrage_cycles[i].getVolumeBTC() == volumeBTCs[i]
            assert (arbitrage_cycles[i].nodesList[0].exchange,arbitrage_cycles[i].nodesList[0].symbol) == ('Kraken','BTC')
            assert (arbitrage_cycles[i].nodesList[1].exchange,arbitrage_cycles[i].nodesList[1].symbol) == ('Binance','BTC')
            assert (arbitrage_cycles[i].nodesList[2].exchange,arbitrage_cycles[i].nodesList[2].symbol) == ('Binance','ETH')
            assert (arbitrage_cycles[i].nodesList[3].exchange,arbitrage_cycles[i].nodesList[3].symbol) == ('Kraken','ETH')
            assert arbitrage_cycles[i].getProfit() == pytest.approx(((1/0.04*0.05)-1)*100)

            assert arbitrage_cycles[i].orderBookPriceList[0].meanPrice == 1
            assert arbitrage_cycles[i].orderBookPriceList[1].meanPrice == 1/0.04
            assert arbitrage_cycles[i].orderBookPriceList[2].meanPrice ==  1
            assert arbitrage_cycles[i].orderBookPriceList[3].meanPrice ==  0.05
            assert arbitrage_cycles[i].orderBookPriceList[0].meanPriceNet  == 1
            assert arbitrage_cycles[i].orderBookPriceList[1].meanPriceNet == 1/0.04
            assert arbitrage_cycles[i].orderBookPriceList[2].meanPriceNet == 1
            assert arbitrage_cycles[i].orderBookPriceList[3].meanPriceNet == 0.05


        arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=1.3,now=1.5,volumeBTCs=volumeBTCs)
        #arbitrage_cycles = graphDB.getArbitrageCycle(Asset(exchange='Kraken', symbol='BTC'),match_lookback_sec=0.5,now=2.1,volumeBTCs=volumeBTCs)

    def test_arbitrage_test_with_three_nodes_relationship_updates(self):
        with GraphDB(resetDBData=True) as graphDB:        
            volumeBTCs=[1]
            graphDB.createAssetNode(Asset(exchange='Bitfinex', symbol='BTC'),volumeBTCs=volumeBTCs,now=0)

            ###################################################################
            # Update trade relationship multiple (3x) times to verify that
            # relationships are properly end-dated and new relationships are created
            graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='BTC/ETH',orderbook='[[1,1]]',rateBTCxBase=1,rateBTCxQuote=1,feeRate=0.002,timeToLiveSec=4,timestamp=1),volumeBTCs=[1])

            graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='BTC/ETH',orderbook='[[2,1]]',rateBTCxBase=1,rateBTCxQuote=2,feeRate=0.002,timeToLiveSec=2,timestamp=2),volumeBTCs=[1])

            graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='BTC/ETH',orderbook='[[3,1]]',rateBTCxBase=1,rateBTCxQuote=3,feeRate=0.002,timeToLiveSec=5,timestamp=3),volumeBTCs=[1])

            graphDB.addTradingRelationship(OrderBook(exchange='Kraken',symbol='ETH/BTC',orderbook='[[4,1]]',rateBTCxBase=1/4,rateBTCxQuote=1,feeRate=0.002,timeToLiveSec=3,timestamp=3),volumeBTCs=[1])

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
            nodesHash_ref = ['ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','ecf0ab3d17c759110327cd433f1dbb68','9887c14ada99b8c72b7996a460afda1e','905ed9c758ce981d7ea0fb1bef55873c','89586e3b288ac93f329280eb9f025d18','7b54e3841e6574caaf429917c88e2bac','17032c1a5da060b45d736930551267b7','0f67e27fbf10b058924b76dce3774945']
            pairs = zip(nodesHash, nodesHash_ref)
            assert any(x != y for x, y in pairs) == False

            ###################################################################
            # validate the properties of all relationships by hash
            #
            relsHash = graphDB.getRelsPropertyHash()

            relsHash_ref=['ed7127753c7561aff65aa934c3ec0b08','d794f53471f01df442d053f452abdef4','d10dd681cd3c15d953fd5ddf4e35730e','b7ce49bb20b4d32d31a1861e48b7c6c2','ab575c242a6e2111badc21dee2409fc3','940bfc678e9a565c173713a3fec69c4c','940bfc678e9a565c173713a3fec69c4c','9062679b13a5bf1e9a3896aae1a3fe48','8ebdbdd4fbd496a13f02113c97bad76c','83f93e9d610ffbfbe4430be7b235bbaf','7a519a3f90b4f903841bca9690f6c189','3ab3d46ae90b2899ca7e48b8d454e6e8','1130f54c147f2e6b8f0fab0620c150ca','0d27de7eb5fd078e734a027283db52f8','09a0a8da97644340bce29000b638cad8','043b1a0eca390ff435a8bf56976f1d45']

            pairs = zip(relsHash, relsHash_ref)
            assert any(x != y for x, y in pairs) == False

            price_validation = graphDB.getLatestExchangePrices(
                baseAsset=Asset(exchange='Kraken', symbol='BTC'),
                quotationAsset=Asset(exchange='Kraken', symbol='ETH'),now=5
                )
            assert price_validation[0]['meanPriceNet'] == 3*(1-0.002)
            assert price_validation[0]['meanPrice'] == 3
            assert price_validation[0]['limitPrice'] == 3