"""
Shodan_python_handler.py
Standard setup configuration handler in Splunk
"""
import splunk.admin as admin


class ConfigApp(admin.MConfigHandler):
    """
    Set up supported arguments
    """

    def setup(self):
        """
        Initial setup
        :return:
        """
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['api_key']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confinfo):
        """
        Lists out items for Setup
        :param confInfo:
        :return:
        """
        confDict = self.readConf("shodan")
        if confDict is not None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['api_key'] and val in [None, '']:
                        val = ''
                    confinfo[stanza].append(key, val)

    def handleEdit(self):
        """
        Handles Editing of Setup information
        :param confinfo:
        :return:
        """

        if self.callerArgs.data['api_key'][0] in [None, '']:
            self.callerArgs.data['api_key'][0] = ''

        api_key = self.callerArgs.data['api_key']
        self.writeConf('shodan', 'shodan', self.callerArgs.data)
        return api_key


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
