""" identifiers.py

DEPRECATED

Splunk scripted input which downloads and outputs stats for each watchlist identifier.

THIS SCRIPTED INPUT HAS BEEN REPLACED BY A MODULAR INPUT SpyCloud_Watchlist_Identifiers

"""
from collections import OrderedDict
import json
import sys
from datetime import datetime

from requests import HTTPError
import api
import common


def main():
    session_key = common.get_session_key()

    message = "The scripted input for SpyCloud identifiers is no longer used. Please disable it"
    common.make_error_message(message, session_key, "identifiers.py")
    sys.exit(0)

if __name__ == "__main__":
    main()
