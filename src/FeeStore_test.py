import pytest  
from FeeStore import FeeStore

@pytest.fixture(scope="class")
def getFeeStore():
    return FeeStore()

class TestClass(object):

    def test_one(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('poloniex','BTC/USDT') == 0.002
        assert feeStore.getMakerFee('poloniex','BTC/USDT') == 0.001

    def test_two(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('kraken','BTC/EUR') == 0.0026
        assert feeStore.getMakerFee('kraken','BTC/EUR') == 0.0016

    def test_three(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('nonameexchange','BTC/EUR') == FeeStore.DEFAULT_TAKER_FEE
        assert feeStore.getMakerFee('nonameexchange','BTC/EUR') == FeeStore.DEFAULT_MAKER_FEE

