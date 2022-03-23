#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# -----------------------------------------------
# all settings for the gasverbrauch application
# -----------------------------------------------

import os
import os.path
from datetime import datetime
import string

# date and time formats
DATEFORMAT_TIMESTAMP = '%Y-%m-%dT%H:%M:%S'
DATEFORMAT_CURRENT = '%Y-%m-%d %H:%M:%S.%f'
DATEFORMAT_HOUR = '%H'
DATEFORMAT_DAY = '%Y-%m-%d'
DATEFORMAT_MONTH = '%Y-%m'
DATEFORMAT_YEAR = '%Y'
TIME_FORMAT = '%H:%M:%S'
DATEFORMAT_UTC = '%Y-%m-%dT%H:%M:%SZ'
DATE_NOW = datetime.now()
DATE_DEFAULT = DATE_NOW.strftime(DATEFORMAT_TIMESTAMP)
DATE_DEFAULT_MIN = "1900-01-01T00:00:00"


def getTimestamp() -> string:
    return datetime.now().strftime(DATEFORMAT_TIMESTAMP)


# date list for periodes
# dynamic can be expand with week, quater ...
DATE_LIST = {
    "gas_per_hour": DATEFORMAT_HOUR,
    "gas_per_day": DATEFORMAT_DAY,
    "gas_per_month": DATEFORMAT_MONTH,
    "gas_per_year": DATEFORMAT_YEAR
}

# gasmeter device setting has to be defined
SMARTMETER_ID = 'GB172BKG'  # internal used smartmeter identification
SMARTMETER_NAME = 'GB172/14 + BK-G2.5'  # Name of the smartmeter
SMARTMETER_IDENTIFIER = "Gaszähler Elster BK-G4 MT"
SMARTMETER_MANUFATURER = "Elster"
SMARTMETER_MODEL = "Gaszähler Elster BK-G4 MT"

# application settings has to be defined
APPS_VERSION = '1.0.3'  # Application version
APPS_DESCRIPTION = "Get esp32-gasmeter values and data from the esp-ems"
APPS_NAME = 'Gasverbauchmessung'
DATADIR = os.path.join(os.path.dirname(__file__), 'data/')
DATAFILE = "{}{}.json".format(DATADIR, SMARTMETER_ID)
REPORTFILE = "{}{}.csv".format(DATADIR, SMARTMETER_ID)
DATA_PROVIDER = 'Data provided by Peter Siebler'
DATA_HOSTNAME = os.uname().nodename


# switch logging has to be defined
LOG_LEVEL = 10  # DEBUG: 10
# LOG_LEVEL = 20  # INFO: 20
# LOG_LEVEL = 30  # WARNING: 30
# LOG_LEVEL = 40  # ERROR: 40
# LOG_LEVEL = 50  # CRITICAL: 50
# LOG_LEVEL = 100 # DISABLED: 100
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs/')

# ems-esp api: has to be defined
EMS_API_URL = "http://ems-heizung.siebler.home/api/boiler"
EMS_MODES = {
    "idle": "idle",
    "water": "boiler",
    "heat": "heizung"
}
EMS_ERROR_TEXT = "Fehler bei der Heizung:\n"

# esp32 Device ha-gasmeter (esphome)
ESP32_GASMETER_API = "wasserundgas.local"
ESP32_GASMETER_PORT = 6053
ESP32_GASMETER_PASSWORD = ""
ESP32_GASMETER_FIELDS = "WUG Gasverbrauch gesamt"
ESP32_API_DATA = {}

# mqtt brocker settings (optional)
# disable mqtt brocker: set MQTTHOST = None
MQTTHOST = "mbs.local"
MQTTPORT = 1883
MQTT_BASETOPIC = "ems-heizung"
MQTTTOPIC = "ems-heizung/gas_data"
MQTT_LWT_TOPIC = "ems-heizung/gas_data/LWT"
MQTTCLIENT = "gasmeter.service"
MQTTAUTH = {
    "username": "theMqttMaster",
    "password": "JgEJu9u6nmqoLiQfWUrjWd3C8"
}

# all for the homeassistant discovery
# disable ha discovery: set GASMETER_HA_DISCOVERY_TOPIC = None
GASMETER_HA_DISCOVERY_TOPIC = "homeassistant"
GASMETER_HA_DISCOVERY_ID = "ESP-Gasmeter"
GASMETER_HA_SECTION = "gas-data"
GASMETER_HA_DISCOVERY_ITEMS = "{}ha-{}.json".format(DATADIR, SMARTMETER_ID)
GASMETER_HA_DISCOVERY_SAVE = True

# all for the influx database (optional)
# disable INFLUXDB Service: set INFLUXDB = None
INFLUXDB_NAME = 'historydata'
INFLUXDB_HOST = 'influx.local'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'dbAdmin'
INFLUXDB_PASSWORD = 'yTWCpNyjExjsDWdJQZso3pBjZ'
INFLUXDB_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs/')
GASMETER_MEASUREMENT = 'gasmeter'

# all for the gotify messages
# disable Gotify Service: set GOTIFY_SERVICE = None
GOTIFY_SERVICE = "https://localhost/gotify/"
GOTIFY_TOKEN = "gFbKKfM4wMfb7S"
GOTIFY_TITLE = "Meldung Heizung"
GOTIFY_PRIORITY = 2

# cost calculation
# optional: disable COST_CALCULATION_ON = False
# Gas Kubikmeter (m³) in Kilowattstunden (kWh) umrechnen
# see: https://www.e-control.at/gas-umrechnungs-check-applikation
COST_CALCULATION_ON = True
COST_CALCULATION = {
    "gaskwhperm3": round((11.26 * 0.9264), 2),
    "unit": "kWh/Nm³",
    "gaskwh": 0.0758
}


def calcGasCost(gasm3: float = 0.00) -> float:
    """simple gascost calulation"""
    return round(gasm3 * COST_CALCULATION["gaskwhperm3"] * COST_CALCULATION["gaskwh"], 2)
