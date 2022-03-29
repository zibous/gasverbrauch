#!/usr/bin/python3
# -*- coding":" utf-8 -*-

# ------------------------------------------------------------------
# Service gasmeter - calculate the gas consumption data
# ------------------------------------------------------------------
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Distribution License
# which accompanies this distribution.
#
# Contributors:
#    Peter Siebler - initial implementation
#
# Copyright (c) 2022 Peter Siebler
# All rights reserved.
# ------------------------------------------------------------------

import sys

# simple check if python 3 is used
if not (sys.version_info.major == 3 and sys.version_info.minor >= 5):
    print("This script requires Python 3.5 or higher!")
    print("You are using Python {}.{}.".format(sys.version_info.major, sys.version_info.minor))
    sys.exit(1)

# all requirements packages
try:
    import requests
    import asyncio
    import json
    import paho.mqtt.publish as publish

except Exception as e:
    print('Import error {}, check requirements.txt'.format(e))

# all private libs
try:
    from lib import logger
    from lib import gotifymessage as gotify
    from lib import calculator
    from lib import discoveryitems
    from lib import utils
    from conf import *
except Exception as e:
    print('Configuration error {}, check config.py'.format(e))
    sys.exit(1)

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR, LOG_SHOWLINES)

def publishMqtt(topic: str = '', payload: str = '', retain: bool = False) -> bool:
    """publish the mqtt payload to the defined brocker"""
    try:
        publish.single(topic, payload=payload, qos=0, retain=retain,
                       hostname=MQTTHOST, port=MQTTPORT,
                       client_id=MQTTCLIENT, keepalive=60, auth=MQTTAUTH)
        return True
    except BaseException as e:
        log.error(f"Error app.pbulishMqtt, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        devicedata.lastError = str(e)
        return False

def publishLWTMessage(payload:str="Offline"):
    if MQTTHOST:
        # mqtt brocker defined, send LWT Topic
        if MQTT_LWT_TOPIC:
            publishMqtt(topic=MQTT_LWT_TOPIC, payload=payload, retain=True)
        if MQTT_CHECK_LWT_TOPIC:
            publishMqtt(topic=MQTT_CHECK_LWT_TOPIC, payload=payload, retain=True)


# ---------------------------------------------------
# heartBeat application
# ---------------------------------------------------
class devicedata():
    """ all for the device """
    status = "offline"
    field = ""
    last = 0.00
    modified = 0
    time =  datetime.min
    lastcall = datetime.min
    logInfo = False
    heartBeatTime = 10
    runCounter = 0
    deviceversion = APPS_VERSION
    device_info = SMARTMETER_ID
    lastError = "None"

def sendHeartBeatData():
    """send heartbeat data"""
    devicedata.runCounter += 1
    delta = datetime.now() - devicedata.time
    payload = {
        "name": devicedata.field,
        "state": round(devicedata.last, 3),
        "status": devicedata.status,
        "modified": devicedata.modified,
        "counter": devicedata.runCounter,
        "elapsed": int(delta.total_seconds()),
        "runnigtime": utils.runningTime(delta.total_seconds()),
        "lastcall": devicedata.lastcall.strftime(DATEFORMAT_TIMESTAMP),
        "timedata": devicedata.time.strftime(DATEFORMAT_TIMESTAMP),
        "timestamp": datetime.now().strftime(DATEFORMAT_TIMESTAMP),
        "lasterror": devicedata.lastError,
        "deviceversion": devicedata.deviceversion,
        "deviceInfo": devicedata.device_info,
        "hostname": DATA_HOSTNAME
    }
    if MQTT_CHECK_HEARTBEAT_TOPIC:
        publishMqtt(topic=MQTT_CHECK_HEARTBEAT_TOPIC, payload=json.dumps(payload, ensure_ascii=False), retain=False)
    if payload["lasterror"]=="":
        log.debug("heartBeat: {}, {}".format(payload["status"], payload["runnigtime"],payload["lasterror"]))
        publishLWTMessage(payload="Online")
    else:
        log.warning("heartBeat DEVICE ERROR: {}".format(payload))
        ## publish lwt message
        publishLWTMessage(payload="Offline")
        gotify.sendMessage(APPS_NAME, "Error: {} on {}, {}".format(DATA_HOSTNAME, getTimestamp(),devicedata.lastError))

async def heartBeat():
    """simple heartbeat"""
    try:
        while True:
            await asyncio.sleep(devicedata.heartBeatTime)
            sendHeartBeatData()

    except BaseException as e:
        log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        devicedata.lastError = str(e)


async def getData():
    """Connect to an ESPHome device and wait for state changes."""

    log.debug("Start main {}".format(APPS_NAME))

    class __espdata__():
        """data values from the esp device"""
        displayvalue= -1.00
        totalvalue = 0.000
        timestamp = datetime.min
        def __init__(self, data: str = ''):
            """constructor espdata class"""
            if data:
                items = data.split("|")
                self.displayvalue = utils.fix_float(float(items[0]))
                self.totalvalue = utils.fix_float(float(items[1]))
                self.timestamp = items[2]    ## 2022-03-29T14:15:44

    # send the start message to gotify
    gotify.sendMessage(APPS_NAME, "start: {} on {}".format(DATA_HOSTNAME, getTimestamp()))

    # publish the ha discovery items
    if GASMETER_HA_DISCOVERY_TOPIC:
        discoveryitems.publish_ha_discovery()

    # get the calculator class
    _calculator = calculator.Calculator()

    # send last will if MQTT is definded
    publishLWTMessage(payload="Online")

    # reset / init the devicedata on start
    devicedata.modified = 0
    devicedata.runCounter = 0
    devicedata.lastError = ""

    while True:
        try:
            log.newLine()
            log.debug("Read data from {}".format(SMARTMETER_DEVICE))
            # first get the esp gasmeter values
            data = utils.getESBHomeData(SMARTMETER_DEVICE["url"],SMARTMETER_DEVICE["platform"],SMARTMETER_DEVICE["itemid"])
            # check the response from the gasmeter device
            if data["state"] == "Error":
                devicedata.status = "offline"
                log.warning("STATUS: {}".format(data["responsemessage"]))
                devicedata.lastError = "Device not ready..."
                log.warning("{}: Read Data Error {}".format(sys._getframe().f_code.co_name, data["responsecode"]))
            else:
                # data from the gasmeter device ready
                devicedata.status = "online"
                devicedata.lastError = ""
                if data and data["value"]:
                    results = __espdata__( data["value"] )
                    ## the gascounter display value
                    ESP32_API_DATA['wug_gaszähler_anzeige'] = results.displayvalue
                    ## the gascounter total value current year
                    ESP32_API_DATA['wug_gasverbrauch_gesamt'] = results.totalvalue
                    ## the last timestamp from the gascounter
                    ESP32_API_DATA['wug_timestamp'] = results.timestamp
                    # check if the gasmeter display value has changed
                    if devicedata.last != results.totalvalue and results.totalvalue > 0:
                        devicedata.modified += 1
                        devicedata.field = data["field"]
                        devicedata.last = results.totalvalue
                        devicedata.time = datetime.now()
                        log.info("Start calulation with {} {}, {} has changed !".format( data["field"], results.totalvalue, devicedata.time))
                        _calculator.__readData__(name=ESP32_GASMETER_FIELDS, value=results.totalvalue)
                    else:
                        log.debug("Data for {} {}, {} has not changed".format( data["field"], results.totalvalue, devicedata.time))
                else:
                    devicedata.lastError = "No data found !"

            ## wait for the next call
            await asyncio.sleep(devicedata.heartBeatTime)

        except KeyboardInterrupt:
            break
        except requests.exceptions.Timeout:
            log.error(f"ERROR Timeout: {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            devicedata.status = "offline"
            devicedata.lastError = "Device http timeout"
        except requests.exceptions.HTTPError as e:
            log.error(f"ERROR HTTP: {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            devicedata.status = "offline"
            devicedata.lastError = str(e)
        except requests.exceptions.RequestException as e:
            log.error(f"ERROR RequestException: {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            devicedata.status = "offline"
            devicedata.lastError = str(e)
        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            devicedata.status = "offline"
            devicedata.lastError = str(e)
            break


# ---------------------------------------------------
# main application
# ---------------------------------------------------
if __name__ == '__main__':
    log.info(" ❖ {} started".format(APPS_DESCRIPTION))
    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(getData())
        asyncio.ensure_future(heartBeat())
        loop.run_forever()
    except KeyboardInterrupt:
        devicedata.status = "offline"
        print("Received KeyboardInterrupt, shutting down...")
        loop.stop()
        pass
    finally:
        # send last will if MQTT is definded
        publishLWTMessage(payload="Offline")
        # send the stop message to gotify
        gotify.sendMessage(APPS_NAME, "stoped: {} on {}".format(DATA_HOSTNAME, getTimestamp()))
        devicedata.status = "offline"
        sendHeartBeatData()
        loop.close()

# end main application
