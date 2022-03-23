#!/usr/bin/python3
# -*- coding":" utf-8 -*-

import sys

# all requirements packages
try:
    from xmlrpc.client import boolean
    import requests
    import json
    import time
    import os
    import os.path
    from datetime import datetime
    import paho.mqtt.publish as publish

    from lib import gotifymessage as gotify
    from lib import logger
    from conf import *

except Exception as e:
    print('Configuration error {}, check config.py'.format(e))
    sys.exit(1)

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


class Calculator():
    """Calculater class calcs all value for the current gasmeter values based on EMS-ESP and Gasmeter ESP Device"""

    version = "1.1.0"

    def __init__(self):
        log.debug('✔︎ Init {}, version {}'.format(__name__, self.version))
        self.emsheaterFilename = "{}gb172.json".format(DATADIR)
        self.prev_data = {}
        self.curr_data = {}
        self.ready = False

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
            lastDate = datetime.strptime(self.prev_data['dattimestamp'], DATEFORMAT_TIMESTAMP)
            newDate = datetime.now()
            diff = newDate - lastDate
            self.curr_data['elapsed_time'] = int(diff.total_seconds())
            # all periodes
            for key in DATE_LIST:
                format = DATE_LIST[key]
                if(self.__checkTimeOrDate__(format, False)):
                    # reset or init value
                    if not (key in self.curr_data):
                        self.curr_data[key] = {}

                    log.debug("{}: Init values for {}, new period found !".format(sys._getframe().f_code.co_name, key))

                    # init values if date or time has changed
                    self.curr_data[key]['boiler'] = round(float(0), 3)
                    self.curr_data[key]['heater'] = round(float(0), 3)
                    self.curr_data[key]['disinfecting'] = round(float(0), 3)

                    # update values based on the mode
                    if self.curr_data['gasverbrauch_boiler']:
                        self.curr_data[key]['boiler'] = self.curr_data['gasverbrauch_boiler']

                    if self.curr_data['gasverbrauch_heater']:
                        self.curr_data[key]['heater'] = self.curr_data['gasverbrauch_heater']

                    if self.curr_data['boiler_disinfecting'] == "on":
                        self.curr_data[key]['disinfecting'] = self.curr_data['gasverbrauch_boiler']
                else:
                    # add new values
                    log.debug("{}: update values for {}".format(sys._getframe().f_code.co_name, key))
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
                self.curr_data['gasverbrauch_boiler'] = round(float(0), 3)
                self.curr_data['gasverbrauch_heater'] = round(float(0), 3)
                # check boiler or heater mode
                if(self.curr_data['boiler_active'] == 'on'):
                    self.curr_data['mode'] = EMS_MODES['water']
                else:
                    if(self.curr_data['heater_active'] == 'on'):
                        self.curr_data['mode'] = EMS_MODES['heat']
                # get the gas consumption
                gas_delta = float((self.curr_data['gas_total'] - self.prev_data['gas_total']))
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
                self.prev_data['gas_total'] = round(float(0), 3)
                for key in DATE_LIST:
                    self.prev_data[key] = {}
                    self.prev_data[key]['boiler'] = round(float(0), 3)
                    self.prev_data[key]['heater'] = round(float(0), 3)
                    self.prev_data[key]['disinfecting'] = round(float(0), 3)
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

    def __readData__(self, name, value) -> bool:
        """Reads the data form the EMS-ESP and ESP Gasmeter device """
        try:
            if(name == 'WUG Gasverbrauch gesamt'):

                log.debug("{}: Read Data started".format(sys._getframe().f_code.co_name))
                # calc the value from the gasmeter
                self.gasvalue = value

                # get the info from the ems-esp device
                if EMS_API_URL:
                    response = requests.get(EMS_API_URL)
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
                        self.curr_data['version'] = APPS_VERSION
                        self.curr_data['hostname'] = DATA_HOSTNAME
                        self.curr_data['unit_of_measurement'] = 'm³'
                        self.curr_data['state_class'] = 'measurement'
                        self.curr_data['device_class'] = 'gas'
                        self.curr_data['attribution'] = DATA_PROVIDER
                        # publish and save the data
                        self.__publishData__()
                        self.__saveData__()
                        # save this for each month
                        self.__saveReportData__()
                        # all well done
                        return self.ready
                    else:
                        log.debug("{}:EMS API - No data found !".format(sys._getframe().f_code.co_name))

        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False
