#!/usr/bin/env python
# encoding = utf-8

'''
' Riverbed Community (https://community.riverbed.com)
'
' input_module_cacontroller_endpoints_stats.py
' 
' Riverbed Community Add-On for Splunk
' version: 1.2.210510
'
' Encoding: UTF8
' End of Line Sequence: LF
'
' Description
'
'     Client Accelerator Endpoints stats events collector for Splunk
'     Based on SteelScript service framework (https://github.com/riverbed/steelscript) to connect to the REST API of the of a Client Accelerator Controller appliance
'
' Copyright (c) 2021 Riverbed Technology, Inc.
' This software is licensed under the terms and conditions of the MIT License accompanying the software ("License").  This software is distributed "AS IS" as set forth in the License.
'''

import os
import sys
import time
import datetime

import logging
import json

from steelscript.common.app import Application
from steelscript.common.service import OAuth
from steelscript.common import Service

def use_single_instance_mode():
    return False

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    #
    # Extract parameters
    #
    opt_client_accelerator_account = helper.get_arg('client_accelerator_account')
    access_code = opt_client_accelerator_account["password"]
    cacontroller_host = helper.get_arg('cacontroller_host',None)
    period = helper.get_arg('period')[0]
    #
    # Connect using SteelScript
    #
    cacontroller = Service("cacontroller",
    cacontroller_host,
    enable_auth_detection=False,
    supports_auth_basic=False,supports_auth_oauth=True,
    auth=OAuth(access_code),
    override_auth_info_api='/api/common/1.0.0/auth_info',
    override_oauth_token_api= '/api/common/1.0.0/oauth/token',
    override_services_api='/api/appliance/1.0.0/services'
    )
    # uri example: /api/stats/1.0.0/report/endpoints?period=last_hour&status=Connected&healthLevel=All&license=All&limit=100&offset=0
    uri = '/api/stats/1.0.0/report/endpoints?period='+ period
    r_dict = cacontroller.conn.json_request('GET', uri)
    #
    # Parse Data
    #
    for ep in r_dict['data']:
        r_json = json.dumps(ep)
        data = r_json
        time=ep['conn_time']
        event = helper.new_event(time=time,source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
        ew.write_event(event)
    #
    # Release resources
    #
    del cacontroller.conn
    del cacontroller
