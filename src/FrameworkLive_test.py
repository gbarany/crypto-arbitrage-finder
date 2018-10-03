import pytest
from FrameworkLive import FrameworkLive


@pytest.fixture(scope="class")
def getFrameworkLive():
    pass


class TestClass(object):
    def test_testone(self):
        pass
