
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import requests
from lib import logger
from conf import *

# register the application logger
log = logger.Log(__name__, LOG_LEVEL, LOG_DIR)


def sendMessage(title: str = GOTIFY_TITLE, message: str = "", priority: int = 2) -> bool:
    """publish the message to the Gotify Server"""
    try:
        if GOTIFY_SERVICE and GOTIFY_TOKEN:
            url = "{}message?token={}".format(GOTIFY_SERVICE, GOTIFY_TOKEN)
            resp = requests.post(url, json={
                "message": message,
                "priority": priority,
                "title": title
            })
            if(resp.status_code != 200):
                log.warning("{}: Fatal Error - Errorcode: {} ".format(sys._getframe().f_code.co_name, resp.status_code))
            else:
                log.debug("{}: Meldung {} send!".format(sys._getframe().f_code.co_name, GOTIFY_TITLE))
            return resp.status_code == 200
        else:
           log.debug("{}: Gotify Service disabled".format(sys._getframe().f_code.co_name))

    except BaseException as e:
        log.error(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return False
