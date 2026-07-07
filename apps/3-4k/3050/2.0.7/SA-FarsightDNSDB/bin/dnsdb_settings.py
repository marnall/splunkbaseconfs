""" dnsdb_settings.py
Custom Splunk endpoint, used to facilitate app setup process
"""
import common
import splunk.admin as admin  # pylint: disable=import-error

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


class DNSDBSettings(admin.MConfigHandler):
    """ config handler """

    def setup(self):  # pylint: disable=no-self-use
        """
        Placeholder; does nothing
        :return:
        """
        return

    def handleList(self, confInfo):
        """Handle list function"""
        _dnsdb_api_key = common.get_credentials(self.getSessionKey())

        if not _dnsdb_api_key:  # pylint: disable=literal-comparison
            dnsdb_api_key_exposed = ""
            dnsdb_api_key = ""
        else:
            dnsdb_api_key_exposed = _dnsdb_api_key
            dnsdb_api_key = "<encrypted>"

        confInfo['config']['dnsdb_api_key'] = dnsdb_api_key
        confInfo['config']['dnsdb_api_key_exposed'] = dnsdb_api_key_exposed

    def handleEdit(self, confInfo):  # pylint: disable=unused-argument, no-self-use
        """Handle edit function"""
        return


admin.init(DNSDBSettings, admin.CONTEXT_NONE)
