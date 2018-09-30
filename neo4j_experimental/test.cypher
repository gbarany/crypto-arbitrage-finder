//MATCH (n) DETACH DELETE n
CREATE  
    (KrakenBTC:CryptoCurrency:Kraken {name:'BTC',exchange:'Kraken'}),
    (KrakenETH:CryptoCurrency:Kraken {name:'ETH',exchange:'Kraken'}),
    (KrakenXRP:CryptoCurrency:Kraken {name:'XRP',exchange:'Kraken'}),
    (KrakenLTC:CryptoCurrency:Kraken {name:'LTC',exchange:'Kraken'}),
    (KrakenBCH:CryptoCurrency:Kraken {name:'BCH',exchange:'Kraken'}),
    (PoloniexBTC:CryptoCurrency:Poloniex {name:'BTC',exchange:'Poloniex'}),
    (PoloniexETH:CryptoCurrency:Poloniex {name:'ETH',exchange:'Poloniex'}),
    (PoloniexXRP:CryptoCurrency:Poloniex {name:'XRP',exchange:'Poloniex'}),
    (PoloniexLTC:CryptoCurrency:Poloniex {name:'LTC',exchange:'Poloniex'}),
    (PoloniexBCH:CryptoCurrency:Poloniex {name:'BCH',exchange:'Poloniex'})

CREATE
    (KrakenBTC)-[:EXCHANGE {rate:0.639}]->(KrakenETH),
	(KrakenBTC)-[:EXCHANGE {rate:5.3712}]->(KrakenXRP),
	(KrakenBTC)-[:EXCHANGE {rate:1.5712}]->(KrakenLTC),
	(KrakenBTC)-[:EXCHANGE {rate:98.8901}]->(KrakenBCH),

    (KrakenBTC)-[:EXCHANGE {rate:1}]->(PoloniexBTC),

	(KrakenETH)-[:EXCHANGE {rate:1.5648}]->(KrakenBTC),
	(KrakenETH)-[:EXCHANGE {rate:8.4304}]->(KrakenXRP),
	(KrakenETH)-[:EXCHANGE {rate:2.459}]->(KrakenLTC),
	(KrakenETH)-[:EXCHANGE {rate:154.7733}]->(KrakenBCH),
    (KrakenETH)-[:EXCHANGE {rate:1}]->(PoloniexETH),


	(KrakenXRP)-[:EXCHANGE {rate:0.1856}]->(KrakenBTC),
	(KrakenXRP)-[:EXCHANGE {rate:0.1186}]->(KrakenETH),
	(KrakenXRP)-[:EXCHANGE {rate:0.2921}]->(KrakenLTC),
	(KrakenXRP)-[:EXCHANGE {rate:18.4122}]->(KrakenBCH),
    (KrakenXRP)-[:EXCHANGE {rate:1}]->(PoloniexXRP),

	(KrakenLTC)-[:EXCHANGE {rate:0.6361}]->(KrakenBTC),
	(KrakenLTC)-[:EXCHANGE {rate:0.4063}]->(KrakenETH),
	(KrakenLTC)-[:EXCHANGE {rate:3.4233}]->(KrakenXRP),
	(KrakenLTC)-[:EXCHANGE {rate:62.94}]->(KrakenBCH),
    (KrakenLTC)-[:EXCHANGE {rate:1}]->(PoloniexLTC),

	(KrakenBCH)-[:EXCHANGE {rate:0.01011}]->(KrakenBTC),
	(KrakenBCH)-[:EXCHANGE {rate:0.00645}]->(KrakenETH),
	(KrakenBCH)-[:EXCHANGE {rate:0.05431}]->(KrakenXRP),
	(KrakenBCH)-[:EXCHANGE {rate:0.01588}]->(KrakenLTC),
    (KrakenBCH)-[:EXCHANGE {rate:1}]->(PoloniexBCH)

WITH KrakenBTC as s
MATCH (s)-[:EXCHANGE]->()-[:EXCHANGE]->(d) RETURN s,d,labels(s) LIMIT 50;


