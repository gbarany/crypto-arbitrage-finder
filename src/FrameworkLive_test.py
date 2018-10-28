import pytest
from FrameworkLive import main
import time
import asyncio
from threading import Thread

@pytest.fixture(scope="class")
def getFrameworkLive():
    pass


class TestClass(object):
    def test_testone(self):
        def stop_loop():
            time.sleep(10)
            loop.call_soon_threadsafe(loop.stop)

        loop = asyncio.get_event_loop()
        Thread(target=stop_loop).start()

        main(argv=[])
