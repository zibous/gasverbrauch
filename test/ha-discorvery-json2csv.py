#!/usr/bin/python3
# -*- coding":" utf-8 -*-

# call: python3 ha-discorvery-json2csv.py

from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from pandas import json_normalize
from lib import utils

sys.path.append("..")

try:
    from lib import logger
    from lib import utils
except Exception as e:
    print('Import error {}, check requirements.txt'.format(e))

 # register the application logger
log = logger.Log(__name__, 10)

filename = "../data/HA-GB172BKG.json"
log.info("Read Filename: {}".format(filename))

data = utils.loadjsondata(filename)
df = json_normalize(data)

filename = filename.replace(".json", ".csv")
df.to_csv(filename, index=False)

log.info("Data Filename: {} ready".format(filename))

