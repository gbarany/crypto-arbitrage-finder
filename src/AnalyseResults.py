
# coding: utf-8

# In[2]:

import pandas as pd
import operator
# In[]:
df = pd.read_csv('./results/arbitrage_Vol=1BTC-0.1BTC-0.01BTC_XC=coinfloor-kraken-bitfinex-bittrex-gdax-bitstamp-coinbase-poloniex.csv')
df_grouped=df[['exchanges_involved', 'profit_perc','vol_BTC','nodes']].groupby(['exchanges_involved','vol_BTC','nodes']).agg(['min','max','mean', 'count']).sort_values([('profit_perc', 'mean')], ascending=False)
tradelog = {}
for index, row in df_grouped.iterrows():
    trades=row.name[2].split(',')
    for idx, trade in enumerate(trades[:-1]):
        tradeFrom = trade.split('-')
        tradeTo = trades[idx+1].split('-')
        key = ((tradeFrom[0],tradeFrom[1]),(tradeTo[0],tradeTo[1]))
        if key in tradelog.keys():
            tradelog[key] += row[('profit_perc', 'count')]
        else:
            tradelog[key] = row[('profit_perc', 'count')]

sorted_d = sorted(tradelog.items(), key=operator.itemgetter(1),reverse=True)

#for item in sorted_d:
#    print(item)

def generateExchangeTradingPairs(exchangeName = 'Bitstamp',limit = 10,verbose=True):
    str = ''
    cntr=0
    for item in sorted_d:
        if item[0][0][0].lower()==exchangeName.lower() and item[0][1][0].lower()==exchangeName.lower():
            if verbose:
                print(item[0][0][1],item[0][1][1],item[1])
            A = item[0][0][1]
            B = item[0][1][1]
            if A == 'EUR' or A =='USD' or A =='GBP':
                str += "'"+B+"/"+A+"',"
            elif A == 'BTC' and B!='EUR' and B!='USD' and B!='GBP':
                str += "'"+B+"/"+A+"',"
            elif A == 'ETH' and B!='EUR' and B!='USD' and B!='GBP' and B!='BTC' :
                str += "'"+B+"/"+A+"',"
            else:
                str += "'"+A+"/"+B+"',"
            cntr+=1
            if cntr>=limit:
                break
    str ="symbols['"+exchangeName+"'] =" + "["+str[:-1]+"]"
    print(str)


exchangeNames=['coinfloor','Kraken','Bitfinex','Bittrex','Gdax','Bitstamp','Coinbase','Poloniex']
for exchangeName in exchangeNames:
    generateExchangeTradingPairs(exchangeName=exchangeName,limit=10,verbose=False)