#!/usr/bin/python3
# -*- coding":" utf-8 -*-

import sys
sys.path.append("..")

try:
    import json
    from datetime import datetime
    from influxdb import InfluxDBClient

    from conf import *
    from lib import logger

except Exception as e:
    print('Import error {}, check requirements.txt'.format(e))

log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


class InfuxdbCient:

    version = "1.0.1"

    def __init__(self, database: str = INFLUXDB_NAME, host: str = INFLUXDB_HOST, port: int = INFLUXDB_PORT, user: str = INFLUXDB_USER, passwd: str = INFLUXDB_PASSWORD):
        self.database = database
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.measurement = "data"
        self.fields = None
        self.time = datetime.utcnow().strftime(DATEFORMAT_UTC)
        self.influxClient = None
        self.__connect__()

    def __connect__(self) -> bool:
        """connect tho the influx db"""
        try:
            log.debug(f"Connect to influxdb {self.host} database: {self.database}")
            self.influxClient = InfluxDBClient(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.passwd
            )
            return True
        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def post(self, fields, measurement: str = 'data', time: str = None) -> bool:
        """post the data to the influxdb"""
        try:
            if self.influxClient:
                self.measurement = measurement
                self.fields = fields
                if time:
                    self.time = time
                if self.measurement and self.fields:
                    log.debug(f"Post data to influxdb {self.host} database: {self.database}")
                    if INFLUXDB_LOG_DIR:
                        self.__savelogdata__(self.fields, self.measurement)
                    self.influxClient.write_points([{
                        "measurement": self.measurement,
                        "time": self.time,
                        "fields": self.fields
                    }], database=self.database)
                    return True
        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False

    def get(self, query: str = None):
        """get query data from the influxdb"""
        try:
            if self.influxClient and query:
                log.debug(f"Get data to influxdb {self.host} database: {self.database}")
                return self.influxClient.query(query)
        except BaseException as e:
            log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return None

    def __savelogdata__(self, data, measurement) -> bool:
        """ save the influx data to the definded log file"""
        if(INFLUXDB_LOG_DIR):
            if data and measurement:
                filename = INFLUXDB_LOG_DIR + measurement + '.json'
                try:
                    with open(filename, 'w') as f:
                        f.write(json.dumps(data, sort_keys=False, indent=4, ensure_ascii=False))
                    return True
                except BaseException as e:
                    log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
            return False
