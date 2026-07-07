import hashlib
import re
import sys
import time
import os
import json


def _get_key_time_reversed(key):
    key_time = key[-10:][::-1]
    match_key = re.search('[a-zA-Z]', key_time)
    return key_time, match_key


def _calculate_sum(decimal_value):
    return sum([int(x) for x in str(int(decimal_value))])


def _validate_activation_key(app_name, key):
    try:
        key_time, match_key = _get_key_time_reversed(key)
        app_md = hashlib.md5(app_name.encode('utf-8')).hexdigest().upper()
        app_dec = int(app_md, 16)
        app_dec_sum = _calculate_sum(app_dec)
        key = key[:-10]
        vbits = key[:-32]
        key = key[-32:]
        dec = int(key, 16)
        li = [int(x) for x in str(int(dec))]
        s = sum(list(li))
        current_ts = time.time()

        if len(key) != 32 or match_key:
            log = "Activation Key mismatch or invalid characters detected."
            return log
        else:
            if current_ts - int(key_time) > 1296000:
                log = "Activation Key expired or incorrect. Please obtain a new one."
                return log
            if not int(s) + int(app_dec_sum) == int(vbits):
                log = "Activation Key mismatch. Please enter the correct key."
                return log
    except Exception:
        err = "Activation Key validation failed. Please enter the correct key."
        return err
