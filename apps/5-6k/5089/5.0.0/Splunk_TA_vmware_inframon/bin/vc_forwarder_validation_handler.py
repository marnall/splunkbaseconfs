# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing rest_utility
from rest_utility import setup_logger
import rest_utility as ru

# TA and SA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))
from hydra_inframon.models import SplunkStoredCredential
from ta_vmware_inframon.models import TAVMwareVCenterForwarderStanza

# defining global constants
logger = setup_logger(log_name="vcenter_configuration.log",
                      logger_name="vcenter_configuration")
local_host_path = splunk.mergeHostPath()

OPT_ARGS_LIST = ['vc']


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_LIST:
            for arg in OPT_ARGS_LIST:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, conf_info):
        """ This method is called on GET request on vc_forwarder_validation,
        it expects @vc-path of vCenter to validate its forwarder."""
        try:
            args = self.callerArgs
            vc_path = args.get("vc")
            vc_path = vc_path[0]
            local_session_key = self.getSessionKey()

            forwarder_stanza = TAVMwareVCenterForwarderStanza.from_name(vc_path, "Splunk_TA_vmware_inframon", "nobody",
                                                                        session_key=local_session_key,
                                                                        host_path=local_host_path)

            if forwarder_stanza:
                stored_cred = SplunkStoredCredential.from_name(
                    SplunkStoredCredential.build_name(forwarder_stanza.host, forwarder_stanza.user),
                    app="Splunk_TA_vmware_inframon",
                    owner="nobody", host_path=local_host_path, session_key=local_session_key)

                password = stored_cred.clear_password
                username = forwarder_stanza.user
                uri = forwarder_stanza.host
                response = ru.validate_vcenter_forwarder(uri, username, password, local_session_key, logger)

                forwarder_stanza.credential_validation = response["credential_validation"]
                forwarder_stanza.addon_validation = response["addon_validation"]
                if not forwarder_stanza.passive_save():
                    logger.error(
                        "Problem updating the validation status of splunk forwarder stanza for vc=%s and vc_splunk_uri=%s.",
                        vc_path, uri)
                else:
                    logger.info(
                        "Successfully updated the validation status of splunk forwarder stanza for vc=%s and vc_splunk_uri=%s.",
                        vc_path, uri)

                conf_info["data"]["status"] = response["status"]
                conf_info["data"]["message"] = response["message"]

            else:
                logger.error(
                    "vCenter forwarder stanza for vc:{0} not found for validating.".format(
                        vc_path))
                conf_info["data"]["status"] = "404"
                conf_info["data"]["message"] = "Stanza not found."
        except Exception as e:
            logger.exception("Exception Occurred:" + str(e))
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
