# -*- coding: utf-8 -*-
# !/usr/bin/env python

import ConfigParser
import sys
import os


CONFIG_FILE = 'blueliv.cfg'
SECTION_NAME_KEY = 'Actions'


def main():
    
    Config = ConfigParser.RawConfigParser(allow_no_value=True)
    Config.read(CONFIG_FILE)
    if not Config.has_section(SECTION_NAME_KEY):
        Config.add_section(SECTION_NAME_KEY)
    Config.set(SECTION_NAME_KEY, "reset", True)
    try:
        with open(CONFIG_FILE, 'wb') as configfile:
            Config.write(configfile)
        sys.stderr.write("ok")
    except:
        sys.stderr.write("error")

main()
