""" breach_catalog.py

DEPRECATED

Splunk scripted input which downloads and outputs latest Spycloud breaches.

THIS SCRIPTED INPUT HAS BEEN REPLACED BY A MODULAR INPUT SpyCloud_Breach_Catalog

"""
from collections import OrderedDict
import json
import os
import sys

from requests import HTTPError
import api
import common
from consts import APP_NAME


def main():
    session_key = common.get_session_key()

    message = "The scripted input for SpyCloud breach_catalog is no longer used. Please disable it"
    common.make_error_message(message, session_key, "breach_catalog.py")
    sys.exit(0)

if __name__ == "__main__":
    main()
