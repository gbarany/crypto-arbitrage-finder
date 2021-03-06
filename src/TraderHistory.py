import asyncio
import boto3
import json
from typing import Dict, Any
import ccxt.async_support as ccxt
from ccxt.async_support.base.exchange import Exchange
import time
import logging
# import MySQLdb
import os
from Database import Database

logger = logging.getLogger('TraderHistory')


class TraderHistory:
    NOF_CCTX_RETRY = 4


    SYMBOLS = ["BCH/BTC", "XRP/BTC", "LTC/BTC", "ETH/BTC", "BCH/ETH", "ETC/BTC", "ETC/ETH", "LSK/ETH", "LSK/BTC", "LTC/USDT", "BTC/EUR", "LTC/EUR", "BTC/USD", "ETH/USD", "ETH/EUR", "BCH/EUR", "BCH/USD"]

    def __init__(self):
        self.__exchanges: Dict[str, Exchange] = {}
        self.__db = Database.initDBFromAWSParameterStore()
        logger.info(f'TraderHistory.__init__()')

    @staticmethod
    async def getInstance():
        ''' :return:TraderHistory '''
        th = TraderHistory()
        await th.initExchangesFromAWSParameterStore()
        return th

    async def close(self):
        logger.info(f'TraderHistory.close()')
        self.__db.close()
        await self.__close_exchanges()

    async def initExchangesFromAWSParameterStore(self):
        logger.info(f'initExchangesFromAWSParameterStore')
        with open(os.path.dirname(os.path.realpath(__file__)) + '/../cred/aws-keys.json') as file:
            cred = json.load(file)
            ssm = boto3.client('ssm',
                               aws_access_key_id=cred['aws_access_key_id'],
                               aws_secret_access_key=cred['aws_secret_access_key'],
                               region_name=cred['region_name'])

            def getSSMParam(paramName):
                return ssm.get_parameter(Name=paramName, WithDecryption=True)['Parameter']['Value']

            enabledExchanges = getSSMParam('/prod/enabledExchanges').split(',')

            for exch in enabledExchanges:
                path = f'/prod/exchange/{exch}/'
                pars = ssm.get_parameters_by_path(
                    Path=path,
                    Recursive=True,
                    WithDecryption=True
                )
                exchangeCreds = {}
                for par in pars['Parameters']:
                    key = par['Name'].split('/')[-1]
                    value = par['Value']
                    exchangeCreds[key] = value
                await self.__init_exchange(exch, exchangeCreds)
        # await self.fetch_balances()

    # def __initDBFromAWSParameterStore(self):
    #     logger.info(f'__initDBFromAWSParameterStore')
    #     with open(os.path.dirname(os.path.realpath(__file__)) + '/../cred/aws-keys.json') as file:
    #         cred = json.load(file)
    #         ssm = boto3.client('ssm',
    #                            aws_access_key_id=cred['aws_access_key_id'],
    #                            aws_secret_access_key=cred['aws_secret_access_key'],
    #                            region_name=cred['region_name'])
    #
    #         def getSSMParam(paramName):
    #             return ssm.get_parameter(Name=paramName, WithDecryption=True)['Parameter']['Value']
    #
    #         self.__db = MySQLdb.connect(host=getSSMParam(TraderHistory.SSM_DB_PREFIX + '/host'),
    #                                     user=getSSMParam(TraderHistory.SSM_DB_PREFIX + '/user'),
    #                                     passwd=getSSMParam(TraderHistory.SSM_DB_PREFIX + '/password'),
    #                                     db=getSSMParam(TraderHistory.SSM_DB_PREFIX + '/database'),
    #                                     port=int(getSSMParam(TraderHistory.SSM_DB_PREFIX + '/port')))

    async def __init_exchange(self, exchangeName: str, exchangeCreds):
        exchange = getattr(ccxt, exchangeName)(exchangeCreds)
        await exchange.load_markets()
        self.__exchanges[exchangeName.lower().replace(" ", "")] = exchange

    async def __close_exchange(self, exchange):
        await exchange.close()

    async def __close_exchanges(self):
        tasks = []
        for _, exchange in self.__exchanges.items():
            tasks.append(asyncio.ensure_future(
                self.__close_exchange(exchange)))
        await asyncio.gather(*tasks)
        logger.info("Exchanges closed")

    async def fetch_balance(self, exchange):
        for retrycntr in range(TraderHistory.NOF_CCTX_RETRY):
            t1 = time.time()
            try:
                balance = await exchange.fetch_balance()
                self.__balances[exchange.name.lower().replace(
                    " ", "")] = balance
                d_ms = (time.time() - t1) * 1000.0
                logger.info('Balance fetching completed from ' +
                            exchange.name + f" in {d_ms} ms")
                await asyncio.sleep(exchange.rateLimit / 1000)  # wait for rateLimit
                return
            except (ccxt.ExchangeError, ccxt.NetworkError) as error:
                d_ms = (time.time() - t1) * 1000.0
                logger.error('Fetch balance failed from ' + exchange.name +
                             " " + type(error).__name__ + " " +
                             str(error.args) + " retrycntr:" + str(retrycntr) + f" in {d_ms} ms")
                await asyncio.sleep(exchange.rateLimit / 1000)
        logger.error(f'Error during fetch balance for {exchange}.')
        raise ValueError(f'Error during fetch balance for {exchange}.')

    async def fetch_balances(self):
        self.__balances = {}
        tasks = []
        for _, exchange in self.__exchanges.items():
            tasks.append(asyncio.ensure_future(self.fetch_balance(exchange)))
        await asyncio.gather(*tasks)

    def get_free_balance(self, exchangeName, symbol) -> float:
        try:
            return float(self.__balances[exchangeName][symbol]["free"])
        except Exception as e:
            # logger.warning()
            raise ValueError(
                f"No balance available from {exchangeName} {symbol} {self.__balances[exchangeName][symbol]['free']}")

    def get_exchange(self, exchange_name: str) -> Exchange:
        if exchange_name not in self.__exchanges:
            raise ValueError(
                f'Exchange ({exchange_name}) does not exists in initialized exchanges'
            )
        return self.__exchanges[exchange_name]

    def get_market(self, exchange_name: str,
                   market_str: str) -> Dict[str, Any]:
        exchange = self.get_exchange(exchange_name)
        if market_str not in exchange.markets:
            raise ValueError(
                f'Symbol ({market_str}) does not exists in exchange ({exchange_name})'
            )
        return exchange.markets[market_str]

    def __insertOrders(self, exchange, orders):
        for order in orders:
            self.__insertOrder(exchange, order)

    def __insertOrder(self, exchange, order):

        query = " INSERT ignore  INTO `order`" \
                "(exchange, exchange_id, `timestamp`, `datetime`, status, symbol, `type`, side, price, cost, amount, filled, remaining, fee_cost, fee_currency, fee_rate, json)" \
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s, %s, %s)"
        args = (
            exchange,
            order['id'],
            order['timestamp'],
            order['datetime'],
            order['status'],
            order['symbol'],
            order['type'],
            order['side'],
            order['price'],
            order['cost'],
            order['amount'],
            order['filled'],
            order['remaining'],
            order['fee']['cost'] if order['fee'] is not None else 0,
            order['fee']['currency'] if order['fee'] is not None else 0,
            order['fee']['rate'] if order['fee'] is not None else 0,
            json.dumps(order, indent=2)
        )

        try:

            cursor = self.__db.cursor()
            cursor.execute(query, args)

            if cursor.lastrowid:
                if cursor.lastrowid % 100 == 0:
                    print('last insert id', cursor.lastrowid)

            self.__db.commit()
        except Exception as e:
            print(e)

    def __insertTrades(self, exchange, trades):
        for trade in trades:
            self.__insertTrade(exchange, trade)

    def __insertTrade(self, exchange, trade):

        query = " INSERT ignore  INTO `trade`" \
                "(exchange, exchange_id, exchange_order_id, `timestamp`, `datetime`, symbol, `type`, side, price, cost, amount, fee_cost, fee_currency, fee_rate, json)" \
                "VALUES(%s,%s,%s,%s,%s,%s,%s,%s, %s,%s,%s,%s,%s,%s, %s)"
        args = (
            exchange,
            trade['id'],
            trade['order'],
            trade['timestamp'],
            trade['datetime'],
            trade['symbol'],
            trade['type'],
            trade['side'],
            trade['price'],
            trade['cost'],
            trade['amount'],
            trade['fee']['cost'],
            trade['fee']['currency'],
            trade['fee'].get('rate', None),
            json.dumps(trade, indent=2)
        )

        try:
            cursor = self.__db.cursor()
            cursor.execute(query, args)
            self.__db.commit()
        except Exception as e:
            print(e)

    async def pollTrades(self):
        for _, exchange in self.__exchanges.items():
            if exchange.has['fetchOrders']:
                if exchange.id == 'binance':
                    for symbol in TraderHistory.SYMBOLS:
                        try:
                            if symbol in exchange.symbols:
                                logger.debug(f"CALL: {exchange.id}.fetchOrders({symbol})")
                                fetchOrdersItems = await exchange.fetchOrders(symbol)
                                logger.debug(fetchOrdersItems)
                                self.__insertOrders(exchange.id, fetchOrdersItems)
                        except Exception as e:
                            logger.error(e)
                else:
                    try:
                        logger.debug(f"CALL: {exchange.id}.fetchOrders()")
                        fetchOrdersItems = await exchange.fetchOrders()
                        logger.debug(fetchOrdersItems)
                        self.__insertOrders(exchange.id, fetchOrdersItems)
                    except Exception as e:
                        logger.error(e)

        for _, exchange in self.__exchanges.items():
            if exchange.has['fetchClosedOrders']:
                if exchange.id == 'binance':
                    for symbol in TraderHistory.SYMBOLS:
                        try:
                            if symbol in exchange.symbols:
                                logger.debug(f"CALL: {exchange.id}.fetchClosedOrders({symbol})")
                                fetchClosedOrdersItems = await exchange.fetchClosedOrders(symbol)
                                logger.debug(fetchOrdersItems)
                                self.__insertOrders(exchange.id, fetchClosedOrdersItems)
                        except Exception as e:
                            logger.error(e)
                else:
                    try:
                        logger.debug(f"CALL: {exchange.id}.fetchClosedOrders()")
                        fetchClosedOrdersItems = await exchange.fetchClosedOrders()
                        logger.debug(fetchClosedOrdersItems)
                        self.__insertOrders(exchange.id, fetchClosedOrdersItems)
                    except Exception as e:
                        logger.error(e)

        for _, exchange in self.__exchanges.items():
            if exchange.has['fetchMyTrades']:
                if exchange.id == 'coinbasepro' or exchange.id == 'binance':
                    for symbol in TraderHistory.SYMBOLS:
                        try:
                            if symbol in exchange.symbols:
                                logger.debug(f"CALL: {exchange.id}.fetchMyTrades({symbol})")
                                fetchMyTradesItems = await exchange.fetchMyTrades(symbol=symbol, since=None, limit=None, params={})
                                logger.debug(fetchMyTradesItems)
                                self.__insertTrades(exchange.id, fetchMyTradesItems)
                        except Exception as e:
                            logger.error(e)
                else:
                    try:
                        logger.debug(f"CALL: {exchange.id}.fetchMyTrades()")
                        fetchMyTradesItems = await exchange.fetchMyTrades(symbol=None, since=None, limit=None, params={})
                        logger.debug(fetchMyTradesItems)
                        self.__insertTrades(exchange.id, fetchMyTradesItems)
                    except Exception as e:
                        logger.error(e)
