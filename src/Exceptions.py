class TradesShowstopper(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class OrderCreationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)

class OrderCancellationError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)
