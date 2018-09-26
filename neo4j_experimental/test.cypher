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