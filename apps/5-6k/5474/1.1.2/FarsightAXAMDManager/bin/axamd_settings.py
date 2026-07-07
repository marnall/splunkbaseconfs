""" greynoise_config.py
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


class AXAMDSettings(admin.MConfigHandler):
    """ config handler """

    def setup(self):  # pylint: disable=no-self-use
        """
        Placeholder; does nothing
        :return:
        """
        return

    def handleList(self, confInfo):
        """Handle list function"""
        _axamd_api_key = common.get_credentials(self.getSessionKey())

        if not _axamd_api_key:  # pylint: disable=literal-comparison
            axamd_api_key = ""
            axamd_api_key_exposed = ""
        else:
            axamd_api_key = "<encrypted>"
            axamd_api_key_exposed = _axamd_api_key

        confInfo['config']['axamd_api_key'] = axamd_api_key
        confInfo['config']['axamd_api_key_exposed'] = axamd_api_key_exposed

    def handleEdit(self, confInfo):  # pylint: disable=unused-argument, no-self-use
        """Handle edit function"""
        return


admin.init(AXAMDSettings, admin.CONTEXT_NONE)
