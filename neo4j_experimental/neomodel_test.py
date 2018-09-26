from neomodel import (config, StructuredNode, StringProperty, IntegerProperty,
    UniqueIdProperty, RelationshipTo, RelationshipFrom, StructuredRel,DateTimeProperty,FloatProperty)
from datetime import datetime
import pytz

config.DATABASE_URL = 'bolt://neo4j:neo@localhost:7687'

class quotationRel(StructuredRel):
    created = DateTimeProperty(default_now=True)
    rate = FloatProperty()

class CryptoCurrency(StructuredNode):
    name = StringProperty(required=True,unique_index=True)
    symbol = StringProperty(required=True,unique_index=False)
    exchange = StringProperty(required=True,unique_index=False)

    # traverse outgoing IS_FROM relations, inflate to Country objects
    quotation = RelationshipTo('CryptoCurrency', 'EXCHANGE',model=quotationRel)
    __label__ = 'CryptoCurrency'

CryptoCurrency(name='Kraken-BTC',symbol='BTC',exchange='Kraken').save()
CryptoCurrency(name='Poloniex-BTC',symbol='BTC',exchange='Poloniex').save()
CryptoCurrency(name='Kraken-ETH',symbol='ETH',exchange='Kraken').save()

#rel  = BTC.quotation.connect(ETH,{'rate':1})
#rel  = BTC.quotation.connect(ETH,{'rate':2})

#a = CryptoCurrency.nodes.get(name="BTC",exchange="Kraken")
try:
    currencyBase = CryptoCurrency.nodes.get(name='Kraken-BTC')
    currencyQuotation = CryptoCurrency.nodes.get(name='Kraken-ETH')
except CryptoCurrency.DoesNotExist:
    print("Couldn't find node")

currencyBase.quotation.connect(currencyQuotation,{'rate':1})

#print(rel.created)
#jim.delete()
#jim.refresh() # reload properties from neo
#jim.id # neo4j internal id