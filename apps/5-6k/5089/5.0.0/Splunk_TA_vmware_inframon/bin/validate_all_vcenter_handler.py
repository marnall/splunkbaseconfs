# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing rest_utility
from rest_utility import setup_logger
import rest_utility as ru

# Core Python Imports
import json

# TA and SA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'Splunk_TA_vmware_inframon', 'bin']))

# models import
from hydra_inframon.models import SplunkStoredCredential
from ta_vmware_inframon.models import TAVMwareCollectionStanza

# defining global constants
logger = setup_logger(log_name="vcenter_configuration.log",
                      logger_name="vcenter_configuration")
local_host_path = splunk.mergeHostPath()
entity_type = "collection"


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        pass

    def handleList(self, conf_info):
        """This method is called at GET request on validate_all_vcenter endpoint."""
        try:
            local_session_key = self.getSessionKey()
            stanzas = TAVMwareCollectionStanza.all(sessionKey=local_session_key)

            validation_response = {}
            pool_list = set()
            for vc_stanza in stanzas:

                vc_path = vc_stanza.target[0]
                username = vc_stanza.username
                pool_name = vc_stanza.pool_name

                stored_cred = SplunkStoredCredential.from_name(
                    SplunkStoredCredential.build_name(vc_path, vc_stanza.username),
                    app="Splunk_TA_vmware_inframon",
                    owner="nobody", host_path=local_host_path, session_key=local_session_key)
                password = stored_cred.clear_password

                response = ru.validate_vcenter(vc_path, username, password, pool_name, local_session_key, logger)

                vc_stanza.last_connectivity_checked = response["last_connectivity_checked"]
                validation_modified = False

                if vc_stanza.credential_validation != response["credential_validation"]:
                    validation_modified = True

                vc_stanza.credential_validation = response["credential_validation"]

                if not vc_stanza.passive_save():
                    logger.error(
                        "[pool={1}]Failed to update connectivity checked time for vc stanza:{0}".format(vc_path,
                                                                                                        pool_name))
                elif validation_modified:
                    logger.info(
                        "[pool={1}]Successfully updated connectivity checked time for vc stanza:{0} after validation".format(
                            vc_path, pool_name))
                    pool_list.add(pool_name)

                validation_response.update({vc_path: {"status": response["status"], "message": response["message"],
                                                      "last_connectivity_checked": response[
                                                          "last_connectivity_checked"].strftime(
                                                          "%Y-%m-%dT%H:%M:%S.%f")}})

            # updating conf modification time of all the pools
            # for which validation status is modified
            for pool_name in pool_list:
                ru.set_conf_modification_time(pool_name, entity_type, local_session_key, logger)

            conf_info["data"]["validation_response"] = json.dumps(validation_response)
        except Exception as e:
            logger.exception("Exception occurred:" + str(e))
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
