import pytest
from Notifications import sendNotification

class TestClass(object):
    def test_sendNotification(self):
        sendNotification("Test message")