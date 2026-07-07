# encoding = utf-8

#
# The MIT License (MIT)
# Copyright (c) 2021 Mark Sivill, Splunk Inc
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

# updated generated Splunk Add-on Builder code to hook into custom code

import os
import sys
import time
import datetime


# mark sivill - added reference to custom code
# try to avoid directories/modules/filename with same name
from f1_2020_external.f1_2020_shared import f1_2020_shared

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

# mark sivill - methods updated to call custom code
def validate_input(helper, definition):

    #
    # check udp port number is valid
    #
    udp_port_number = definition.parameters.get('udp_port_number', None)

    # check is a number
    try:
        _ = int(udp_port_number)
    except:
        raise ValueError(
            "UDP Port Number must be a number, current value is {}".format(udp_port_number))

    # check if number is above 0
    if int(udp_port_number) <= 0:
        raise ValueError(
            "UDP Port Number must be above 0, current value is {}".format(udp_port_number))

    #
    # check interval is -1 ( so script only runs once in endless loop )
    #
    interval = definition.parameters.get('interval', None)

    # check is a number
    try:
        _ = int(interval)
    except:
        raise ValueError(
            "Interval must be a number, current value is {}".format(interval))

    # check if number is -1
    if int(interval) != -1:
        raise ValueError(
            "Interval must be set to the number -1 (minus one), current value is {}".format(interval))

    pass


# mark sivill - methods updated to call custom code
def collect_events(helper, ew):

    #
    # define specfic Splunk functions to pass to a generic f1 class
    #
    def output_event(data, time, host, source, sourcetype):
        event = helper.new_event(
            data=data, time=time, host=host, index=helper.get_output_index(), source=source, sourcetype=sourcetype)
        ew.write_event(event)

    def log_error(text):
        ew.log("ERROR", "[{}][{}] {}".format(helper.get_app_name(), helper.get_input_stanza_names() ,text))

    def log_warn(text):
        ew.log("WARN", "[{}][{}] {}".format(helper.get_app_name(), helper.get_input_stanza_names() ,text))

    def log_info(text):
        ew.log("INFO", "[{}][{}] {}".format(helper.get_app_name(), helper.get_input_stanza_names() ,text))

    def log_debug(text):
        ew.log("DEBUG", "[{}][{}] {}".format(helper.get_app_name(), helper.get_input_stanza_names() ,text))

    # pass functions and variables into shared python module
    f1 = f1_2020_shared(helper.get_arg('udp_port_number'), output_event, log_error, log_warn, log_info, log_debug)

    # start collecting data on port
    f1.collect_data()
