#!/usr/bin/python3
# -*- coding":" utf-8 -*-

# ------------------------------------------------------------------
# Simple testcase for aioesphomeapi
# ------------------------------------------------------------------
import sys
sys.path.append("..")

from lib import logger
from conf import *
import time
import asyncio
import aioesphomeapi
from asyncio import constants


# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


class devicedata():
    last = 0.00
    time = datetime.now()
    logInfo = False
    heartBeatTime = 10
    runningTime = 0
    runCounter = 0

async def heartBeat():
    """simple heartbeat"""
    devicedata.time = datetime.now()
    while True:
        await asyncio.sleep(devicedata.heartBeatTime)
        devicedata.runCounter += 1
        delta = datetime.now() - devicedata.time
        payload = {
            "status": "connected",
            "lastvalue": round(devicedata.last, 3),
            "counter": devicedata.runCounter,
            "elapsed": int(delta.total_seconds()),
            "timedata": devicedata.time.strftime(DATEFORMAT_TIMESTAMP),
            "timestamp": datetime.now().strftime(DATEFORMAT_TIMESTAMP)
        }
        log.warning("heartBeat:{}".format(payload))


async def main():

    """Connect to an ESPHome device and wait for state changes."""
    log.debug("Start main {}".format(APPS_NAME))

    cli = aioesphomeapi.APIClient(ESP32_GASMETER_API, ESP32_GASMETER_PORT, ESP32_GASMETER_PASSWORD)

    await cli.connect(login=True)
    sensors, services = await cli.list_entities_services()
    sensor_by_keys = dict((sensor.key, sensor.name) for sensor in sensors)

    def change_callback(state):
        """Print the state changes of the device."""
        if isinstance(state, aioesphomeapi.SensorState):
            fieldName = sensor_by_keys[state.key]
            if(fieldName == ESP32_GASMETER_FIELDS):
                if(state.state != devicedata.last):
                    log.info("State changed for {} {}".format(fieldName, state.state))
                    devicedata.last = state.state
                    devicedata.time = datetime.now()
                else:
                    log.debug("Data for {} {}, {} has not changed".format(fieldName, state.state, devicedata.runningTime))
            else:
                if devicedata.logInfo:
                    log.debug("Data for {} {}, {}".format(fieldName, state.state, devicedata.runningTime))

    # Subscribe to the state changes
    await cli.subscribe_states(change_callback)


loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(heartBeat())
    asyncio.ensure_future(main())
    loop.run_forever()
except KeyboardInterrupt:
    print("Received KeyboardInterrupt, shutting down...")
    pass
finally:
    loop.close()
