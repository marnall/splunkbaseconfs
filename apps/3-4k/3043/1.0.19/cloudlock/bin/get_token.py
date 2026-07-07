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
#
from __future__ import print_function
import json
import sys
import splunk.Intersplunk as si
import splunk.rest
import six
if six.PY2:
	import urllib
else:
    import urllib.parse as urllib 

def getSettings(input_buf):

    settings = {}
    # get the header info
    input_buf = sys.stdin
    # until we get a blank line, read "attr:val" lines, setting the values in 'settings'
    attr = last_attr = None
    while True:
        line = input_buf.readline()
        line = line[:-1] # remove lastcharacter(newline)
        if len(line) == 0:
            break

        colon = line.find(':')
        if colon < 0:
            if last_attr:
               settings[attr] = settings[attr] + '\n' + urllib.unquote(line)
            else:
               continue

        # extract it and set value in settings
        last_attr = attr = line[:colon]
        val  = urllib.unquote(line[colon+1:])
        settings[attr] = val

    return(settings)

def get_token(sessionKey, base_uri=None):
    '''Get the token from the KV Store'''

    # Permit override of base URI in order to target a remote server.
    endpoint = '/servicesNS/nobody/cloudlock/storage/collections/data/cloudlock'
    if base_uri:
        repl_uri = base_uri + endpoint
    else:
        repl_uri = endpoint

    response, content = splunk.rest.simpleRequest(repl_uri,
        method='GET', sessionKey=sessionKey, raiseAllErrors=False)

    if response.status == 400:
        return (False, response.status, content)
    elif response.status != 200:
        return (False, response.status, content)
    return (True, response.status, content)


if __name__ == '__main__':

    try:
        name = '*'
        token = ''
        url = '*'
        if len(sys.argv) >1:
            for arg in sys.argv[1:]:
                if arg.lower().startswith("name="):
                    eqsign = arg.find('=')
                    name = arg[eqsign+1:len(arg)].strip()
                elif arg.lower().startswith("url="):
                    eqsign = arg.find('=')
                    url = arg[eqsign+1:len(arg)].strip()

        settings = getSettings(sys.stdin)
        (worked, response, content) = get_token(settings['sessionKey'], None)

        if worked == False:
            raise Exception("GetCloudLockToken: Failed to get token list")

        print("Name,URL,Token")
        j = json.loads(content)

        #
        # look for exact match
        #

        for row in j:
            # find exact match
            if row["name"].lower() == name.lower() and row["url"].lower() == url.lower():
                token = row["token"]
            elif token == '' and row["name"] == "*" and row["url"] == url:
                token = row["token"]
            elif token == '' and row["name"] == "*" and url == "*":
                token = row["token"]

        print(name + "," + url + "," + token)

    except Exception as e:
        si.generateErrorResults(e)
