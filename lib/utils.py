#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import math
import string
from uptime import uptime


def dumps(o) -> str:
    """helper method to convert dictionary to object
    """
    try:
        return json.dumps(o, sort_keys=True, indent=4)
    except BaseException as e:
        print(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return ""

def write_to_file(data: str, filepath: str) -> bool:
    try:
        with open(filepath, "w+") as f:
            f.write(data)
    except:
        raise Exception(f"Saving data to {filepath} encountered an error")

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


def loadjsondata(filename: str = None) -> dict:
    """load the json data from the defined file"""
    try:
        if filename:
            if os.path.isfile(filename):
                with open(filename, "r") as f:
                    data = json.load(f)
            return data
    except BaseException as e:
        print(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return None

def runningTime(total_seconds) -> str:
    try:
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
    except BaseException as e:
        print(f"Error {sys._getframe().f_code.co_name}, {str(e)}, {str(e)} line {sys.exc_info()[-1].tb_lineno}")
        return ""

def up_time() -> str:
    """calculates the uptime"""
    total_seconds = uptime()
    return (runningTime(total_seconds))

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

def fix_float(value: float) -> float:
    """Fix precision for single-precision floats and return what was probably
    meant as a float.
    Unfortunately the float representation of 0.1 converted to a double is not the
    double representation of 0.1, but 0.10000000149011612.
    This methods tries to round to the closest decimal value that a float of this
    magnitude can accurately represent.
    """
    if value == 0 or not math.isfinite(value):
        return value
    abs_val = abs(value)
    # assume ~7 decimals of precision for floats to be safe
    l10 = math.ceil(math.log10(abs_val))
    prec = 7 - l10
    return round(value, prec)


def remove_umlaut(string) -> str:
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

def generate_csv_data(data: dict) -> str:
    # Defining CSV columns in a list to maintain
    # the order
    csv_columns = data.keys()
    # Generate the first row of CSV
    csv_data = ",".join(csv_columns) + "\n"
    # Generate the single record present
    new_row = list()
    for col in csv_columns:
        new_row.append(str(data[col]))
    # Concatenate the record with the column information
    # in CSV format
    csv_data += ",".join(new_row) + "\n"
    return csv_data

def flatten_json(nested_json) -> string:
    """
        Flatten json object with nested keys into a single level.
        Args:
            nested_json: A nested json object.
        Returns:
            The flattened json object if successful, None otherwise.
    """
    out = {}
    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(nested_json)
    return out