WITH 1000000 AS startVal
MATCH x = (c:CryptoCurrency)-[r:EXCHANGE*..4]->(c)
WHERE c.name = "BTC" AND  c:Kraken
WITH x, REDUCE(s = startVal, e IN r | s * e.rate) AS endVal, startVal
WHERE endVal > startVal
RETURN EXTRACT(n IN NODES(x) | labels(n)[0]+n.name) AS Exchanges, endVal - startVal AS Profit
ORDER BY Profit DESC
LIMIT 5


//
CALL algo.allShortestPaths.stream('rate',{nodeQuery:'CryptoCurrency',defaultValue:1.0})
YIELD sourceNodeId, targetNodeId, distance
WITH sourceNodeId, targetNodeId, distance
WHERE algo.isFinite(distance) = true

MATCH (source:CryptoCurrency) WHERE id(source) = sourceNodeId
MATCH (target:CryptoCurrency) WHERE id(target) = targetNodeId
WITH source, target, distance //WHERE source = target

RETURN source.name AS source, target.name AS target, distance
ORDER BY distance DESC
LIMIT 10

////////


MATCH p=(a)-[rels:EXCHANGE]->(b)
WITH collect(rels.created) as createdList
FOREACH (r IN relationships(p)| SET r.created = max(createdList) )

MATCH (startNode(r):CryptoCurrency)-[subrel:EXCHANGE]->(endNode(r):CryptoCurrency)
//WHERE ($now-r.created)<=r.timeToLiveSec
RETURN subrel.rate
ORDER BY subrel.created DESC
LIMIT 1


MATCH (a:CryptoCurrency:Kraken)-[subrel:EXCHANGE]->(CryptoCurrency:Kraken:CryptoCurrency)
WITH subrel, max(collect(subrel.created)) AS mostrecent
WHERE subrel.created = mostrecent
RETURN mostrecent

///

MATCH (base:CryptoCurrency)-[r:EXCHANGE]->(quotation:CryptoCurrency)
WHERE base.exchange = "Kraken" AND base.symbol = "BTC" AND quotation.exchange = "Kraken" AND quotation.symbol = "ETH" AND r.
SET r.to = 1

MATCH (base:CryptoCurrency),(quotation:CryptoCurrency)
WHERE base.exchange = "Kraken" AND base.symbol = "BTC" AND quotation.exchange = "Kraken" AND quotation.symbol = "ETH"
CREATE(base)-[:EXCHANGE {rate:1,from:0,to:1}]->(quotation)

///

MATCH path = (x)-[:EXCHANGE*]-(y)
  UNWIND NODES(path) AS n
    WITH path, 
         SIZE(COLLECT(DISTINCT n)) AS testLength 
    WHERE testLength = LENGTH(path) + 1
RETURN path

///
MATCH x = (c)-[EXCHANGE*2..4]->(c)
UNWIND NODES(x) AS xx
WITH SIZE(COLLECT(DISTINCT xx)) AS testLength
UNWIND testLength as t
RETURN t

WHERE testLength = LENGTH(x) AND c.symbol = $symbol AND  c.exchange = $exchange AND NONE (a in r WHERE a.to<$now) 


//



MATCH path = (c:CryptoCurrency)-[r:EXCHANGE*1..4]->(c)
UNWIND NODES(path) AS n
WITH path, SIZE(COLLECT(DISTINCT n)) AS testLength, c, r
WHERE testLength = LENGTH(path)
RETURN path, nodes(path)[0], relationships(path)


//

MATCH (n:Asset)-[s:STATE]-(h:AssetState)
WHERE s.to>=timestamp()/1000
MATCH (n:Asset)-[r:EXCHANGE]-(k:Asset)
WHERE r.to>=timestamp()/1000
RETURN n,r,k,s,h


MATCH (n:Asset)-[s:STATE]-(h:AssetState)
WHERE s.to>1538264086.152025
MATCH (n:Asset)-[r:EXCHANGE]-(k:Asset)
WHERE r.to>1538264086.152025
RETURN n,r,k,s,h
