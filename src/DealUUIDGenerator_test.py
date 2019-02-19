import pytest
from DealUUIDGenerator import DealUUIDGenerator


class TestClass(object):

    def test_singleExchangeConstantProfit(self):
        dealUUIDGenerator = DealUUIDGenerator()
        id1 = dealUUIDGenerator.getUUID(timestamp=1, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id2 = dealUUIDGenerator.getUUID(timestamp=2, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id3 = dealUUIDGenerator.getUUID(timestamp=7, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id4 = dealUUIDGenerator.getUUID(timestamp=12.1, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id5 = dealUUIDGenerator.getUUID(timestamp=12.2, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id6 = dealUUIDGenerator.getUUID(timestamp=12.3, nodesStr="bitstamp,coinbasepro", profitPerc=0.51)
        assert id1 == id2 == id3 != id4 == id5 != id6
        assert id5[:-2] == id6[:-2]

    def test_variedExchangesConstantProfit(self):
        dealUUIDGenerator = DealUUIDGenerator()
        id1 = dealUUIDGenerator.getUUID(timestamp=1, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id2 = dealUUIDGenerator.getUUID(timestamp=2, nodesStr="coinbasepro-BTC,coinbasepro-EUR,kraken-EUR,kraken-BTC,coinbasepro-BTC", profitPerc=0.5)
        id3 = dealUUIDGenerator.getUUID(timestamp=7, nodesStr="coinbasepro-BTC,coinbasepro-EUR,kraken-EUR,kraken-BTC,coinbasepro-BTC", profitPerc=0.5)
        id4 = dealUUIDGenerator.getUUID(timestamp=12.1, nodesStr="bitstamp,coinbasepro", profitPerc=0.5)
        id5 = dealUUIDGenerator.getUUID(timestamp=12.2, nodesStr="coinbasepro-BTC,coinbasepro-EUR,kraken-EUR,kraken-BTC,coinbasepro-BTC", profitPerc=0.51)
        assert id1 != id2 == id3 != id4 != id5
        assert id4[:-2] != id5[:-2]
