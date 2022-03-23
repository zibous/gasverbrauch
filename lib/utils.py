#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import string
from uptime import uptime


def dumps(o):
    """helper method to convert dictionary to object
    """
    return json.dumps(o, sort_keys=True, indent=4)


def savefile(content, datatype: str = 'json', filename: str = None) -> bool:
    """save the content to the defined file based on the datatype"""
    if not content:
        return False
    if filename and datatype:
        try:
            with open(filename, 'w') as f:
                if datatype == 'json':
                    f.write(json.dumps(content, sort_keys=False, indent=4, ensure_ascii=False))
                if datatype == 'text':
                    f.write(content)
            return True
        except BaseException as e:
            return False
    return False


def loadjsondata(filename: str = None):
    """load the json data from the defined file"""
    try:
        if filename:
            if os.path.isfile(filename):
                with open(filename, "r") as f:
                    return json.load(f)
            return None
    except BaseException as e:
        return None


def up_time() -> string:
    """calculates the uptime"""
    total_seconds = uptime()
    # Helper vars:
    MINUTE = 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24
    # Get the days, hours, etc:
    days = int(total_seconds / DAY)
    hours = int((total_seconds % DAY) / HOUR)
    minutes = int((total_seconds % HOUR) / MINUTE)
    seconds = int(total_seconds % MINUTE)
    # Build up the pretty output (like this: "N days, N hours, N minutes, N seconds")
    output = ""
    if days > 0:
        output += str(days) + " " + (days == 1 and "day" or "days") + ", "
    if len(output) > 0 or hours > 0:
        output += str(hours) + " " + (hours == 1 and "hour" or "hours") + ", "
    if len(output) > 0 or minutes > 0:
        output += str(minutes) + " " + (minutes == 1 and "minute" or "minutes") + ", "
    output += str(seconds) + " " + (seconds == 1 and "second" or "seconds")
    return output


def round_digits(x: float = 0.00, decimal_places: int = 2) -> float:
    """helper to round a number based on the decimal places"""
    return round(x, decimal_places)


def round_3digits(x: float = 0.00) -> float:
    """helper to round a number to 3 digits"""
    return round(x, 3)


def addNumber(field1: float = 0.00, field2: float = 0.00) -> float:
    """helper to add to numbers"""
    result = round(float(field1) + float(field2), 3)
    return float(result)


def substructNumber(field1: float = 0.00, field2: float = 0.00) -> float:
    """helper to substract a number"""
    result = round(float(field1) - float(field2), 3)
    return float(result)


def divideNumber(field1: float = 0.00, field2: float = 0.00) -> float:
    """helper to get the result for divide"""
    if field2 > 0.00:
        result = round(float(field1) / float(field2), 3)
        return float(result)
    return 0.00

def calcTotal(field1: float = 0.00, field2: float = 0.00, field3: float = 0.00) -> float:
    """calcs the total for the defined fields"""
    result = round(float(field1) + float(field2) - float(field3), 3)
    return float(result)


def remove_umlaut(string) -> string:
    """
    Removes umlauts from strings and replaces them with the letter+e convention
    :param string: string to remove umlauts from
    :return: unumlauted string
    """
    u = 'ü'.encode()
    U = 'Ü'.encode()
    a = 'ä'.encode()
    A = 'Ä'.encode()
    o = 'ö'.encode()
    O = 'Ö'.encode()
    ss = 'ß'.encode()
    string = string.encode()
    string = string.replace(u, b'ue')
    string = string.replace(U, b'Ue')
    string = string.replace(a, b'ae')
    string = string.replace(A, b'Ae')
    string = string.replace(o, b'oe')
    string = string.replace(O, b'Oe')
    string = string.replace(ss, b'ss')
    string = string.decode('utf-8')
    return string
