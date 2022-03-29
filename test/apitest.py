#!/usr/bin/python3
# -*- coding":" utf-8 -*-

# ------------------------------------------------------------------
# Simple testcase for aioesphomeapi
# ------------------------------------------------------------------
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

import asyncio
import aioesphomeapi
from aioesphomeapi.api_pb2 import SubscribeLogsResponse

from lib.utils import fix_float
from lib import logger
from lib import utils
from conf import *

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)

class devicedata():
    """simple heartbeat data class"""
    status = "offline"
    field = ""
    last = 0.00
    modified = 0
    time = datetime.min
    lastcall = datetime.min
    logInfo = False
    heartBeatTime = 10
    runCounter = 0
    deviceversion = ""
    device_info = ""
    lastError = "None"

async def heartBeat():
    """simple heartbeat"""
    try:
        while True:
            await asyncio.sleep(devicedata.heartBeatTime)
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
            log.warning("heartBeat:{}".format(payload))

    except BaseException as e:
        log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        devicedata.lastError = str(e)


async def main():
    """Connect to an ESPHome device and wait for state changes."""
    try:
        log.debug("Start main {}".format(APPS_NAME))

        cli = aioesphomeapi.APIClient("wug2022.siebler.home", ESP32_GASMETER_PORT, ESP32_GASMETER_PASSWORD)
        await cli.connect(login=True)

       # reset / init the devicedata on start
        devicedata.last = 0
        devicedata.modified = 0
        devicedata.runCounter = 0
        devicedata.deviceversion = cli.api_version
        devicedata.device_info = await cli.device_info()

        sensors, services = await cli.list_entities_services()
        sensor_by_keys = dict((sensor.key, sensor.name) for sensor in sensors)

        def change_callback(state):
            """Print the state changes of the device."""
            log.warning(state)
            try:
                devicedata.status = "online"
                devicedata.field = ESP32_GASMETER_FIELDS
                devicedata.lastcall = datetime.now()

                if isinstance(state, aioesphomeapi.SensorState):
                    fieldName = sensor_by_keys[state.key]
                    fieldValue = utils.fix_float(state.state)
                    ## log.info("Check State for {} {} vs. {}".format(fieldName, fieldValue,devicedata.last))
                    if(fieldName == "WUG2 Gasverbrauch gesamt"):
                        if(fieldValue != devicedata.last):
                            log.info("----> State changed for {} {} previous:{}".format(fieldName, fieldValue,devicedata.last))
                            devicedata.modified += 1
                            devicedata.time = datetime.now()
                        else:
                            log.debug("Data for {} {}, {} has not changed".format(fieldName, fieldValue,devicedata.time))

                        devicedata.last = fieldValue
                    else:
                        if devicedata.logInfo:
                            log.debug("Data for {} {}, {}".format(fieldName, fieldValue, devicedata.time))
            except BaseException as e:
                log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
                devicedata.lastError = str(e)

        def log_callback(msg: SubscribeLogsResponse):
           time_ = datetime.now().time().strftime("[%H:%M:%S]")
           text = msg.message
           ## print(time_ + text.decode("utf8", "backslashreplace"))
           log.info(text.decode("utf8", "backslashreplace"))


        # Subscribe to the state changes
        await cli.subscribe_states(change_callback)

        # Subscribe to the logging messages
        await cli.subscribe_logs(log_callback, log_level=4)

    except BaseException as e:
        log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        devicedata.lastError = str(e)

loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(heartBeat())
    asyncio.ensure_future(main())
    loop.run_forever()
except KeyboardInterrupt:
    devicedata.status = "offline"
    print("Received KeyboardInterrupt, shutting down...")
    pass
finally:
    devicedata.status = "offline"
    loop.close()
