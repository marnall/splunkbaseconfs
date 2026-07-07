#!/usr/bin/env python

import os
import sys

try:
    from ConfigParser import RawConfigParser as cp
except ImportError:
    from configparser import RawConfigParser as cp

def main():
    confs = cp()
    confs.read([os.path.join(os.getenv('SPLUNK_HOME'),
                                 "etc/apps/NagiosOperationCenter/default/nagiosoc.conf"),
                os.path.join(os.getenv('SPLUNK_HOME'),
                                 "etc/apps/NagiosOperationCenter/local/nagiosoc.conf")])
    script = os.path.join(
            os.getenv('SPLUNK_HOME'),
            "etc/apps/NagiosOperationCenter/bin/dumpnagios")

    if confs.has_option('nagiosoc', 'path'):
        os.system("%s %s %s" % (script, confs.get('nagiosoc','path'), sys.argv[1]))

if __name__ == "__main__":
    main()
