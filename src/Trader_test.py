import pytest  
from Trader import Trader
from Trade import Trade

@pytest.fixture(scope="class")
def getOrderbookAnalyser():
    pass


class TestClass(object):

    def test_one(self):
        with Trader(exchangeNames=["kraken"],credfile='./cred/api_balance.json',isSandboxMode=True) as trader:
            tradelist = [
                Trade("kraken","BTC/USD",0.1,20000,Trade.SELL_ORDER),
            ]
            assert trader.isSandboxMode == True
            assert ('kraken' in trader.balance) == False
            trader.executeTrades(tradelist)
            assert ('kraken' in trader.balance) == True
            print("done")

if __name__ == "__main__":
    tc=TestClass()
    tc.test_one()