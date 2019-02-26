import uuid


class DealHistoryDictItem:
    def __init__(self, timestamp, nodesStr, profitPerc):
        self.timestamp = timestamp
        self.nodesStr = nodesStr
        self.profitPerc = profitPerc
        self.uuid = uuid.uuid4()

    def getUUIDString(self):
        return str(self.uuid)


class DealUUIDGenerator:
    def __init__(self, deltaTimeLimitSec=5):
        self.dealHistoryDict = dict()
        self.deltaTimeLimitSec = deltaTimeLimitSec

    def purgeExpiredDictItems(self, timestamp):
        keysToDelete = []
        # purge expired data from history
        for key, value in self.dealHistoryDict.items():
            if (timestamp - value.timestamp) > self.deltaTimeLimitSec:
                keysToDelete.append(key)

        for key in keysToDelete:
            self.dealHistoryDict.pop(key)

    def getUUID(self, timestamp, volBTC, nodesStr, profitPerc):

        key = (nodesStr, volBTC)

        self.purgeExpiredDictItems(timestamp)

        # is this deal known from before?
        if key in self.dealHistoryDict:
            self.dealHistoryDict[key].timestamp = timestamp
            self.dealHistoryDict[key].profitPerc = profitPerc
            return self.dealHistoryDict[key].getUUIDString()
        else:
            newDealItem = DealHistoryDictItem(timestamp=timestamp, nodesStr=nodesStr, profitPerc=profitPerc)
            self.dealHistoryDict[key] = newDealItem
            return newDealItem.getUUIDString()
