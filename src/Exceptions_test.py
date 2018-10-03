import pytest
from Exceptions import TradesShowstopper, OrderCreationError, OrderCancellationError


class TestClass(object):
    def test_TradesShowstopper(self):
        e = TradesShowstopper("test")
        assert str(e) == "test"

    def test_OrderCreationError(self):
        e = OrderCreationError("test")
        assert str(e) == "test"

    def test_OrderCancellationError(self):
        e = OrderCancellationError("test")
        assert str(e) == "test"
