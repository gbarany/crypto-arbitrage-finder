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


"""
    Exception for any exchange related error: If this error occurs the Trading must be aborted
"""
class OrderErrorByExchange(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)
