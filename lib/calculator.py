#!/usr/bin/python3
# -*- coding":" utf-8 -*-

import sys
from urllib import response

# all requirements packages
try:
    import json
    import time
    import os
    import os.path
    from datetime import datetime
    import paho.mqtt.publish as publish

    from conf import *
    from lib import logger
    from lib import utils
    from lib import gotifymessage as gotify
    from lib import influxdata


except Exception as e:
    print('Configuration error {}, check config.py'.format(e))
    sys.exit(1)

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR, LOG_SHOWLINES)


class Calculator():
    """Calculater class calcs all value for the current gasmeter values based on EMS-ESP and Gasmeter ESP Device"""

    version = "1.2.0"

    def __init__(self):
        """constuctor caclculator"""
        log.debug('✔︎ Init {}, version {}'.format(__name__, self.version))
        self.emsheaterFilename = "{}{}.json".format(DATADIR, SMARTMETER_ID)
        self.prev_data = {}
        self.curr_data = {}
        self.ready = False
        self.runcount = 0
        self.lastRun = datetime.now()

    def __getElapsedTime__(self, timestamp: datetime = datetime.now()) -> int:
        """get the elapsed time in minutes:
           result = now - timestamp
           example: self.__getElapsedTime__(self.lastRun)
        """
        try:
            diff = datetime.now() - timestamp
            return int(diff.total_seconds()/60)

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return -1

    def __checkTimeOrDate__(self, format: str = DATEFORMAT_HOUR, checkInitDate: bool = False) -> bool:
        """ checks if the current date or time has changed"""
        try:
            lastDate = datetime.strptime(self.prev_data['dattimestamp'], DATEFORMAT_TIMESTAMP)
            if checkInitDate and lastDate.strftime(DATEFORMAT_YEAR) == "1900":
                return False
            newDate = datetime.now()
            hasChange = (newDate.strftime(format) != lastDate.strftime(format))
            if hasChange:
                log.info("{}: Data format {} has changed: Last={}  New={}".format(
                         sys._getframe().f_code.co_name,
                         DATEFORMAT_TIMESTAMP,
                         lastDate.strftime(format),
                         newDate.strftime(format)
                         ))
            return hasChange
        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __checkChanged__(self) -> bool:
        """Checks if the timeslot hour, day, month and year has changed and calculates the gas consumption for the period"""
        try:
            # get the timestamps
            timestamp = datetime.strptime(self.prev_data['dattimestamp'], DATEFORMAT_TIMESTAMP)
            self.curr_data['elapsed_time'] = self.__getElapsedTime__(timestamp) * 60

            # all periodes
            for key in DATE_LIST:
                format = DATE_LIST[key]
                if(self.__checkTimeOrDate__(format, False)):
                    # reset or init value
                    if not (key in self.curr_data):
                        self.curr_data[key] = {}

                    log.debug("{}: Init values for {}, new period found !".format(sys._getframe().f_code.co_name, key))

                    # init values if date or time has changed
                    self.curr_data[key]['boiler'] = float(0.00)
                    self.curr_data[key]['heater'] = float(0.00)
                    self.curr_data[key]['disinfecting'] = float(0.00)

                    # update values based on the mode
                    if self.curr_data['gasverbrauch_boiler']:
                        self.curr_data[key]['boiler'] = self.curr_data['gasverbrauch_boiler']

                    if self.curr_data['gasverbrauch_heater']:
                        self.curr_data[key]['heater'] = self.curr_data['gasverbrauch_heater']

                    if self.curr_data['boiler_disinfecting'] == "on":
                        self.curr_data[key]['disinfecting'] = self.curr_data['gasverbrauch_boiler']
                else:
                    # add new values
                    if not (key in self.curr_data):
                        self.curr_data[key] = {}
                    self.curr_data[key]['boiler'] = round(float(self.prev_data[key]['boiler']) + float(self.curr_data['gasverbrauch_boiler']), 3)
                    self.curr_data[key]['heater'] = round(float(self.prev_data[key]['heater']) + float(self.curr_data['gasverbrauch_heater']), 3)
                    if not ("disinfecting" in self.prev_data[key]):
                        self.prev_data[key]['disinfecting'] = float(0.00)
                    if self.curr_data['boiler_disinfecting'] == "on":
                        self.curr_data[key]['disinfecting'] = round(float(self.prev_data[key]['disinfecting']) + float(self.curr_data['gasverbrauch_boiler']), 3)
                    else:
                        self.curr_data[key]['disinfecting'] = round(float(self.prev_data[key]['disinfecting']), 3)

                # check the last error
                if not ("lasterror" in self.prev_data):
                    self.prev_data['lasterror'] = self.curr_data['lasterror']
                if(self.curr_data['lasterror'] != self.prev_data['lasterror']):
                    gotify.sendMessage(GOTIFY_TITLE, "{} ERROR:{}".format(EMS_ERROR_TEXT, self.curr_data['lasterror']))

            return True

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __calcCosts__(self) -> bool:
        """simple gas cost calculation based on the config setting"""
        try:
            if COST_CALCULATION_ON:
                for key in DATE_LIST:
                    field = "{}{}".format("cost_", key)
                    if not (field in self.curr_data):
                        self.curr_data[field] = {}
                    self.curr_data[field]['boiler'] = calcGasCost(self.curr_data[key]['boiler'])
                    self.curr_data[field]['heater'] = calcGasCost(self.curr_data[key]['heater'])
                    self.curr_data[field]['disinfecting'] = calcGasCost(self.curr_data[key]['disinfecting'])
            return True

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __calcData__(self) -> bool:
        """Calculates the gas consumption based on the values from the ems-esp and gasmeter esp device"""
        try:
            if self.prev_data:
                log.debug("{}: Mode: {}".format(sys._getframe().f_code.co_name, EMS_MODES['idle']))
                # init the defaults
                self.curr_data['mode'] = EMS_MODES['idle']
                self.curr_data['gasverbrauch_boiler'] = float(0.00)
                self.curr_data['gasverbrauch_heater'] = float(0.00)
                # check boiler or heater mode
                if(self.curr_data['boiler_active'] == 'on'):
                    self.curr_data['mode'] = EMS_MODES['water']
                else:
                    if(self.curr_data['heater_active'] == 'on'):
                        self.curr_data['mode'] = EMS_MODES['heat']
                # get the gas consumption
                gas_delta = utils.fix_float((self.curr_data['gas_total'] - self.prev_data['gas_total']))
                # calculate the current gas consumption
                self.curr_data['gasverbrauch'] = round(gas_delta, 3)
                if(self.curr_data['mode'] == EMS_MODES['water']):
                    self.curr_data['gasverbrauch_boiler'] = self.curr_data['gasverbrauch']
                if(self.curr_data['mode'] == EMS_MODES['heat']):
                    self.curr_data['gasverbrauch_heater'] = self.curr_data['gasverbrauch']
                # calc the values for periodes
                if(self.__checkChanged__() == False):
                    log.warning("{}:calc changed values faild!".format(sys._getframe().f_code.co_name))
                    return False
                # make the cost calculation
                self.__calcCosts__()
                return self.ready
            else:
                log.warning("{}:Missing previous data".format(sys._getframe().f_code.co_name))
                return False

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __loadData__(self) -> bool:
        """loads the previous data form the defined json file"""
        try:
            fileName = self.emsheaterFilename
            if not os.path.isfile(fileName):
                fileName = fileName.replace(".json", "_default.json")
                log.debug("{}: No previous datafile:{}, try to use the default {}".format(sys._getframe().f_code.co_name, self.emsheaterFilename, fileName))

            if os.path.isfile(fileName):
                with open(fileName, 'r', encoding='utf-8') as fp:
                    self.prev_data = json.load(fp)
                log.debug("{}: Load previous Data:{} o.k".format(sys._getframe().f_code.co_name, fileName))
                return True

            else:
                log.debug("{}: Fallback - Init previous Data:{}".format(sys._getframe().f_code.co_name, fileName))
                self.prev_data = {}
                self.prev_data['gas_total'] = float(0.00)
                for key in DATE_LIST:
                    self.prev_data[key] = {}
                    self.prev_data[key]['boiler'] = float(0.00)
                    self.prev_data[key]['heater'] = float(0.00)
                    self.prev_data[key]['disinfecting'] = float(0.00)
                self.prev_data['boiler_disinfecting'] = "off"
                self.prev_data['boiler_disinfecting_sec'] = 0
                self.curr_data['boiler_disinfecting_start'] = DATE_DEFAULT_MIN
                self.curr_data['boiler_disinfecting_end'] = DATE_DEFAULT_MIN
                self.prev_data['dattimestamp'] = DATE_DEFAULT_MIN
                return False

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __saveData__(self) -> bool:
        """saves the current data to the defined json file"""
        try:
            if(self.curr_data and self.emsheaterFilename):
                with open(self.emsheaterFilename, 'w', encoding='utf-8') as f:
                    json.dump(self.curr_data, f, indent=2, ensure_ascii=False)
                log.debug("{}: Save Data:{} o.k".format(sys._getframe().f_code.co_name, self.emsheaterFilename))
            return True
        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __saveReportData__(self) -> bool:
        """saves the values (per month) to the history report data file"""
        try:
            if (self.ready == False):
                # first start, skip calculation, because we don't have previous data
                return False

            if REPORTFILE:
                # reportfile is defined
                if(self.__checkTimeOrDate__(DATEFORMAT_MONTH, True)):
                    # all data for the history data
                    if ESP32_API_DATA and ("wug_gasverbrauch_gesamt" in ESP32_API_DATA) and ("wug_gaszähler_anzeige" in ESP32_API_DATA):
                        now = datetime.now()
                        datalist = (
                            self.curr_data['device'],
                            self.curr_data['id'],
                            now.strftime(DATEFORMAT_DAY),
                            now.strftime(TIME_FORMAT),
                            # all from the gasmeter
                            ESP32_API_DATA['wug_gaszähler_anzeige'],
                            ESP32_API_DATA['wug_gasverbrauch_gesamt'],
                            # for the last month
                            self.curr_data['gas_per_month']['boiler'],
                            self.curr_data['gas_per_month']['heater'],
                            self.curr_data['gas_per_month']['boiler_disinfecting'],
                            # for the current year
                            self.curr_data['gas_per_year']['boiler'],
                            self.curr_data['gas_per_year']['heater'],
                            self.curr_data['gas_per_year']['boiler_disinfecting'],
                            # consumtion over all
                            self.curr_data['gas_total'],
                            self.curr_data['gas_heater'],
                            self.curr_data['gas_boiler'],
                            ESP32_API_DATA['wug_timestamp'],
                            now.strftime(DATEFORMAT_TIMESTAMP)
                        )
                        log.debug("{}: Save Report: {} to file{}".format(sys._getframe().f_code.co_name, datalist, REPORTFILE))
                        output = ",".join(map(str, datalist))
                        with open(REPORTFILE, 'a+') as f:
                            f.write(output + '\n')
                        return True
                    else:
                        return False
            else:
                log.debug("{}:Save Reportdata disabled".format(sys._getframe().f_code.co_name))
                return False

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __publishData__(self) -> bool:
        """publish the data to the mqtt brocker"""
        try:
            if MQTTHOST:
                # mqtt brocker defined, publish the data
                json_data = json.dumps(self.curr_data, ensure_ascii=False)
                log.info("{}: Publish MQTT Topic:{}".format(sys._getframe().f_code.co_name, MQTTTOPIC))
                publish.single(MQTTTOPIC, payload=json_data, qos=0, retain=False, hostname=MQTTHOST,
                               port=MQTTPORT, client_id=MQTTCLIENT, keepalive=60, auth=MQTTAUTH)
            else:
                log.debug("{}:MQTT Service disabled".format(sys._getframe().f_code.co_name))

            # send gotify message every day
            if(self.__checkTimeOrDate__(DATEFORMAT_DAY, True)):
                if ESP32_API_DATA and "wug_gasverbrauch_gesamt" in ESP32_API_DATA:
                    messageData = [
                        "Gaszähler Anzeige: {} m³".format(ESP32_API_DATA['wug_gaszähler_anzeige']),
                        "Gasverbrauch:"
                        " - Gesamt: {} m³".format(ESP32_API_DATA['wug_gasverbrauch_gesamt']),
                        " - Warmwasser: {} m³".format(self.curr_data['gas_per_month']['boiler']),
                        " - Boilerdesinfizierung: {}".format(self.curr_data['gas_per_month']['disinfecting']),
                        " - Heizen: {} m³".format(self.curr_data['gas_per_month']['heater']),
                        "created by {} {}, {} ".format(APPS_NAME, APPS_VERSION, DATA_HOSTNAME)
                    ]
                    message = '\n'.join(messageData)
                    gotify.sendMessage(GOTIFY_TITLE, message)

            return True

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def __publishToInfluxdb__(self):
        """Publish the defined fields to the influx db"""
        try:
            if INFLUXDB_HOST and INFLUXDB_GASMETER_MEASUREMENT:
                log.info("{}: Publish Data to influxDB".format(sys._getframe().f_code.co_name))
                i = influxdata.InfuxdbCient()
                # all fields for the influx database
                row = dict()
                if ESP32_API_DATA and "wug_gaszähler_anzeige" in ESP32_API_DATA:
                    row['gas_display'] = ESP32_API_DATA['wug_gaszähler_anzeige']
                if ESP32_API_DATA and "wug_gasverbrauch_gesamt" in ESP32_API_DATA:
                    row['gas_overall'] = ESP32_API_DATA['wug_gasverbrauch_gesamt']
                row['gas_total'] = self.curr_data['gas_total']
                row['gas_heater'] = self.curr_data['gas_heater']
                row['gas_boiler'] = self.curr_data['gas_boiler']
                row['gas_boiler'] = self.curr_data['gas_boiler']
                row['gasverbrauch'] = self.curr_data['gasverbrauch']
                row['gasverbrauch_boiler'] = self.curr_data['gasverbrauch_boiler']
                row['gasverbrauch_heater'] = self.curr_data['gasverbrauch_heater']
                row['runnig_total_sec'] = self.curr_data['runnig_total_sec']
                row['runnig_heater_ratio'] = self.curr_data['runnig_heater_ratio']
                row['runnig_boiler_ratio'] = self.curr_data['runnig_boiler_ratio']
                for key in DATE_LIST:
                    row["{}_boiler".format(key)] = self.curr_data[key]['boiler']
                    row["{}_heater".format(key)] = self.curr_data[key]['heater']
                    row["{}_disinfecting".format(key)] = self.curr_data[key]['disinfecting']
                    field = "{}{}".format("cost_", key)
                    row["cost_{}_boiler".format(key)] = self.curr_data[field]['boiler']
                    row["cost_{}_heater".format(key)] = self.curr_data[field]['heater']
                    row["cost_{}_disinfecting".format(key)] = self.curr_data[field]['disinfecting']
                if row:
                    i.post(row, INFLUXDB_GASMETER_MEASUREMENT)
                    return True
                else:
                    log.warning("{}: Publish data to influxDB failed, no data found!".format(sys._getframe().f_code.co_name))
                    return False

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")

        return False

    def __readData__(self, name, value) -> bool:
        """Reads the data form the EMS-ESP and ESP Gasmeter device """
        try:
            if(name == ESP32_GASMETER_FIELDS):

                log.debug("{}: Read Data started".format(sys._getframe().f_code.co_name))

                # calc the value from the gasmeter (current total value for the current year)
                self.gasvalue = value

                # get the info from the ems-esp device
                if EMS_API_URL:
                    response = utils.getResponse(EMS_API_URL)
                    if response.status_code != 200:
                        log.warning("{}: Read Data Error {}".format(sys._getframe().f_code.co_name, response.status_code))
                        return False
                else:
                    log.debug("{}:EMS API Service disabled".format(sys._getframe().f_code.co_name))
                    return False

                # decode the data from the ems-esp device
                if(response and response.text):
                    data = json.loads(response.text)
                    # start calculation and save data
                    if(self.emsheaterFilename and data):
                        # get the previous data
                        self.ready = self.__loadData__()
                        # new data
                        now = datetime.now()
                        self.curr_data['device'] = SMARTMETER_NAME
                        self.curr_data['id'] = SMARTMETER_ID

                        self.curr_data['heater_active'] = data['heatingactive']
                        self.curr_data['boiler_active'] = data['ww3wayvalve']
                        self.curr_data['tapwater_active'] = data['tapwateractive']

                        self.curr_data['runnig_total_sec'] = (data['heatworkmin']) * 60 + (data['wwworkm'] * 60)
                        self.curr_data['runnig_heater_sec'] = data['heatworkmin'] * 60
                        self.curr_data['runnig_boiler_sec'] = data['wwworkm'] * 60
                        self.curr_data['runnig_heater_ratio'] = round((data['heatworkmin'] * 60) / self.curr_data['runnig_total_sec'], 2)
                        self.curr_data['runnig_boiler_ratio'] = round((data['wwworkm'] * 60) / self.curr_data['runnig_total_sec'], 2)

                        self.curr_data['servicecodenumber'] = data['servicecodenumber']
                        self.curr_data['boiler_disinfecting'] = data['wwdisinfecting']
                        self.curr_data['boiler_disinfecting_sec'] = self.prev_data['boiler_disinfecting_sec']

                        if self.curr_data['boiler_disinfecting'] == "on":
                            # boiler disinfecting starts now
                            self.curr_data['boiler_disinfecting_start'] = now.strftime(DATEFORMAT_TIMESTAMP)
                            log.debug("{}:  boiler disinfecting starts now".format(sys._getframe().f_code.co_name))
                        else:
                            self.curr_data['boiler_disinfecting_start'] = self.prev_data['boiler_disinfecting_start']

                        if self.curr_data['boiler_disinfecting'] == "off" and self.prev_data['boiler_disinfecting'] == "on":
                            # boiler disinfecting ends now
                            log.debug("{}:  boiler disinfecting ends now".format(sys._getframe().f_code.co_name))
                            self.curr_data['boiler_disinfecting_end'] = now.strftime(DATEFORMAT_TIMESTAMP)
                            date1 = datetime.strptime(self.curr_data['boiler_disinfecting_start'], DATEFORMAT_TIMESTAMP)
                            date2 = datetime.strptime(self.curr_data['boiler_disinfecting_end'], DATEFORMAT_TIMESTAMP)
                            diff = date2 - date1
                            # increment the running time for boiler disinfecting
                            self.curr_data['boiler_disinfecting_sec'] = self.curr_data['boiler_disinfecting_sec'] + int(diff.total_seconds())
                        else:
                            self.curr_data['boiler_disinfecting_end'] = self.prev_data['boiler_disinfecting_end']

                        self.curr_data['burngas'] = data['burngas']
                        self.curr_data['gas_total'] = round(value, 3)
                        self.curr_data['gas_heater'] = round(value * self.curr_data['runnig_heater_ratio'], 3)
                        self.curr_data['gas_boiler'] = round(value * self.curr_data['runnig_boiler_ratio'], 3)
                        self.curr_data['lasterror'] = data['lastcode']
                        bValid = self.__calcData__()
                        self.curr_data['dattime'] = time.ctime()
                        self.curr_data['datperiode'] = now.strftime(DATEFORMAT_DAY)
                        self.curr_data['datmonth'] = now.strftime(DATEFORMAT_MONTH)
                        self.curr_data['datyear'] = now.strftime(DATEFORMAT_YEAR)
                        self.curr_data['dattimestamp'] = now.strftime(DATEFORMAT_TIMESTAMP)
                        self.curr_data['datlastupdate'] = now.strftime(DATEFORMAT_CURRENT)
                        self.curr_data['datlastrun'] = self.lastRun.strftime(DATEFORMAT_TIMESTAMP)
                        self.curr_data['version'] = APPS_VERSION
                        self.curr_data['hostname'] = DATA_HOSTNAME
                        self.curr_data['unit_of_measurement'] = 'm³'
                        self.curr_data['state_class'] = 'measurement'
                        self.curr_data['device_class'] = 'gas'
                        self.curr_data['attribution'] = DATA_PROVIDER
                        # publish and save the data
                        self.__publishData__()
                        self.__saveData__()
                        # pubish data every hour to the influxdb every 10 min
                        # if(self.__getElapsedTime__(self.lastRun) >= 10):
                        self.__publishToInfluxdb__()
                        # save this for each month
                        self.__saveReportData__()
                        # all well done
                        self.runcount += 1
                        self.lastRun = datetime.now()
                        return self.ready
                    else:
                        log.debug("{}:EMS API - No data found !".format(sys._getframe().f_code.co_name))

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False
