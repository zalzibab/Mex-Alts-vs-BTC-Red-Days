#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import sys
if not sys.warnoptions:
    import warnings
    warnings.simplefilter("ignore")

import pandas as pd
import requests
import dateutil.parser
from datetime import datetime, timedelta
import time
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import gridspec
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
from matplotlib.pyplot import figure
import matplotlib.dates as mdates
import matplotlib.ticker as mtick
import sys
import numpy as np


# In[ ]:


alt_names = ['ADA', 'BCH', 'ETH', 'EOS', 'LTC', 'TRX', 'XRP']
futs_letters = ['H', 'M', 'U', 'Z']
futs_years = ['17', '18', '19', '20']
combined = []
for x in futs_letters:
    for y in futs_years:
        combined.append(x+y)
contracts = []
for x in alt_names:
    for y in combined:
        contracts.append(x+y)


# In[ ]:


startTimes = []
endTimes = []
null_contracts = []
for x in contracts:
    try:
        resp = requests.get('https://www.bitmex.com/api/v1/instrument?symbol='+x+'&count=1&reverse=false').json()[0]
        startTimes.append(resp['listing'])
        endTimes.append(resp['expiry'])
        time.sleep(1.5)
    except IndexError:
        null_contracts.append(x)
        pass
contracts = [x for x in contracts if x not in null_contracts]


# In[ ]:


binsizes = []
for x in range(len(startTimes)):
    binsizes.append(str((datetime.strptime(endTimes[x], '%Y-%m-%dT%H:%M:%S.%fZ') - datetime.strptime(startTimes[x], '%Y-%m-%dT%H:%M:%S.%fZ')).days+1))


# In[ ]:


quotes = []
xbtusd_quotes = []
for x in range(len(contracts)):
    quotes.append(requests.get('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1d&partial=false&symbol='+contracts[x]+'&count='+binsizes[x]+'&reverse=false&startTime='+startTimes[x]).json())
    xbtusd_quotes.append(requests.get('https://www.bitmex.com/api/v1/trade/bucketed?binSize=1d&partial=false&symbol=XBTUSD&count='+binsizes[x]+'&reverse=false&startTime='+startTimes[x]).json())
    time.sleep(3)


# In[ ]:


contract_dfs = []
xbtusd_dfs = []
for x in range(len(quotes)):
    temp_df = pd.DataFrame(data=quotes[x][0], index=[0])
    temp_xbt_df = pd.DataFrame(data=xbtusd_quotes[x][0], index=[0])
    for y in range(1, len(quotes[x])):
        short_df = pd.DataFrame(data=quotes[x][y], index=[0])
        short_xbt_df = pd.DataFrame(data=xbtusd_quotes[x][y], index=[0])
        temp_df = pd.concat([temp_df, short_df], axis=0)
        temp_xbt_df = pd.concat([temp_xbt_df, short_xbt_df], axis=0)
    contract_dfs.append(temp_df)
    xbtusd_dfs.append(temp_xbt_df)


# In[ ]:


drops = ['symbol', 'high', 'low', 'trades', 'volume', 'vwap', 'lastSize', 'turnover', 'homeNotional', 'foreignNotional']
for x in range(len(xbtusd_dfs)):
    xbtusd_dfs[x] = xbtusd_dfs[x].reset_index(drop=True)
    contract_dfs[x] = contract_dfs[x].reset_index(drop=True)
    contract_dfs[x][contracts[x]+'_daily_btc'] = 0
    contract_dfs[x] = contract_dfs[x].drop(columns=drops)
    for l in range(len(contract_dfs[x])):
        if contract_dfs[x]['open'].iloc[l] is None:
            xbtusd_dfs[x] = xbtusd_dfs[x].drop([l])
    contract_dfs[x] = contract_dfs[x].dropna()
    xbtusd_dfs[x] = xbtusd_dfs[x].drop(columns=drops)
    xbtusd_dfs[x]['xbtusd_daily_change'] = 0
    for y in range(len(xbtusd_dfs[x])):
        contract_dfs[x][contracts[x]+'_daily_btc'].iloc[y] = round(((contract_dfs[x]['close'].iloc[y] - contract_dfs[x]['open'].iloc[y]) / contract_dfs[x]['open'].iloc[y])*100, 2)
        xbtusd_dfs[x]['xbtusd_daily_change'].iloc[y] = round(((xbtusd_dfs[x]['close'].iloc[y] - xbtusd_dfs[x]['open'].iloc[y]) / xbtusd_dfs[x]['open'].iloc[y])*100, 2)
    xbtusd_dfs[x] = xbtusd_dfs[x].reset_index(drop=True)
    contract_dfs[x] = contract_dfs[x].reset_index(drop=True)


