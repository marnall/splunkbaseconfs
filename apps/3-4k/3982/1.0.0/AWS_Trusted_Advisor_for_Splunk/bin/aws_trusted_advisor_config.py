""" aws_trusted_advisor_config.py
Custom Splunk endpoint, used to facilitate app setup process
"""
import common
import splunk.admin as admin

"""
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values
      corresponds to handleractions = edit in restmap.conf

"""  # pylint: disable=pointless-string-statement


class AWSTrustedAdvisorConfig(admin.MConfigHandler):
    """ AWSTrustedAdvisorConfig config handler"""
    def setup(self):  # pylint: disable=no-self-use
        """
        Placeholder; does nothing
        :return:
        """
        return

    def handleList(self, confInfo):
        """Handle list function"""
        access_key, secret_key = common.get_credentials(self.getSessionKey())
        region = self.readConfCtx("aws")["aws"]["region"]

        if access_key is not None:
            access_key = "<encrypted>"
        if secret_key is not None:
            secret_key = "<encrypted>"

        confInfo['config']['access_key'] = access_key
        confInfo['config']['secret_key'] = secret_key
        confInfo['config']['region'] = region

    def handleEdit(self, confInfo):  # pylint: disable=unused-argument, no-self-use
        """Handle edit function"""
        return


admin.init(AWSTrustedAdvisorConfig, admin.CONTEXT_NONE)
