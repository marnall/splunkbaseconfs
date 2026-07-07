#!/usr/bin/env python

from splunk.clilib import apps
import os
import sys

app_dir = apps.getAppPaths("PythonLibs")[1]
lib_dir = os.path.join(app_dir, "lib")

sys.path.append(lib_dir)