# In[ ]:


red_days = []
for x in range(len(xbtusd_dfs)):
    red_days.append(list(*np.where(xbtusd_dfs[x].xbtusd_daily_change < 0)))


# In[ ]:


for x in range(len(red_days)):
    xbtusd_dfs[x] = xbtusd_dfs[x][xbtusd_dfs[x].index.isin(red_days[x])]
    contract_dfs[x] = contract_dfs[x][contract_dfs[x].index.isin(red_days[x])]


# In[ ]:


for x in range(len(xbtusd_dfs)):
    xbtusd_dfs[x] = pd.concat([xbtusd_dfs[x], contract_dfs[x][contracts[x]+'_daily_btc']], axis=1)
    xbtusd_dfs[x][contracts[x]+'_daily_usd'] = round(xbtusd_dfs[x]['xbtusd_daily_change'] + xbtusd_dfs[x][contracts[x]+'_daily_btc'], 2)
    xbtusd_dfs[x][contracts[x]+'_cumulative_btc'] = round(xbtusd_dfs[x][contracts[x]+'_daily_btc'].cumsum(), 2)
    xbtusd_dfs[x] = xbtusd_dfs[x].set_index(pd.to_datetime(xbtusd_dfs[x]['timestamp']))


# In[ ]:


for x in range(len(xbtusd_dfs)):
    figure(num=None, figsize=(26, 14), dpi=100, facecolor='white', edgecolor='black')
    gs = gridspec.GridSpec(2, 1, height_ratios=[3, 1])
    x_axis = xbtusd_dfs[x].index

    ax = plt.subplot(gs[0])
    plt.plot(x_axis, xbtusd_dfs[x]['xbtusd_daily_change'], label = 'xbtusd_daily_change')
    plt.plot(x_axis, xbtusd_dfs[x][contracts[x]+'_daily_btc'], label = contracts[x]+'_daily_btc_change')
    plt.plot(x_axis, xbtusd_dfs[x][contracts[x]+'_daily_usd'], label = contracts[x]+'_daily_usd_change')
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    plt.ylabel('Daily Percent Change', fontdict={'fontsize': 32})
    plt.legend(fontsize=16)
    plt.title(contracts[x]+' vs XBTUSD', fontdict={'fontsize': 32})
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d-%Y"))
    plt.gcf().autofmt_xdate()
    ax.set_axisbelow(True)
    plt.grid(b=True, which='major', axis='both')
    plt.tick_params(axis='x', which='both', top=False, bottom=False, labelbottom=False, labelsize=16)
    plt.tick_params(axis='y', which='both', left=True, right=True, labelleft=True, labelright=True, labelsize=16)


    ax1 = plt.subplot(gs[1], sharex=ax)
    plt.plot(x_axis, xbtusd_dfs[x][contracts[x]+'_cumulative_btc'], label = contracts[x]+'_cumulative_btc_change')
    plt.legend(fontsize=16)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d-%Y"))
    plt.gcf().autofmt_xdate()
    ax1.set_axisbelow(True)
    plt.grid(b=True, which='major', axis='both')
    plt.tick_params(axis='x', which='both', top=False, bottom=True, labelbottom=True, labelsize=16)
    plt.tick_params(axis='y', which='both', left=True, right=True, labelleft=True, labelright=True, labelsize=16)

    plt.tight_layout(True)
    plt.autoscale(tight=True)
    plt.subplots_adjust(top=0.955, bottom=0.07, left=0.07, right=0.93, hspace=0, wspace=0)
    plt.savefig(str(sys.path[0])+'/Charts/'+contracts[x][0:3]+'/'+contracts[x]+'_Chart.png');
    plt.clf()
    
    xbtusd_dfs[x]['timestamp'] = xbtusd_dfs[x].index
    xbtusd_dfs[x].to_csv(str(sys.path[0])+'/Charts/'+contracts[x][0:3]+'/'+contracts[x]+'_DataFrame.csv', index=False)


# In[ ]:





# In[ ]:




