""" spycloud_config.py

Custom Splunk endpoint, used to facilitate app setup process

"""
import time

from requests.exceptions import HTTPError
from api import breach_catalog
import common
import splunk.admin as admin
import splunk.entity
import splunk.rest

"""
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

""" #pylint: disable=pointless-string-statement


class SpyCloudConfig(admin.MConfigHandler):
    """ SpyCloud config handler"""
    def setup(self):
        """
        Set up supported arguments
        """
        if self.requestedAction == admin.ACTION_EDIT:
            self.supportedArgs.addOptArg('first_run')

    def handleList(self, confInfo):
        """Handle list function"""
        api_key = common.get_credentials(self.getSessionKey())
        try:
            catalog = breach_catalog(api_key, "2017-07-01")
            next(catalog)
        except HTTPError as http_exception:
            if http_exception.response.status_code == 403:
                confInfo['config']['api_status'] = 'auth_failed'
            elif http_exception.response.status_code == 429:
                confInfo['config']['api_status'] = 'rate_limited'
            else:
                confInfo['config']['api_status'] = 'other_error'
        else:
            confInfo['config']['api_status'] = 'success'
        confInfo['config']['first_run'] = 0

    def handleEdit(self, confInfo): #pylint: disable=unused-argument
        """Handle edit function"""
        args = self.callerArgs
        session_key = self.getSessionKey()

        if 'first_run' not in args:
            pass

        # Enable both saved searches
        splunk.rest.simpleRequest(
            '/servicesNS/nobody/SpyCloud/saved/searches/'
            'SpyCloud%20Breach%20Catalog%20Lookup%20Populator/enable',
            method='POST', sessionKey=session_key)
        splunk.rest.simpleRequest(
            '/servicesNS/nobody/SpyCloud/saved/searches/'
            'SpyCloud%20Active%20User%20Lookup%20Populator/enable',
            method='POST', sessionKey=session_key)

        # Force inputs to run by setting its interval to a non-cron value and then toggling it.
        inputs_path = '/servicesNS/nobody/SpyCloud/data/inputs/script/' \
                      '%24SPLUNK_HOME%252Fetc%252Fapps%252FSpyCloud%252Fbin%252F'
        splunk.rest.simpleRequest(
            inputs_path + 'breach_catalog.py/disable',
            method='POST', sessionKey=session_key
        )
        splunk.rest.simpleRequest(
            inputs_path + 'breach_catalog.py',
            method='POST', sessionKey=session_key, postargs={'interval': '86400'}
        )
        splunk.rest.simpleRequest(
            inputs_path + 'breach_catalog.py/enable',
            method='POST', sessionKey=session_key
        )

        splunk.rest.simpleRequest(
            inputs_path + 'watchlist.py/disable',
            method='POST', sessionKey=session_key
        )
        splunk.rest.simpleRequest(
            inputs_path + 'watchlist.py',
            method='POST', sessionKey=session_key, postargs={'interval': '86400'}
        )
        run_time = int(time.time())
        splunk.rest.simpleRequest(
            inputs_path + 'watchlist.py/enable', method='POST', sessionKey=session_key
        )

        timeout = 0
        while True:
            if timeout > 160:
                raise admin.InternalException(
                    "Timed out while waiting for breach_catalog.py to run.")
            entity = splunk.entity.getEntity('/data/inputs/script',
                                             '$SPLUNK_HOME/etc/apps/SpyCloud/bin/breach_catalog.py',
                                             namespace='SpyCloud', sessionKey=session_key,
                                             owner='nobody')
            if 'endtime' not in entity:
                continue
            if int(entity['endtime']) >= run_time:
                break
            else:
                timeout += 1
                time.sleep(0.5)

        # Run breach lookup populator search
        resp = splunk.rest.simpleRequest(
            '/servicesNS/nobody/SpyCloud/saved/searches/'
            'SpyCloud%20Breach%20Catalog%20Lookup%20Populator/dispatch',
            method='POST', sessionKey=session_key)
        job_id = resp[0]['location'].split('jobs/')[1]

        timeout = 0
        while True:
            if timeout > 120:
                raise admin.InternalException(
                    "Timed out while waiting for lookup populator to run.")
            entity = splunk.entity.getEntity('search/jobs', job_id, owner='nobody',
                                             namespace='SpyCloud', sessionKey=session_key)
            if entity['dispatchState'] == 'DONE':
                break
            else:
                timeout += 1
                time.sleep(0.5)

        # Run AD lookup populator
        splunk.rest.simpleRequest(
            '/servicesNS/nobody/SpyCloud/saved/searches/'
            'SpyCloud%20Active%20User%20Lookup%20Populator/dispatch',
            method='POST', sessionKey=session_key)

        # Finally, switch the inputs to a cron schedule to ensure they don't run at the same time.
        splunk.rest.simpleRequest(inputs_path + 'breach_catalog.py', method='POST',
                                  sessionKey=session_key, postargs={'interval': '0 * * * *'})
        splunk.rest.simpleRequest(inputs_path + 'watchlist.py', method='POST',
                                  sessionKey=session_key, postargs={'interval': '30 * * * *'})


# initialize the handler
admin.init(SpyCloudConfig, admin.CONTEXT_NONE)
