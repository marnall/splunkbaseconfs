#! /usr/bin/python
#
# Copyright (c) 2015-2017. CloudLock, LLC.  All rights reserved.
#
# This application is protected by contract law, copyright laws, and international treaties.
# Only authorized users of the CloudLock Service are authorized to use this application.
# This application includes Python, an open source component subject to the following notice:
#
# Copyright 2011-2014 Splunk, Inc. 
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may 
# not use this file except in compliance with the License. You may obtain 
# a copy of the License at 
# http://www.apache.org/licenses/LICENSE-2.0 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT 
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations 
# under the License.
from __future__ import print_function
import sys
import splunk.Intersplunk as si
import json
import requests
import six
if six.PY2:
	from ConfigParser import ConfigParser, NoOptionError
else:
	from configparser import ConfigParser, NoOptionError

if __name__ == '__main__':

    url = ""
    token = ""
    ticket = ""
    status = ""
    severity = ""

    try:
        if len(sys.argv) >5:
            for arg in sys.argv[1:]:
                if arg.lower().startswith("url="):
                    eqsign = arg.find('=')
                    url = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("token="):
                    eqsign = arg.find('=')
                    token = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("ticket="):
                    eqsign = arg.find('=')
                    ticket = arg[eqsign+1:len(arg)]
                elif arg.lower().startswith("status="):
                    eqsign = arg.find('=')
                    status = arg[eqsign+1:len(arg)].replace("%20"," ")
                elif arg.lower().startswith("severity="):
                    eqsign = arg.find('=')
                    severity = arg[eqsign+1:len(arg)]
        else:
            raise Exception("updateCloudLockTicket-F001: Usage: updateCloudLockTicket url=<string> token=<string> ticket=<string> severity=<string> status=<string>")

        print("Response")
        method = "PUT"
        session = requests.session()
        session.mount(url, requests.adapters.HTTPAdapter())
        session.headers.update({'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(token)})
        data = {'incident_status': status, 'severity': severity}
        url = url + "/incidents/" + ticket
        params=None;
        verify_ssl = False
        response = session.request(method, url, params=None, data=json.dumps(data), verify=False)
        # Success will return json object, Failure will print ERROR and then reason
        #response.raise_for_status()
        #theResponse = response.json();
        if response.status_code == 888:
            msg = "There is a new version of the CloudLock Splunk Application. In order to continue receiving CloudLock information, please upgrade the Application." 
            print("ERROR")
            print(msg)
        else:
            response.raise_for_status()
            print("SUCCESS")

    except Exception as e:
        si.generateErrorResults(e)

