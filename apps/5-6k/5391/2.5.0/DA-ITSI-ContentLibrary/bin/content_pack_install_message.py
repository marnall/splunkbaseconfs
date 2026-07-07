import json
import os
import sys

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
    sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'DA-ITSI-ContentLibrary', 'lib']))
except ImportError:
    sys.path.insert(0, os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'DA-ITSI-ContentLibrary', 'lib'))


from itsi_content_setup_logging import logger
from itsi_content_utils import SplunkMessageHandler
from solnlib.modular_input import ModularInput
import splunk.rest as rest


class InstallMessageModularInput(ModularInput):
    """
    Modular input dedicated to post an informational message on Installation/Upgrade of Splunk App for Content Packs v2.0.0 or later
    """
        
    title = "Splunk App for Content Packs Installation Message"
    description = "Modular input to post an informational message on installation of Splunk App for Content Packs"
    handlers = None
    app = "DA-ITSI-ContentLibrary"
    name = "content_pack_install_message"
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [{
            'name': 'log_level',
            'title': 'Logging Level',
            'description': 'This is the level at which the modular input will log data.'
        }]
    
    def disable_input(self):
        '''
        This method disables the modular input.
        '''
        try:
            mod_input_endpoint = rest.makeSplunkdUri() + "servicesNS/nobody/DA-ITSI-ContentLibrary/data/inputs/content_pack_install_message/default/disable"
            rest.simpleRequest(
                path=mod_input_endpoint,
                method='POST',
                postargs={},
                sessionKey=self.session_key)
        except Exception as ex:
            logger.exception('Exception occured while posting message: %s', ex)

    def get_version(self):
        '''
        This method fetches the version of DA-ITSI-ContentLibrary installed in customer's environment
        :return: the version of DA-ITSI-ContentLibrary
        :rtype: str
        '''
        try:
            app_endpoint = rest.makeSplunkdUri() + "servicesNS/nobody/system/apps/local/DA-ITSI-ContentLibrary?output_mode=json"
            response, contents = rest.simpleRequest(
                path=app_endpoint,
                method='GET',
                sessionKey=self.session_key)
            if response.status == 200:           
                data = json.loads(contents)
                version = data["entry"][0]["content"].get("version")
                return version
        except Exception as ex:
            logger.exception('Exception occured while fetching app version: %s', ex)

    
    def do_run(self, input_config):
        '''
        This is the method called by splunkd when modular input is enabled.
        @type input_config: dict
        @param input_config: config passed down by splunkd
        '''
        message_handler = SplunkMessageHandler(self.session_key)
        version = self.get_version()
        if version:
            message_handler.post_or_update_message("content_pack_install_message", "info", "[IMPORTANT] Successfully installed Splunk App for Content Packs v" + version + ". Saved searches are now deactivated by default. You can activate saved searches for each content pack from the [[/app/itsi/data_integrations?tab=content|Data Integrations page]]. For more information, see the [https://docs.splunk.com/Documentation/ContentPackApp/" + version + "/Overview/Overview Overview of the Splunk App for Content Packs].","itoa_admin")
        else:
            logger.error('Unable to fetch the version of Splunk App for Content Packs')
        self.disable_input()
          

if __name__ == '__main__':
    worker = InstallMessageModularInput()
    worker.execute()
    sys.exit(0)
