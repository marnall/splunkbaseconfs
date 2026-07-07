#!/usr/bin/env python

import os
execfile(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "PythonLibs.py")))

from splunk.clilib import cli_common as common

import requests
import sys

lookup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lookups"))

watchlist = sys.argv[1]

watchlistconf = common.getConfStanza("watchlists", watchlist)

filename = common.getConfStanza("transforms", watchlistconf["name"])["filename"]
outfile = os.path.join(lookup_dir, filename)
with open(outfile, "w") as f:
    if "header" in watchlistconf:
        f.write("{header}\n".format(**watchlistconf))
    f.write(requests.get(watchlistconf["url"]).content)
