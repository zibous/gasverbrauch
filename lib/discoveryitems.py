#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import json
import os
import string
import os.path
from uuid import uuid4
import paho.mqtt.publish as publish

from lib import logger
from conf import *

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


def __publishitem__(topic_name, type, counter, payload) -> bool:
    """mqtt publish discovery item"""

    try:
        topic = "{}/{}/{}/{}/config".format(GASMETER_HA_DISCOVERY_TOPIC, type, GASMETER_HA_SECTION, topic_name)
        log.debug("{}: Publish {}".format(sys._getframe().f_code.co_name, topic))
        if MQTTHOST:
            # mqtt brocker defined, send LWT Topic
            publish.single(topic, payload=json.dumps(payload, ensure_ascii=False), qos=0, retain=True,
                           hostname=MQTTHOST, port=MQTTPORT, client_id=MQTTCLIENT, keepalive=60, auth=MQTTAUTH)
            if GASMETER_HA_DISCOVERY_SAVE:
                # optional used to control the discovery item
                ha_file = "{}ha/{}/{}-{}.json".format(DATADIR, type, counter, topic_name)
                with open(ha_file, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
        else:
            log.debug("{} Payload for MQTT: {}".format(sys._getframe().f_code.co_name, payload))

    except BaseException as e:
        log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return False


def publish_ha_discovery():
    """publish all ha discovery items for the gasmeter values based on the configuration settings"""

    try:
        if os.path.isfile(GASMETER_HA_DISCOVERY_ITEMS):
            # valid setting found, open the file
            log.debug("{}: Loading file {}".format(sys._getframe().f_code.co_name, GASMETER_HA_DISCOVERY_ITEMS))
            with open(GASMETER_HA_DISCOVERY_ITEMS, 'r', encoding='utf-8') as fp:
                sensordata = json.load(fp)
            # all sensors
            isFristBinary = True
            isFirstSensor = True
            intCounter = 1
            for o in sensordata:
                # check enabeld flag
                if(int(o["enabled"] == 1)):
                    # build the payload based on the attributes for the selected item
                    name = "{} {}".format(GASMETER_HA_ITEM_PREFIX, o["name"])
                    uqId = "{}-{}".format(SMARTMETER_ID.lower(), o["field"].replace("_", "-"))
                    val_tpl = "{{{{value_json.{}}}}}".format(o["field"])
                    if isFristBinary == True and (o["type"] == "binary_sensor"):
                        payload = {
                            "~": MQTT_BASETOPIC,
                            "uniq_id": uqId,
                            "stat_t": "~/gas_data",
                            "name": name,
                            "val_tpl": val_tpl,
                            "payload_on": "on",
                            "payload_off": "off",
                            "dev": {
                                "sa": "Heizung",
                                "ids": [GASMETER_HA_DISCOVERY_ID],
                                "name": GASMETER_HA_DISCOVERY_ID.replace("-", " "),
                                "mf": SMARTMETER_MANUFATURER,
                                "mdl": SMARTMETER_MODEL,
                                "sw": APPS_VERSION,
                                "via_device": GASMETER_HA_DISCOVERY_ID.lower()
                            }
                        }
                        isFristBinary = False
                    elif isFirstSensor == True and (o["type"] == "sensor"):
                        payload = {
                            "~": MQTT_BASETOPIC,
                            "uniq_id": uqId,
                            "stat_t": "~/gas_data",
                            "name": name,
                            "val_tpl": val_tpl,
                            "dev": {
                                "sa": "Heizung",
                                "ids": [GASMETER_HA_DISCOVERY_ID],
                                "name": GASMETER_HA_DISCOVERY_ID.replace("-", " "),
                                "mf": SMARTMETER_MANUFATURER,
                                "mdl": SMARTMETER_MODEL,
                                "sw": APPS_VERSION,
                                "via_device": GASMETER_HA_DISCOVERY_ID.lower()
                            }
                        }
                        isFirstSensor = False
                    else:

                        if (o["type"] == "binary_sensor"):
                            payload = {
                                "~": MQTT_BASETOPIC,
                                "uniq_id": uqId,
                                "stat_t": "~/gas_data",
                                "name": name,
                                "val_tpl": val_tpl,
                                "payload_on": "on",
                                "payload_off": "off",
                                "dev": {
                                    "ids": [GASMETER_HA_DISCOVERY_ID],
                                }
                            }
                        if (o["type"] == "sensor"):
                            payload = {
                                "~": MQTT_BASETOPIC,
                                "uniq_id": uqId,
                                "stat_t": "~/gas_data",
                                "name": name,
                                "val_tpl": val_tpl,
                                "dev": {
                                    "ids": [GASMETER_HA_DISCOVERY_ID],
                                }
                            }
                    if o["unit"] != "":
                        payload['unit_of_meas'] = o["unit"]
                    if o["class"] != "":
                        payload['state_class'] = o["class"]
                    if o["icon"] != "":
                        payload['icon'] = o["icon"]
                    if ("device_class" in o):
                        if o["device_class"] != "":
                            payload['device_class'] = o["device_class"]

                    # publish item
                    topic_name = "{}".format(o["field"].replace(".", "_").lower())
                    __publishitem__(topic_name, o["type"], intCounter, payload)

                    intCounter += 1

            # all well done

        return True

    except BaseException as e:
        log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return False
