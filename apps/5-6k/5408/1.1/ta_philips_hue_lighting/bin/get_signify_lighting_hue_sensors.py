#!/usr/bin/env python
"""J. Fehn 14.02.20 | Get Hue Sensor Infos
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

def get_sensors():
    global s_sensor_res
    s_sensor_res = requests.get(""+cs_transport_mode+"://"+cs_bridge_ip+"/api/"+cs_api_key+"/sensors")

def main():
    get_sensors()
    response = s_sensor_res.content.decode("utf-8")
    response = response[:-1]
    response = response[5:]
    print(response)

main()

