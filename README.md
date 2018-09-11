CryptoArbitrage - Stabilizing crypto price swings accross multiple exchanges,
whilst pocketing the arbitrage gains

High level architecture: 
https://bit.ly/2CLrzK7

FrameworkLive orchestrates the components and threads of the live arbitrage trading system.

Components of the live trading framework:
- Exchange pollers: run in parallel, fetch orderbook data from predefined exchanges and sends data to the Orderbook Analyser
- Coinmarketcap pollers: fetch cyrpto exchange-wide market price dataand and sends data to the Orderbook Analyser
- Forex poller: fetches current Forex ask and bid prices (from Oanda) and sends the data to the Orderbook Analyser
- Orderbook analyser: 
  - ArbitrageGraph : runs multiple instances in parallel, with a different throughput volume nominated in Bitcoin
  - PriceStore : maintaining the latest known market price for every asset
  - FeeStore : contains current fee ratios for all active exchanges
- Trader : trade execution and error handling
- Logging : global logging (errors, warnings, info)


Folder structure:
- src : source code and unit tests (*_test.py)
- cred : contains exchange credentials
- results : output folder where the system saves the trade log and error log 
- tools : scripts to analyse the result files

Docker:
docker-build.sh : builds the appication docker container
docker-run-live.sh : starts the docker container