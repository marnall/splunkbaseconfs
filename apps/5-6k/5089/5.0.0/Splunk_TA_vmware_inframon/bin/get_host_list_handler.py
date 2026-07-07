# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# importing core python packages
import json
from xml.dom import minidom

# TA and SA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))
from hydra_inframon.models import SplunkStoredCredential
from ta_vmware_inframon.models import TAVMwareCollectionStanza
import ta_vmware_inframon.simple_vsphere_utils as vsu

# defining global constants
local_host_path = splunk.mergeHostPath()
logger = setup_logger(log_name="vcenter_configuration.log",
                      logger_name="vcenter_configuration")

REQUIRED_ARGS_LIST = ['vc']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_LIST:
            for arg in REQUIRED_ARGS_LIST:
                self.supportedArgs.addReqArg(arg)

    def handleList(self, conf_info):
        """When GET request is done on the endpoint get_host_list, this method is called,
        It returns the list of hosts of given vCenter"""
        try:
            args = self.callerArgs
            local_session_key = self.getSessionKey()
            vc_path = args.get("vc")[0]

            vc_stanza = TAVMwareCollectionStanza.from_name(vc_path, "Splunk_TA_vmware_inframon", "nobody",
                                                           session_key=local_session_key,
                                                           host_path=local_host_path)

            if not vc_stanza:
                logger.error("Failed to find vCenter stanza for: {0}".format(vc_path))
                raise RestError(400, "Failed to find vCenter stanza for: {0}".format(vc_path))

            stored_cred = SplunkStoredCredential.from_name(
                SplunkStoredCredential.build_name(vc_path, vc_stanza.username),
                app="Splunk_TA_vmware_inframon",
                owner="nobody", host_path=local_host_path, session_key=local_session_key)

            if not stored_cred:
                logger.error("Failed to find credential stanza of vCenter:{0}".format(vc_path))
                raise RestError(400, "Failed to find credential stanza of vCenter:{0}".format(vc_path))

            password = stored_cred.clear_password
            username = vc_stanza.username

            vss = vsu.vSphereService(vc_path, username=username, password=password)
            response = vss.get_obj_list(
                [{'type': 'HostSystem', 'all': 'false', 'pathSet': 'name'}],
                {'type': 'Folder', 'moid': "group-d1"})

            resp_xml = minidom.parseString(response)
            host_list = []
            for name in resp_xml.getElementsByTagName("val"):
                host_list.append(name.firstChild.data)

            conf_info["data"]["host_list"] = json.dumps(host_list)

        except vsu.LoginFailure as e:
            logger.error(str(e))
            raise e
        except vsu.ConnectionFailure as e:
            logger.error(str(e))
            raise e
        except Exception as e:
            logger.exception("Could not get host list for vCenter: {0}".format(vc_path))
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
