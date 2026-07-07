#!/usr/bin/env python
"""J. Fehn 14.02.20 | Get Hue Lamps Infos
"""
from __future__ import print_function
import os
import sys
import argparse
import requests
import json

cs_api_key = ""
cs_bridge_ip = ""
cs_transport_mode = "http"

def get_lights():
    global s_light_res
    s_light_res = requests.get(""+cs_transport_mode+"://"+cs_bridge_ip+"/api/"+cs_api_key+"/lights")

def main():
    get_lights()
    response = s_light_res.content.decode("utf-8")
    response = response[:-1]
    response = response[5:]
    print(response)

main()

