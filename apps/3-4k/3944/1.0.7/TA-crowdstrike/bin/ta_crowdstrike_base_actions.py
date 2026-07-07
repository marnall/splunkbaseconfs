# Python imports
import json
import sys
import os
import base64
import logging
import re

# Splunk imports
import splunk.version as ver

version = float(re.search("(\d+.\d+)", ver.__version__).group(1))

try:
    if version >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError as e:
    sys.exit(3)

# Get app name
myapp = __file__.split(os.sep)[-3]
# Add path to app's lib directory to use modules within it
sys.path.append(make_splunkhome_path(["etc", "apps", myapp, "bin", "lib"]))
LIB_FOLDER_NAME = 'ta_crowdstrike'
folder_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(folder_path, LIB_FOLDER_NAME))

# Local imports
from cim_actions import ModularAction
import crowdstrike_utils as csutils
from ta_crowdstrike import requests
import crowdstrike_consts as consts

class CrowdStrikeBaseAction(ModularAction):
    """ ModularAction wrapper
    """

    def __init__(self, settings, logger, action_name=None):
        """ Initialize object of CrowdStrikeBaseAction.

        :param settings: includes action metadata and various other configurations obtained by reading standard input
        :param logger: logger for the action
        :param action_name: action name
        """

        # Call __int__ of super class
        super(CrowdStrikeBaseAction, self).__init__(settings, logger, action_name)
        # Base URL
        self.falcon_url = consts.FALCON_URL
        # Obtain session key
        session_key = self.session_key
        # Get username and password for query API
        account_name, account_key = csutils.get_credentials(session_key)
        if not account_name or not account_key:
            self.message('CrowdStrike Error: Unable to fetch the credentials required to execute the action', 'failure')
            sys.exit(-1)

        # Encode username and password
        base64string = base64.b64encode('%s:%s' % (account_name, account_key))
        # Prepare request headers
        self.headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
        # Obtain proxy details
        self.proxies = csutils.get_proxy_info(session_key)

    def dowork(self, endpoint, method="get", params=None, data=None, source=None, sourcetype=None):
        """ Make REST call for the requested action and index back the response obtained along with the status
        of the action(success/failure).

        :param endpoint: REST endpoint to hit
        :param method: request method (GET/POST/PUT/DELETE)
        :param params: request parameters
        :param data: request payload
        :param source: source for the data to be indexed
        :param sourcetype: sourcetype for the data to be indexed
        """

        # Send the required request to falcon and index back the obtained response
        request_func = getattr(requests, method)
        # Make REST call
        rest_resp = request_func(self.falcon_url + endpoint, headers=self.headers, params=params, data=data,
                                 proxies=self.proxies)
        # Add response in the events list
        self.addevent(json.dumps(rest_resp.json()), sourcetype=sourcetype)

        if (self.action_name == "crowdstrike_ioc_count" and rest_resp.status_code == 404) or\
                rest_resp.status_code == 200:
            if self.action_name == "crowdstrike_upload_ioc" and rest_resp.json().get("errors"):
                if self.writeevents(index="main", source=source):
                    # Log message
                    self.message('Created event for the error encountered', status='failure', rids=self.rids)
                else:
                    # Log message
                    self.message('Failed to create event for the error encountered', status='failure', rids=self.rids,
                                 level=logging.ERROR)
            else:
                # Write the events added in the events list into the specified index and source
                if self.writeevents(index="main", source=source):
                    # Log message
                    self.message('Successfully created splunk event', status='success', rids=self.rids)
                else:
                    # Log message
                    self.message('Failed to create splunk event', status='failure', rids=self.rids, level=logging.ERROR)

        # Mark action as failure if http status code of request is other than 200
        else:
            # Write the events added in the events list into the specified index and source
            if self.writeevents(index="main", source=source):
                # Log message
                self.message('Created event for the error encountered', status='failure', rids=self.rids)
            else:
                # Log message
                self.message('Failed to create event for the error encountered', status='failure', rids=self.rids,
                             level=logging.ERROR)

        del self.events[:]
