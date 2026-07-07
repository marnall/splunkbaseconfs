import os
import splunk.admin as admin
from splunk.clilib.bundle_paths import make_splunkhome_path

BASE_PATH = make_splunkhome_path(['etc', 'apps', 'Splunk_SA_rwi-executive-dashboard', 'appserver',
                                'static', 'js', 'Splunk_SA_rwi-executive-dashboard', 'setup'])

REQUIRED_ARGS_LIST = ['filename']
class StaticHtmlHandler(admin.MConfigHandler):

    def setup(self):
        """This function gets called everytime when static_html endpoint is triggered.
        """
        if self.requestedAction == admin.ACTION_LIST:
            for arg in REQUIRED_ARGS_LIST:
                self.supportedArgs.addReqArg(arg)

    def handleList(self, conf_info):
        """
        This function expects html file name and returns its content as a text.
        """
        args = self.callerArgs

        filename = args.get("filename")[0]
        path = os.path.join(BASE_PATH, filename)

        with open(path, 'r') as fp:
            content = fp.read()

        conf_info["data"]["html_markup"] = content
                
# initialize the handler
admin.init(StaticHtmlHandler, admin.CONTEXT_APP_AND_USER)
        
