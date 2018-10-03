import pytest
from FeeStore import FeeStore


@pytest.fixture(scope="class")
def getFeeStore():
    return FeeStore()


class TestClass(object):
    def test_ploniex(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('poloniex', 'BTC/USDT') == 0.002
        assert feeStore.getMakerFee('poloniex', 'BTC/USDT') == 0.001

    def test_kraken(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('kraken', 'BTC/EUR') == 0.0026
        assert feeStore.getMakerFee('kraken', 'BTC/EUR') == 0.0016

    def test_noNameExchange(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('nonameexchange',
                                    'BTC/EUR') == FeeStore.DEFAULT_TAKER_FEE
        assert feeStore.getMakerFee('nonameexchange',
                                    'BTC/EUR') == FeeStore.DEFAULT_MAKER_FEE

    def test_bitStamp(self):
        feeStore = getFeeStore()
        assert feeStore.getTakerFee('bitstamp', 'BTC/EUR') == 0.0025
        assert feeStore.getMakerFee('bitstamp', 'BTC/EUR') == 0.0025

    def test_coinfloor(self):
        feeStore = getFeeStore()
        print(feeStore.getTakerFee('Coinfloor', 'BTC/EUR'))
        #assert feeStore.getTakerFee('coinfloor','BTC/EUR') == 0.0025
        #assert feeStore.getMakerFee('coinfloor','BTC/EUR') == 0.0025


if __name__ == "__main__":
    tc = TestClass()
    tc.test_coinfloor()
