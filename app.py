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

sys.path.append("..")

# simple check if python 3 is used
if not (sys.version_info.major == 3 and sys.version_info.minor >= 5):
    print("This script requires Python 3.5 or higher!")
    print("You are using Python {}.{}.".format(sys.version_info.major, sys.version_info.minor))
    sys.exit(1)

# all requirements packages
try:
    import aioesphomeapi
    import asyncio
    import paho.mqtt.publish as publish
except Exception as e:
    print('Import error {}, check requirements.txt'.format(e))

# all private libs
try:
    from lib import logger
    from lib import gotifymessage as gotify
    from lib import calculator
    from lib import discoveryitems
    import paho.mqtt.publish as publish

    from conf import *
except Exception as e:
    print('Configuration error {}, check config.py'.format(e))
    sys.exit(1)

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


def publishMqtt(topic: str = '', payload: str = '', retain: bool = False) -> bool:
    """publish the mqtt payload to the defined brocker"""
    try:
        publish.single(topic, payload=payload, qos=0, retain=retain,
                       hostname=MQTTHOST, port=MQTTPORT,
                       client_id=MQTTCLIENT, keepalive=60, auth=MQTTAUTH)
        return True
    except BaseException as e:
        log.error(f"Error app.pbulishMqtt, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return False

# ---------------------------------------------------
# main application
# ---------------------------------------------------


async def main():
    """main application"""
    log.debug("Start main {}".format(APPS_NAME))

    # send the start message to gotify
    gotify.sendMessage(APPS_NAME, "start: {} on {}".format(DATA_HOSTNAME, getTimestamp()))

    # publish the ha discovery items
    if GASMETER_HA_DISCOVERY_TOPIC:
        discoveryitems.publish_ha_discovery()

    # get the calculator class
    _calculator = calculator.Calculator()

    # send last will if MQTT is definded
    if MQTTHOST:
        # mqtt brocker defined, send LWT Topic
        if MQTT_LWT_TOPIC:
            publishMqtt(topic=MQTT_LWT_TOPIC, payload="Online", retain=True)
        if MQTT_CHECK_LWT_TOPIC:
            publishMqtt(topic=MQTT_CHECK_LWT_TOPIC, payload="Online", retain=True)

    """Connect to an ESPHome device and wait for state changes."""
    cli = aioesphomeapi.APIClient(ESP32_GASMETER_API, ESP32_GASMETER_PORT, ESP32_GASMETER_PASSWORD)

    await cli.connect(login=True)
    sensors, services = await cli.list_entities_services()
    sensor_by_keys = dict((sensor.key, sensor.name) for sensor in sensors)

    def cb(state):
        """callback function to get the sensor values and if fieldname match - start the caclulation"""
        if isinstance(state, aioesphomeapi.SensorState):
            fieldName = sensor_by_keys[state.key]
            if(fieldName == ESP32_GASMETER_FIELDS):
                # execute the calculation
                log.debug("{}-state : Start new calculation with key {}".format(APPS_NAME, fieldName))
                # call calculater with the file gascounter_total and the gasmeter total value
                _calculator.__readData__(name=fieldName, value=state.state)
                log.debug("{}-state: End calculation".format(APPS_NAME))
            else:
                # store the others to the global dictionary
                ESP32_API_DATA[fieldName.replace(" ", "_").lower()] = state.state

            log.debug("{}-state: aioesphomeapi Field {}".format(APPS_NAME,fieldName))

    ## subscribe the callback function
    await cli.subscribe_states(cb)

# start main application
log.info(" ❖ {} started".format(APPS_DESCRIPTION))
loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(main())
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
     # send last will if MQTT is definded
    if MQTTHOST:
        # mqtt brocker defined, send LWT Topic
        if MQTT_LWT_TOPIC:
            publishMqtt(topic=MQTT_LWT_TOPIC, payload="Offline", retain=True)
        if MQTT_CHECK_LWT_TOPIC:
            publishMqtt(topic=MQTT_CHECK_LWT_TOPIC, payload="Offline", retain=True)
    # send the stop message to gotify
    gotify.sendMessage(APPS_NAME, "stoped: {} on {}".format(DATA_HOSTNAME, getTimestamp()))
    loop.close()

# end main application
