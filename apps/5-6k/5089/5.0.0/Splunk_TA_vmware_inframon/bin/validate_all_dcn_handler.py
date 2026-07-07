# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# importing core python packages
import json

# SA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
from hydra_inframon.models import HydraNodeStanza

# importing rest_utility
from rest_utility import setup_logger
import rest_utility as ru

# defining global constants
logger = setup_logger(log_name="dcn_configuration.log",
                      logger_name="dcn_configuration")
local_host_path = splunk.mergeHostPath()
entity_type = "node"


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        pass

    def handleList(self, conf_info):
        """When GET request is done on the endpoint validate_all_dcn this method is called,
        It returns the validation details of all the configured DCN in json format."""
        try:

            local_session_key = self.getSessionKey()

            # getting all the stanzas of inframon_hydra_node.conf
            stanzas = HydraNodeStanza.all(sessionKey=local_session_key)
            stanzas = stanzas.filter_by_app("Splunk_TA_vmware_inframon")
            stanzas._owner = "nobody"
            # preparing response from stanza list
            validation_response = {}
            pool_list = set()
            for stanza in stanzas:
                node_path = stanza.host
                heads = stanza.heads
                pool_name = stanza.pool_name
                auth_token = ru.get_node_auth_token(stanza, local_session_key, logger)

                response = ru.validate_dcn(
                    node_path, auth_token, str(heads), pool_name, local_session_key, logger,
                    legacy_username=stanza.user)

                validation_modified = False
                if stanza.credential_validation != response['credential_validation'] or \
                        stanza.addon_validation != response['addon_validation']:
                    validation_modified = True

                token_principal = response.get("token_principal")
                if token_principal and token_principal != stanza.user:
                    logger.warning(
                        "Validation principal mismatch for node=%s current=%s resolved=%s. "
                        "Keeping stored principal to preserve credential stanza binding.",
                        node_path, stanza.user, token_principal)
                stanza.credential_validation = response['credential_validation']
                stanza.addon_validation = response['addon_validation']
                stanza.last_connectivity_checked = response["last_connectivity_checked"]

                if not stanza.passive_save():
                    logger.error(
                        "[pool={1}]Failed to update validation status for node stanza:{0}".format(node_path, pool_name))
                elif validation_modified:
                    logger.info(
                        "[pool={1}]Successfully updated connectivity checked time for dcn stanza:{0} after validation".format(
                            node_path, pool_name))
                    pool_list.add(pool_name)

                validation_response.update({node_path: {"status": response["status"], "message": response["message"],
                                                        "last_connectivity_checked": response[
                                                            "last_connectivity_checked"].strftime(
                                                            "%Y-%m-%dT%H:%M:%S.%f")}})

            for pool_name in pool_list:
                ru.set_conf_modification_time(pool_name, entity_type, local_session_key, logger)

            conf_info["data"]["validation_response"] = json.dumps(validation_response)
        except Exception as e:
            logger.exception(e)
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
