import pytest
from asynctest import TestCase, logging
from TraderHistory import TraderHistory

logging.getLogger('TraderHistory').setLevel(logging.DEBUG)
rootLogger = logging.getLogger()
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(funcName)s:%(lineno)s]')
ch.setFormatter(formatter)
# add the handlers to the logger
rootLogger.addHandler(ch)


class TestClass(TestCase):

    async def setUp(self):
        self.traderHistory = await TraderHistory.getInstance()

    async def TearDown(self):
        await self.traderHistory.close()

    @pytest.mark.skip(reason="ezt csak manuálisan futtassuk")
    @pytest.mark.asyncio
    async def test_poll_trades(self):
        await self.traderHistory.pollTrades()

