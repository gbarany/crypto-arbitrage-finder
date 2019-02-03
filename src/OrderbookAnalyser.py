from ArbitrageGraph import ArbitrageGraph
from ArbitrageGraphNeo import ArbitrageGraphNeo
from FeeStore import FeeStore
from OrderBook import OrderBook, OrderBookPair, Asset
from PriceStore import PriceStore
import datetime
import logging
from FWLiveParams import FWLiveParams
import asyncio
from utilities import timed
from TradingStrategy import TradingStrategy
from aiokafka import AIOKafkaProducer
import json
from multiprocessing import Process, Pipe, Queue
import numbers

logger = logging.getLogger('CryptoArbitrageApp')

class KafkaProducerWrapper:
    def __init__(self,kafkaCredentials):
        loop = asyncio.get_event_loop()
        self.kafkaProducer = None
        
        if kafkaCredentials is not None:
            self.topic = kafkaCredentials["topicDeals"]
            try:
                self.kafkaProducer = AIOKafkaProducer(
                    loop=loop,
                    bootstrap_servers=kafkaCredentials["uri"],
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'))
                asyncio.ensure_future(self.kafkaProducer.start())
            except Exception as e:
                logger.error('Kafka producer initialization failed')
                
        else:
            logger.info('No credentials available for Kafka producer')

    def sendDeal(self,deal):
        if self.kafkaProducer is not None:
            asyncio.ensure_future(self.sendAsync(deal))

    async def sendAsync(self,deal):
        payload = deal.getLogJSONDump()
        try:
            await self.kafkaProducer.send_and_wait(self.topic, payload)
        except Exception as e:
            logger.warning('Failed to publish to Kafka stream ')
    
    def __del__(self):
        if self.kafkaProducer is not None:
            asyncio.ensure_future(self.kafkaProducer.stop())


class OrderbookAnalyser:
    PRICE_SOURCE_ORDERBOOK = "PRICE_SOURCE_ORDERBOOK"
    PRICE_SOURCE_CMC = "PRICE_SOURCE_CMC"

    def __init__(self,
                 vol_BTC=[1],
                 edgeTTL=5,
                 priceTTL=60,
                 resultsdir='./',
                 priceSource=PRICE_SOURCE_ORDERBOOK,
                 trader=None,
                 neo4j_mode=FWLiveParams.neo4j_mode_disabled,
                 dealfinder_mode=FWLiveParams.dealfinder_mode_networkx,
                 kafkaCredentials=None):

        # create Arbitrage Graph objects
        if dealfinder_mode & FWLiveParams.dealfinder_mode_networkx:
            self.arbitrageGraphs = [ArbitrageGraph() for count in range(len(vol_BTC))]
            self.pipes = [Pipe() for count in range(len(vol_BTC))]
            self.dealQueue = Queue()
            self.processes = [Process(target=self.updatePointProcess, args=(self.arbitrageGraphs[i], vol_BTC[i], self.pipes[i], self.dealQueue)) for i in range(len(vol_BTC))]
            self.dealProcessor = Process(target=self.dealProcess)
            self.dealProcessor.daemon = True
        else:
            self.arbitrageGraphs = None

        if dealfinder_mode & FWLiveParams.dealfinder_mode_neo4j:
            self.arbitrageGraphNeo = ArbitrageGraphNeo(neo4j_mode=neo4j_mode,volumeBTCs=vol_BTC)
        else:
            self.arbitrageGraphNeo = None

        self.edgeTTL=edgeTTL
        self.feeStore = FeeStore()
        self.priceStore = PriceStore(priceTTL=priceTTL)
        self.vol_BTC = vol_BTC
        self.resultsdir = resultsdir
        self.timestamp_start = datetime.datetime.now()
        self.cmcTicker = None
        self.neo4j_mode = neo4j_mode
        self.priceSource = priceSource
        self.dealfinder_mode = dealfinder_mode
        self.isRunning = True
        assert trader is not None
        self.trader = trader
        
        self.kafkaProducer = KafkaProducerWrapper(kafkaCredentials)

        self.dealProcessor.start()
        # kick-of processes
        for process in self.processes:
            process.daemon = True
            process.start()

    def updateCoinmarketcapPrice(self, cmcTicker):
        self.cmcTicker = cmcTicker

    def updateForexPrice(self, forexTicker):
        self.priceStore.updatePriceFromForex(forexTicker)

    def dealProcess(self):
        while True:
            path = self.dealQueue.get()  # Read from the queue
            logger.info("NetX Found arbitrage deal: " + str(path))
            path.log()
            self.kafkaProducer.sendDeal(path)

            if TradingStrategy.isDealApproved(path) is True:
                sorl = path.toSegmentedOrderList()
                asyncio.ensure_future(self.trader.execute(sorl))
                logger.info("Called Trader ensure_future")

    @staticmethod
    def updatePointProcess(arbitrageGraph, volumeBTC, pipe, dealQueue):
        p_output, p_input = pipe
        while True:
            orderBookPair, timestamp = p_output.recv()    # Read from the output pipe
            arbitrageGraph.updatePoint(orderBookPair=orderBookPair, volumeBTC=volumeBTC)
            path = arbitrageGraph.getArbitrageDeal(timestamp)
            if path.isProfitable() is True:
                dealQueue.put(path)


    @timed
    def update(self, exchangename, symbol, bids, asks, timestamp):
        # Validate inputs and reject if invalid
        if isinstance(exchangename, str) is False:
            raise Exception("Exchange name is not a string: " + str(exchangename)+" "+str(symbol))
        if (isinstance(symbol, str) is False) or (symbol.find("/") == -1):
            raise Exception("Invalid symbol:"+symbol + " "+str(exchangename))
        if (not bids) or any(not isinstance(entry, list) for entry in bids) or any(not isinstance(entry[0], numbers.Number) or not isinstance(entry[1], numbers.Number) for entry in bids):
            raise Exception("Invalid bids format on " + str(exchangename)+" "+str(symbol)+", bids:"+str(bids))

        if self.priceSource == OrderbookAnalyser.PRICE_SOURCE_ORDERBOOK:
            self.priceStore.updatePriceFromOrderBook(
                symbol=symbol,
                exchangename=exchangename,
                asks=asks,
                bids=bids,
                timestamp=timestamp)
        elif self.priceSource == OrderbookAnalyser.PRICE_SOURCE_CMC:
            if self.cmcTicker is not None:
                self.priceStore.updatePriceFromCoinmarketcap(ticker=self.cmcTicker)
            else:
                # logger.info('No CMC ticker received yet, reverting to orderbook pricing')
                # self.priceStore.updatePriceFromOrderBook(symbol=symbol,exchangename=exchangename,asks=asks,bids=bids,timestamp=timestamp)
                logger.info('No CMC ticker received yet, skipping update')
                return

        rateBTCxBase = self.priceStore.getMeanPrice(
            symbol_base_ref='BTC',
            symbol_quote_ref=symbol.split('/')[0],
            timestamp=timestamp)

        rateBTCxQuote = self.priceStore.getMeanPrice(
            symbol_base_ref='BTC',
            symbol_quote_ref=symbol.split('/')[1],
            timestamp=timestamp)

        # Price store doesn't have an exchange rate for this trading pair
        # therefore trading graph won't be updated
        if rateBTCxBase is None or rateBTCxQuote is None :
            return

        orderBookPair = OrderBookPair(
            timestamp=timestamp,
            symbol=symbol,
            exchange=exchangename,
            asks=asks,
            bids=bids,
            rateBTCxBase=rateBTCxBase,
            rateBTCxQuote=rateBTCxQuote,
            feeRate=self.feeStore.getTakerFee(exchangename, symbol),
            timeToLiveSec=self.edgeTTL)


        
        # ArbitrageGraphNeo deal finder (Neo4j)
        # TODO: add neo4j processing back on
        '''if self.dealfinder_mode & FWLiveParams.dealfinder_mode_neo4j:
            
            self.arbitrageGraphNeo.updatePoint(orderBookPair=orderBookPair)
            paths_neo=self.arbitrageGraphNeo.getArbitrageDeal(
                timestamp=timestamp,
                asset=Asset(exchange=orderBookPair.exchange, symbol=orderBookPair.getSymbolBase()))
            

            for path_neo in paths_neo:
                if path_neo.isProfitable() is True:
                    logger.info("Neo4j Found arbitrage deal: "+str(path_neo))
                    path_neo.log()
                    self.kafkaProducer.sendDeal(path_neo)
                    if TradingStrategy.isDealApproved(path_neo) is True:
                        sorl = path_neo.toSegmentedOrderList()
                        asyncio.ensure_future(self.trader.execute(sorl))
                        logger.info("Called Trader ensure_future")
        '''
        # ArbitrageGraph deal finder (NetworkX)
        if self.dealfinder_mode & FWLiveParams.dealfinder_mode_networkx:
            for idx, pipe in enumerate(self.pipes):
                pipe[1].send((orderBookPair, timestamp))
                '''arbitrageGraph.updatePoint(orderBookPair=orderBookPair,volumeBTC = self.vol_BTC[idx])
                path = arbitrageGraph.getArbitrageDeal(timestamp)
                if path.isProfitable() is True:
                    logger.info("NetX Found arbitrage deal: "+str(path))
                    path.log()
                    self.kafkaProducer.sendDeal(path)
                    
                    if TradingStrategy.isDealApproved(path) is True:
                        sorl = path.toSegmentedOrderList()
                        asyncio.ensure_future(self.trader.execute(sorl))
                        logger.info("Called Trader ensure_future")'''

    def terminate(self):
        self.isRunning = False
        # terminate running processes
        self.dealProcessor.terminate()
        for process in self.processes:
            process.terminate()

    def plotGraphs(self):
        for idx, arbitrageGraph in enumerate(self.arbitrageGraphs):
            arbitrageGraph.plotGraph(
                figid=(idx + 1), vol_BTC=self.vol_BTC[idx])
