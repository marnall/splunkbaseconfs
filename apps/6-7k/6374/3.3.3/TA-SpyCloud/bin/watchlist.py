""" watchlist.py

DEPRECATED

Splunk scripted input which downloads and outputs latest Spycloud watchlist hits.

THIS SCRIPTED INPUT HAS BEEN REPLACED BY A MODULAR INPUT SpyCloud_Watchlist

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

    message = "The scripted input for SpyCloud watchlist is no longer used. Please disable it"
    common.make_error_message(message, session_key, "watchlist.py")
    sys.exit(0)

if __name__ == "__main__":
    main()
