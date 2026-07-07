""" threatintel_config.py
Custom Splunk endpoint, used to facilitate app setup process
"""
import common
from splunk import admin # pylint: disable=import-error

# pylint: disable=pointless-string-statement
"""
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

"""
# pylint: enable=pointless-string-statement


class SAHLThreatIntelFeedConfig(admin.MConfigHandler):
    """ config handler """
    def setup(self):
        """
        Placeholder; does nothing
        :return:
        """
        return

    def handleList(self, confInfo):
        """Handle list function"""
        api_key = common.getCredentials(self.getSessionKey())

        if api_key is "":  # pylint: disable=literal-comparison
            api_key = ""
        else:
            api_key = "<encrypted>"

        confInfo['config']['api_key'] = api_key

    def handleEdit(self, confInfo):  # pylint: disable=unused-argument
        """Handle edit function"""
        return


admin.init(SAHLThreatIntelFeedConfig, admin.CONTEXT_NONE)
