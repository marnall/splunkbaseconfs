#!/usr/bin/python

import sys
import time

def parse_time(str):
    try:
        t = time.strptime(str, "%Y-%m-%d %H:%M:%S")
        return long(time.mktime(t)) * long(1e9)
    except ValueError, e:
        pass
    try:
        ns = long(str)
    except Exception, e:
        sys.stderr.write("Invalid time `%s'" % str)
        sys.exit(1)
    if ns < 0x7fffffff:
        return ns * long(1e9)
    return ns
