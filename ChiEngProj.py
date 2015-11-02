# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 23:25:47 2015

Data incubator challenge question

"predicting power usage for new home owners" version 1.0
based on 2010 usage and weather data in Chicago

@author: Sangkyu Lee
"""
import pandas as pd
import numpy as np
import requests
import json
import calendar
from ggplot import *
#matplotlib.style.use('ggplot')

##################subfunctions#######################################
# month name parsing
def IsItMonth(colname):
    found = False
    monthnames = [x.lower() for x in calendar.month_name[1:]]
    found = any(s in colname for s in monthnames)
    return found
# used as a key function to sort month columns    
def MonthSorting(colname):    
    month_key = {m.lower(): i for i, m in enumerate(calendar.month_name[1:])}
    for mon_name in month_key.keys():
        if mon_name in colname:
            ind_to_return = month_key[mon_name]
    return ind_to_return    
# returns the rows with extreme values (defined by deviation from mean)    
def DetectOutlier(df,sigma):
    from scipy import stats as stats
    in_rows = (np.abs(stats.zscore(df)) < sigma).all(axis=1)
    return in_rows
 
#####################################################################

# API data import 
url = 'https://data.cityofchicago.org/resource/energy-usage-2010.json?'
# create a filter
filt = [
    '$limit=50000',
    #'&building_subtype=Multi+7%2B',
    '&building_type=Residential',
    #'&average_stories=2',
    '&$where=occupied_units_percentage > 0.5']
token = 'TNukBspJMhzXso6cZ9guqb6w2'
r = requests.get(url+''.join(filt), headers={'X-App-Token':token})
print(r.status_code)
data_json = json.loads(r.text)
_data_raw = pd.DataFrame(data_json)
_data_raw = _data_raw.convert_objects(convert_numeric=True)
_data_raw.rename(columns={'term_april_2010': 'therm_april_2010'}, inplace=True)
data_raw = _data_raw[_data_raw.notnull().all(axis=1)] # remove NaN

#separate time series data for power and gas consumption
el_time_cols = [col for col in data_raw.columns if IsItMonth(col) & ('kwh' in col)]
gas_time_cols = [col for col in data_raw.columns if IsItMonth(col) & ('therm' in col)]
time_cols = [col for col in data_raw.columns if IsItMonth(col)]
# normalize the month-by-month consumption by square feet
data_raw.loc[:,el_time_cols] = data_raw[el_time_cols].div(data_raw['kwh_total_sqft'],axis='index')
data_raw.loc[:,gas_time_cols] = data_raw[gas_time_cols].div(data_raw['therms_total_sqft'],axis='index')
# factor into different occupancy factor
data_raw.loc[:,time_cols] = data_raw[time_cols].div(data_raw['occupied_units_percentage'],axis='index') 
# remove outliers (defined here as deviation larger than 3sigma)
in_rows = DetectOutlier(data_raw[time_cols],3)
data_raw_2 = data_raw[in_rows]

# calculate monthly change in consumption
el_timeseries = pd.pivot_table(data_raw_2, values=el_time_cols, columns = 'building_subtype', aggfunc=np.average)
gas_timeseries = pd.pivot_table(data_raw_2, values=gas_time_cols, columns = 'building_subtype', aggfunc=np.average)
# sort rows
el_timeseries = el_timeseries.reindex(sorted(el_time_cols,key=MonthSorting))
gas_timeseries = gas_timeseries.reindex(sorted(gas_time_cols,key=MonthSorting))

# rearrange the data for plotting monthly data
el_timeseries.index = el_timeseries.index.map(lambda st: st.replace('kwh_',''))
el_timeseries.reset_index(level=0, inplace=True)
el_timeseries = el_timeseries.rename(columns = {'index':'month'})
el_timeseries['type'] = ['electricity']*12
el_timeseries_long = pd.melt(el_timeseries,id_vars = ['month','type'])
gas_timeseries.index = gas_timeseries.index.map(lambda st: st.replace('therm_',''))
gas_timeseries.reset_index(level=0, inplace=True)
gas_timeseries = gas_timeseries.rename(columns = {'index':'month'})
gas_timeseries['type'] = ['gas']*12
gas_timeseries_long = pd.melt(gas_timeseries,id_vars = ['month','type'])

frames = [gas_timeseries_long,el_timeseries_long]
timeseries_long = pd.concat(frames)
timeseries_long['month'] = timeseries_long['month'].map(lambda st: st.replace('_',' '))
timeseries_long['month'] = pd.to_datetime(timeseries_long['month'])

plot1 = ggplot(aes(x='month',y='value',colour='building_subtype'),timeseries_long) + \
    geom_line() + \
    facet_grid('type',scales='free_y') + \
    ylab('average consumption per sqft') + \
    scale_x_date(labels='%b %y',breaks=date_breaks('month')) 
ggsave(plot1,'figure1.eps')    

# scatterplot that shows the effect of building age on heat consumption
plot2 = ggplot(aes(x='kwh_july_2010', y='therm_january_2010',colour='average_age'), data=data_raw_2) + \
    geom_point() + \
    ylab('gas consumption per sqft, January 2010 (therm)') + \
    xlab('electricity consumption per sqft, July 2010 (kwh)')
ggsave(plot2,'figure2.eps')


