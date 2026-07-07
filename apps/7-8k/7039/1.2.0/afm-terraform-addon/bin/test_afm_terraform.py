import sys
import os

import logging
import json
import datetime
import time
import re


import xml.dom.minidom

# Add the "./lib" directory to sys.path to enable import on Custom Libraries
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))
sys.path.append(os.path.join(os.path.dirname(__file__), "lib", "Terraform"))

import xmltodict

# Terraform Cloud Libraries
from TerraformRuns import TerraformRuns


if __name__ == "__main__":
    host         = "app.terraform.io"
    protocol     = "https"
    token        = "QBrLFeSgXXBcPA.atlasv1.W2LZRnnJqWgRt3OyHC2UYx8jIcdH0HImDyzjIEL4nAaruthHIF3B2ULo8TefO7OzFNY"
    workspace_id = "ws-9QeQkLPLESmnzk4z"

    terraformRuns = TerraformRuns(\
        hostname = host,\
        protocol = protocol,\
        token = token,\
        workspace_id = workspace_id)
    terraformRunsList = terraformRuns.list_runs()

    for event in terraformRunsList:
        print(event)