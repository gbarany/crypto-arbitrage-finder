# Crypto Arbitrage Finder

Stabilizing extreme price gaps accross cryptocurrency exchanges is benefital for the ecosystem. 
Crypto Arbitrage Finder is able to identify arbitrage opportunities and execute arbitrage transactions. 

High level architecture: 
https://bit.ly/2CLrzK7

FrameworkLive orchestrates the components and threads of the live arbitrage trading system.

## Components of the live trading framework
- Exchange pollers: run in parallel, fetch orderbook data from predefined exchanges and sends data to the Orderbook Analyser
- Coinmarketcap pollers: fetch cyrpto exchange-wide market price dataand and sends data to the Orderbook Analyser
- Forex poller: fetches current Forex ask and bid prices (from Oanda) and sends the data to the Orderbook Analyser
- Orderbook analyser: 
  - ArbitrageGraph : runs multiple instances in parallel, with a different throughput volume nominated in Bitcoin
  - PriceStore : maintaining the latest known market price for every asset
  - FeeStore : contains current fee ratios for all active exchanges
- Trader : trade execution and error handling
- Logging : global logging (errors, warnings, info)


## Folder structure
- `src` : source code and unit tests (*_test.py)
- `cred` : contains exchange credentials
- `results` : output folder where the system saves the trade log and error log 
- `tools` : scripts to analyse the result files

## Docker
- `docker-build.sh` : builds the appication docker container
- `docker-run-live.sh` : starts the docker container

## Credentials
- `api_balance.json` : api keys with balance query credentials only
- `api_trading.json` : api keys with trading credentials
- `oanda.json` : oanda api keys

### Example
```javascript
{
    "gdax": {
        "apiKey": "",
        "secret": "",
        "password": "",
        "enableRateLimit": true
    },

    "kraken": {
        "apiKey": "",
        "secret": "",
        "enableRateLimit": true
    },
    "bitstamp": {
        "apiKey": "",
        "secret": "",
        "uid": "",
        "timeout": 5000,
        "enableRateLimit": true
    }
}
```

## Testing

Unit tests are implemented in pytest with test py-cov extension for test coverage measurement. Run `runtests.sh` to get coverage metrics.

A local Neo4j instance is required for some of the unit tests:
```
docker run \
    --publish=7474:7474 --publish=7687:7687 \
    --volume=$HOME/neo4j/data:/data \
    --volume=$HOME/neo4j/plugins:/plugins \
    --volume=$HOME/neo4j/logs:/logs \
    --env=NEO4J_dbms_security_procedures_unrestricted=algo.*,apoc.trigger.*,apoc.meta.*,apoc.\\\* \
    neo4j:3.4.9
```

Copy the following Neo4j plugin to the `$HOME/neo4j/plugins` folder:
* https://github.com/neo4j-contrib/neo4j-graph-algorithms/releases/download/3.4.7.0/graph-algorithms-algo-3.4.7.0.jar
* https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/3.4.0.3/apoc-3.4.0.3-all.jar
