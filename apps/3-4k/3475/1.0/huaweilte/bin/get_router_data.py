#!/usr/bin/python
# coding: utf-8

"""
    This script sends a request to the router's API.
    You need to provide one of the known URI (listed in the check_argument function below) as argument.
    You have to enter the router's homepage URL in the configuration file APP/bin/huaweilte.conf. Defaults to http://192.168.8.1. It must not contain anything else.
    The first time, the script gets the session token from the router's homepage and stores it in the file APP/bin/session.tmp.
    The next times, the script uses this session data to send the request immediately.

"""

from __future__ import (unicode_literals, absolute_import,
                        print_function, division)

import re
import requests
from datetime import datetime
import os
import sys
import pickle


def grep_csrf(html):
    # Regex to extract the token from the router's homepage
    pat = re.compile(r".*meta name=\"csrf_token\" content=\"(.*)\"", re.I)
    matches = (pat.match(line) for line in html.splitlines())
    return [m.group(1) for m in matches if m]

def get_config(conf_filepath,conf_name):
    # Open the config file containing the baseurl
    # conf_filepath is the path to the config file (e.g. APP/bin/huaweilte.conf)
    # conf_name is not used. It may be used in a future version to specify which configuration item to read.
    if os.path.isfile(conf_filepath):
        try:
            conf_file = open(conf_filepath,'r')
            conf_value = conf_file.readline().rstrip()
            conf_file.close()

        # Catch the exception. Real exception handler would be more robust
        except IOError:
            sys.stderr.write('Error: failed to read conf file, ' + conf_filepath + '\n')
            sys.exit(2)
    else:
        sys.stderr.write('Error: ' + conf_filepath + ' file not found! Exiting. \n')
        exit()

    if debug:
        print(conf_name + ' = ' + conf_value)

    return conf_value

def get_new_session(session_filepath,baseurl):
    # Creates a new session 
    session = requests.Session()
    # Gets the homepage
    r = session.get(baseurl)
    # Extracts the token
    csrf_tokens = grep_csrf(r.text)
    token = csrf_tokens[0]
    # Updates the session header with the token
    session.headers.update({'__RequestVerificationToken': token})

    # Saves the session configuration (including the token) to a file
    try:
        with open(session_filepath, "wb") as f:
            pickle.dump(session, f)
            if debug:
                print("Session saved to cache")

    except IOError:
        sys.stderr.write("Warning: Unable to write session to cache.")

    return session

def get_last_session(session_filepath,baseurl):
    # Reads the session configuration from the cache file
    try:
        with open(session_filepath, "rb") as f:
            session = pickle.load(f)
            if debug:
                print("Got session from cache")

    except IOError:
        sys.stderr.write("Warning: Unable to get session from cache. Try to create a new session.")
        session = get_new_session(session_filepath,baseurl)

    return session

def check_argument():
    # List of known request URI. There may be some more... 
    # Some of them do not return any data.
    # Some of them require authentification (e.g. /api/device/information). They are not supported, yet.
    # Some of them must be used with POST request (e.g. api/user/login for login). They are not supported yet too.
    # This list is from https://blog.hqcodeshop.fi/archives/259-Huawei-E5186-AJAX-API.html
    uri_list = ['api/cradle/status-info','api/device/autorun-version','api/device/basic_information','/api/device/control','api/device/device-feature-switch','api/device/information','api/device/signal','api/device/usb-tethering-switch','api/dialup/connection','api/dialup/dial','api/dialup/mobile-dataswitch','api/global/module-switch','api/host/info','api/language/current-language','api/monitoring/check-notifications','api/monitoring/converged-status','api/monitoring/status','api/monitoring/traffic-statistics','api/net/current-plmn','api/net/net-mode','api/online-update/upgrade-messagebox','api/pin/status','api/redirection/homepage','api/security/bridgemode','api/security/upnp','api/sms/get-cbsnewslist','api/sms/sms-list','api/user/login','api/user/logout','api/user/remind','api/user/session','api/user/state-login','api/ussd/get','api/webserver/token','api/wlan/basic-settings','api/wlan/handover-setting','api/wlan/multi-security-settings','api/wlan/multi-switch-settings','api/wlan/station-information','api/wlan/wifi-feature-switch','config/deviceinformation/config.xml','config/global/config.xml','config/global/languagelist.xml','config/global/net-type.xml','config/pcassistant/config.xml','config/webuicfg/config.xml']

    if len(sys.argv) == 2:
        uri = str(sys.argv[1])
        if debug:
            print("uri = " + uri)
        if uri == "list":
            print('List of allowed requests:')
            for item in uri_list:
                print(item)
            exit()
        if not uri in uri_list:
            sys.stderr.write('Error: the request is not in the list of known requests')
            exit()

    else:
        sys.stderr.write('Error: this script requires an API request as argument')
        exit()

    return uri

def main():
    app_bin_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'huaweilte', 'bin', '')
    conf_filepath = app_bin_path + "huaweilte.conf";
    session_filepath = app_bin_path + "session.tmp";
    baseurl = "";
    request = "";

    request = check_argument()
    baseurl = get_config(conf_filepath,"baseurl")
        
    if baseurl:
        # We get the last session data
        s = get_last_session(session_filepath,baseurl)

        # We launch the API request
        full_request = baseurl + request
        if debug:
            print("full_request = " + full_request)
        r = s.get(full_request)

        # We check if the result is correct.
        # When the session is not correctly set, we can get an HTML page or an XML result containing an error
        if '<?xml' in r.text and 'error' not in r.text:
            print(str(datetime.now()))
            print(r.text)
        else:
            sys.stderr.write('Error: result is not xml or session is closed. Try to create a new session.')
            session = get_new_session(session_filepath,baseurl)

    else:
        sys.stderr.write('Error: baseurl not found in conf file')

if __name__ == '__main__':
    debug = False;
    main()


