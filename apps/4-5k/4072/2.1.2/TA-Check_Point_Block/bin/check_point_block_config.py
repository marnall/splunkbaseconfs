""" check_point_block_config.py
Custom Splunk endpoint, used to facilitate app setup process
"""
import common
import splunk.admin as admin  # pylint: disable=import-error, consider-using-from-import

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


class CheckPointBlockConfig(admin.MConfigHandler):
    """ config handler """

    def setup(self):
        """
        Placeholder; does nothing
        :return:
        """
        return

    def handleList(self, confInfo):
        """Handle list function"""
        cp_username, cp_password = common.get_credentials(self.getSessionKey())

        if cp_password == "":  # nosec
            cp_password = "" # nosec
        else:
            cp_password = "<encrypted>" # nosec

        confInfo['config']['cp_password'] = cp_password
        confInfo['config']['cp_username'] = cp_username

    def handleEdit(self, confInfo):  # pylint: disable=unused-argument
        """Handle edit function"""
        return


admin.init(CheckPointBlockConfig, admin.CONTEXT_NONE)
