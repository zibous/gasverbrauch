#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))


from pandas import json_normalize
from conf_default import *

# call dir and store it in a variable.
all_variables = dir()

fields = ['APPS_DESCRIPTION', 'APPS_NAME', 'APPS_VERSION',
          'COST_CALCULATION', 'COST_CALCULATION_ON', 'DATADIR',
          'DATAFILE', 'DATA_HOSTNAME', 'DATA_PROVIDER',
          'DATEFORMAT_CURRENT', 'DATEFORMAT_DAY',
          'DATEFORMAT_HOUR', 'DATEFORMAT_MONTH', 'DATEFORMAT_TIMESTAMP',
          'DATEFORMAT_UTC', 'DATEFORMAT_YEAR', 'DATE_DEFAULT', 'DATE_DEFAULT_MIN',
          'DATE_LIST', 'DATE_NOW', 'EMS_API_URL', 'EMS_ERROR_TEXT',
          'EMS_MODES', 'ESP32_API_DATA', 'ESP32_GASMETER_API',
          'ESP32_GASMETER_FIELDS', 'ESP32_GASMETER_PASSWORD',
          'ESP32_GASMETER_PORT', 'GASMETER_HA_DISCOVERY_ID', 'GASMETER_HA_DISCOVERY_ITEMS',
          'GASMETER_HA_DISCOVERY_SAVE', 'GASMETER_HA_DISCOVERY_TOPIC', 'GASMETER_HA_SECTION',
          'GASMETER_MEASUREMENT', 'GOTIFY_PRIORITY', 'GOTIFY_SERVICE', 'GOTIFY_TITLE',
          'GOTIFY_TOKEN', 'INFLUXDB_HOST', 'INFLUXDB_LOG_DIR', 'INFLUXDB_NAME',
          'INFLUXDB_PASSWORD', 'INFLUXDB_PORT', 'INFLUXDB_USER', 'LOG_DIR', 'LOG_LEVEL',
          'MQTTAUTH', 'MQTTCLIENT', 'MQTTHOST', 'MQTTPORT', 'MQTTTOPIC', 'MQTT_BASETOPIC',
          'MQTT_LWT_TOPIC', 'REPORTFILE', 'SMARTMETER_ID', 'SMARTMETER_IDENTIFIER',
          'SMARTMETER_MANUFATURER', 'SMARTMETER_MODEL', 'SMARTMETER_NAME', 'TIME_FORMAT']

igonore = [
          '__annotations__', '__builtins__',
          '__cached__', '__doc__', '__file__',
          '__loader__', '__name__',
          '__package__', '__spec__',
          'calcGasCost', 'datetime',
          'getTimestamp', 'os',
          'string', 'sys']


# Iterate over the whole list where dir( ) is stored.
print("All config variables:")
i = 1
data = []
for name in all_variables:
    # if not name.startswith('__'):
    # print(name, "is", type(myvalue), "and is equal to ", myvalue)
    if not name in igonore:
        i = i + 1
        myvalue = str(eval(name))
        item = {}
        item["variable"] = name
        item["remarks"] = "        "
        print(item)
        data.append(item)

    df = json_normalize(data)
    filename = "variables.csv"
    df.to_csv(filename, index=False)

print()

print("Date and Time:")
print(datetime.now().strftime(DATEFORMAT_CURRENT))
print(datetime.now().strftime(DATEFORMAT_DAY))
print(datetime.now().strftime(DATEFORMAT_HOUR))
print(datetime.now().strftime(DATEFORMAT_MONTH))
print(datetime.now().strftime(DATEFORMAT_TIMESTAMP))
print(datetime.now().strftime(DATEFORMAT_UTC))
print(datetime.now().strftime(DATEFORMAT_YEAR))
print(DATE_DEFAULT)
print(datetime.now().strftime(DATE_DEFAULT_MIN))
print(DATE_NOW)
