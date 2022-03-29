#!/usr/bin/python3
# -*- coding":" utf-8 -*-

from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

# ------------------------------------------------------------------
# Simple testcase for rest api calls
# ------------------------------------------------------------------
import requests
import asyncio
import signal

from conf import *
from lib import utils
from lib import logger


# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


class devicedata():
    """simple heartbeat data class"""
    status = "offline"
    field = ""
    last = -1.00
    modified = 0
    time = datetime.min
    lastcall = datetime.min
    logInfo = False
    heartBeatTime = int(SMARTMETER_DEVICE["heartbeatTime"])
    runCounter = 0
    deviceversion = ""
    device_info = ""
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
    if payload["lasterror"]=="":
        log.warning("heartBeat: {}, {}".format(payload["status"], payload["runnigtime"],payload["lasterror"]))
    else:
        log.warning("heartBeat DEVICE ERROR: {}".format(payload))

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

    # reset / init the devicedata on start
    devicedata.modified = 0
    devicedata.runCounter = 0
    devicedata.lastError = ""

    while True:
        try:

            log.newLine()
            log.debug("Read data from {}".format(SMARTMETER_DEVICE))

            data = utils.getESBHomeData(SMARTMETER_DEVICE["url"],SMARTMETER_DEVICE["platform"],SMARTMETER_DEVICE["itemid"])

            if data["state"] == "Error":
                devicedata.status = "offline"
                log.warning("STATUS: {}".format(data["responsemessage"]))
                devicedata.lastError = "Device not ready..."
                log.warning("{}: Read Data Error {}".format(sys._getframe().f_code.co_name, data["responsecode"]))
            else:
                devicedata.status = "online"
                devicedata.lastError = ""
                ## {"id":"text_sensor-gasmeterdata","value":"29246.434|0.000|2022-03-29T14:15:44","state":"29246.434|0.000|2022-03-29T14:15:44"}
                if data and data["value"]:
                    results = __espdata__( data["value"] )
                    if devicedata.last != results.displayvalue and results.displayvalue > 0:
                        skipCalc = devicedata.last > 0
                        devicedata.modified += 1
                        devicedata.field = data["field"]
                        devicedata.last = results.displayvalue
                        devicedata.time = datetime.now()
                        if skipCalc==False:
                            log.debug("Data for {} {}, {} has changed !".format( data["field"], results.displayvalue, devicedata.time))
                        else:
                            log.debug("Start calulation with {} {}, {} has changed !".format( data["field"], results.displayvalue, devicedata.time))
                    else:
                        log.debug("Data for {} {}, {} has not changed".format( data["field"], results.displayvalue, devicedata.time))

                    if(results.displayvalue  == -1):
                        devicedata.status = "offline"
                        devicedata.lastError=data["responsemessage"]
                else:
                    devicedata.lastError = "No data"

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
            # fatal error message to gotify !
            devicedata.status = "offline"
            devicedata.lastError = str(e)
            break


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(heartBeat())
    asyncio.ensure_future(getData())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        devicedata.status = "offline"
        print("Received KeyboardInterrupt, shutting down...")
        loop.stop()
        pass
    finally:
        devicedata.status = "offline"
        sendHeartBeatData()
        loop.close()
