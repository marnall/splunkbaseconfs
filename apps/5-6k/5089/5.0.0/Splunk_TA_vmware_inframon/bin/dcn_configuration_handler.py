# splunk sdk imports
import splunk.admin as admin
import splunk
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

# import necessary python packages
import json
import re

# importing rest_utility
from rest_utility import setup_logger, RestError
import rest_utility as ru

# SA imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))
from hydra_inframon.logging_utils import format_log_message
from hydra_inframon.models import HydraNodeStanza, SplunkStoredCredential

# defining global constants
logger = setup_logger(log_name="dcn_configuration.log",
                      logger_name="dcn_configuration")
local_host_path = splunk.mergeHostPath()
entity_type = "node"

REQUIRED_ARGS_CREATE = ['heads', 'pool_name']
REQUIRED_ARGS_EDIT = ['node', 'heads', 'pool_name']
OPT_ARGS = ['auth_token', 'username', 'password']


def _single_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _has_value(value):
    return value not in (None, "")


def _admin_context(node=None, pool_name=None):
    return {
        "component": "admin",
        "node": node,
        "pool": pool_name,
    }


def _admin_log(level, message, fields=None, node=None, pool_name=None):
    getattr(logger, level)(format_log_message(message, fields, _admin_context(node=node, pool_name=pool_name)))


def _admin_event(level, event, status, message, node=None, pool_name=None, reason=None, **fields):
    payload = {"event": event, "status": status}
    if reason:
        payload["reason"] = reason
    payload.update(fields)
    _admin_log(level, message, payload, node=node, pool_name=pool_name)


class ConfigApp(admin.MConfigHandler):

    def setup(self):
        """This method is called at every request before handle method is called.
        This is used for adding optional and required arguments for particular requests."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in REQUIRED_ARGS_EDIT:
                self.supportedArgs.addReqArg(arg)
            for arg in OPT_ARGS:
                self.supportedArgs.addOptArg(arg)

        if self.requestedAction == admin.ACTION_CREATE:
            for arg in REQUIRED_ARGS_CREATE:
                self.supportedArgs.addReqArg(arg)
            for arg in OPT_ARGS:
                self.supportedArgs.addOptArg(arg)

    def handleRemove(self, conf_info):
        """When DELETE request with the target is done, this method is called.
        It expects the path of the DCN to be deleted. """
        try:
            node_path = self.callerArgs.id
            local_session_key = self.getSessionKey()
            _admin_log(
                "info",
                "DCN delete requested",
                {"event": "dcn.delete", "status": "start"},
                node=node_path,
            )

            node_stanza = HydraNodeStanza.from_name(node_path, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                    session_key=local_session_key)

            if node_stanza:
                node_username = node_stanza.user
                pool_name = node_stanza.pool_name
                stored_cred = SplunkStoredCredential.from_name(
                    SplunkStoredCredential.build_name(node_stanza.host, node_username), app="Splunk_TA_vmware_inframon",
                    owner="nobody", host_path=local_host_path,
                    session_key=local_session_key)
                if stored_cred:
                    node_auth_token = stored_cred.clear_password
                    _admin_event(
                        "info",
                        "dcn.credential.delete",
                        "start",
                        "DCN delete is removing stored auth token",
                        node=node_path,
                        pool_name=pool_name,
                        token_principal=node_username,
                    )
                    if not stored_cred.passive_delete():
                        _admin_event(
                            "warning",
                            "dcn.credential.delete",
                            "fail",
                            "DCN delete could not remove stored auth token",
                            node=node_path,
                            pool_name=pool_name,
                            reason="credential_delete_failed",
                            token_principal=node_username,
                        )
                    else:
                        _admin_event(
                            "info",
                            "dcn.credential.delete",
                            "success",
                            "DCN delete removed stored auth token",
                            node=node_path,
                            pool_name=pool_name,
                            token_principal=node_username,
                        )
                else:
                    node_auth_token = None

                if not node_stanza.passive_delete():
                    _admin_log(
                        "error",
                        "DCN delete failed while removing stanza",
                        {"event": "dcn.delete", "status": "fail", "reason": "delete_stanza_failed"},
                        node=node_path,
                        pool_name=pool_name,
                    )
                    raise RestError(500, "Failed to delete node {0}".format(node_path))
                else:
                    _admin_log(
                        "info",
                        "DCN deleted",
                        {"event": "dcn.delete", "status": "success"},
                        node=node_path,
                        pool_name=pool_name,
                    )

                ru.set_conf_modification_time(pool_name, entity_type, local_session_key, logger)
                # Only attempt remote worker cleanup when the DCN credentials were valid.
                if node_stanza.credential_validation:
                    # disabling of inputs only takes place when node is successfully deleted.
                    # for disabling all the inputs(heads), heads is given as Zero.
                    ru.enable_heads_on_dcn(node_auth_token, 0, local_session_key, node_path, pool_name, logger)

                conf_info["data"]["message"] = "Node: {0} deleted successfully".format(node_path)
                conf_info["data"]["status"] = "200"
            else:
                _admin_log(
                    "error",
                    "DCN delete failed because stanza was not found",
                    {"event": "dcn.delete", "status": "fail", "reason": "not_found"},
                    node=node_path,
                )
                raise RestError(404, "Failed to find node {0}".format(node_path))

        except Exception as e:
            _admin_log(
                "exception",
                "DCN delete failed unexpectedly",
                {"event": "dcn.delete", "status": "fail", "reason": "exception", "error": str(e)},
                node=self.callerArgs.id,
            )
            raise e

    def handleCreate(self, conf_info):
        """When POST request is done with the first parameter as 'name' this method is called.
        All the required parameters for this method is settled up in setup() method."""
        try:
            args = self.callerArgs
            node_path = self.callerArgs.id

            local_session_key = self.getSessionKey()

            # getting all the passed arguments
            username = args.get("username")
            auth_token = args.get("auth_token")
            legacy_password = args.get("password")
            if (auth_token == [None] or auth_token is None) and legacy_password not in ([None], None):
                _admin_event(
                    "warning",
                    "dcn.create",
                    "observed",
                    "DCN create received deprecated password field and will treat it as auth token",
                    node=node_path,
                    reason="deprecated_password_field",
                )
                auth_token = legacy_password
            auth_token = _single_value(auth_token)
            heads = args.get("heads")
            pool_name = args.get("pool_name")
            requested_pool_name = _single_value(pool_name)
            _admin_log(
                "info",
                "DCN create requested",
                {"event": "dcn.create", "status": "start", "heads": _single_value(heads)},
                node=node_path,
                pool_name=requested_pool_name,
            )

            if not _has_value(auth_token):
                _admin_log(
                    "error",
                    "DCN create rejected because auth token is missing",
                    {"event": "dcn.create", "status": "fail", "reason": "missing_auth_token"},
                    node=node_path,
                    pool_name=requested_pool_name,
                )
                raise RestError(400, "Auth token is required when creating a data collection node.")

            node_stanza = False

            if node_path:
                node_stanza = HydraNodeStanza.from_name(
                    node_path, "Splunk_TA_vmware_inframon", host_path=local_host_path, session_key=local_session_key)

            # checking if stanza with the given name exist or not, validation only takes place in that case.
            if node_stanza:
                response = {"status": "invalid", "message": "Stanza with the same name already exists.",
                            "credential_validation": False, "addon_validation": False}
            else:
                response = ru.validate_dcn(
                    node_path, auth_token, heads, pool_name, local_session_key, logger,
                    legacy_username=username)

            if response['status'] == "invalid":
                raise RestError(400, str(response['message']))
            else:
                # adding validation response
                conf_info["data"]["validation_status"] = response["status"]
                conf_info["data"]["validation_message"] = response["message"]

                # as fields are valid and it is in list form.
                # node_path is not in list form.
                heads = int(heads[0] if isinstance(heads, list) else heads)
                pool_name = pool_name[0] if isinstance(pool_name, list) else pool_name
                token_principal = response.get("token_principal") or "token_user"

                # saving credentials in passwords.conf
                new_cred = SplunkStoredCredential("Splunk_TA_vmware_inframon", "nobody", token_principal,
                                                  sessionKey=local_session_key, host_path=local_host_path)
                new_cred.realm = node_path
                new_cred.password = auth_token
                new_cred.username = token_principal

                if not new_cred.passive_save():
                    _admin_event(
                        "error",
                        "dcn.credential.save",
                        "fail",
                        "DCN create failed to save auth token",
                        node=node_path,
                        pool_name=pool_name,
                        reason="credential_save_failed",
                        token_principal=token_principal,
                    )
                else:
                    _admin_event(
                        "info",
                        "dcn.credential.save",
                        "success",
                        "DCN create saved auth token",
                        node=node_path,
                        pool_name=pool_name,
                        token_principal=token_principal,
                    )

                # saving stanza in inframon_hydra_node.conf
                node_stanza = HydraNodeStanza("Splunk_TA_vmware_inframon", "nobody", node_path, sessionKey=local_session_key,
                                              host_path=local_host_path)
                node_stanza.host = node_path
                node_stanza.user = token_principal
                node_stanza.heads = heads
                node_stanza.credential_validation = response['credential_validation']
                node_stanza.addon_validation = response['addon_validation']
                node_stanza.pool_name = pool_name
                node_stanza.last_connectivity_checked = response["last_connectivity_checked"]

                # Only manage remote worker inputs when the DCN credentials are valid.
                if response["credential_validation"]:
                    ru.enable_heads_on_dcn(auth_token, heads, local_session_key, node_path, pool_name, logger)

                if node_stanza.passive_save():
                    # handling inframon_ta_vmware_pool.conf
                    _admin_log(
                        "info",
                        "DCN created",
                        {
                            "event": "dcn.create",
                            "status": "success",
                            "heads": heads,
                            "credential_validation": response["credential_validation"],
                            "addon_validation": response["addon_validation"],
                        },
                        node=node_path,
                        pool_name=pool_name,
                    )
                    ru.set_conf_modification_time(pool_name, entity_type, local_session_key, logger)
                    conf_info["data"]["status"] = "200"
                    conf_info["data"]["message"] = "Node stanza:{0} saved successfully.".format(node_path)
                else:
                    _admin_log(
                        "error",
                        "DCN create failed while saving stanza",
                        {"event": "dcn.create", "status": "fail", "reason": "save_stanza_failed"},
                        node=node_path,
                        pool_name=pool_name,
                    )
                    raise RestError(500, "Error in saving node stanza: {0}.".format(node_path))
        except Exception as e:
            _admin_log(
                "exception",
                "DCN create failed unexpectedly",
                {"event": "dcn.create", "status": "fail", "reason": "exception", "error": str(e)},
                node=self.callerArgs.id,
            )
            raise e

    def handleList(self, conf_info):
        """When GET request is done on the endpoint this method is called,
        It returns the details of all the configured DCN in json format."""
        try:

            local_session_key = self.getSessionKey()

            # getting all the stanzas of inframon_hydra_node.conf
            stanzas = HydraNodeStanza.all(sessionKey=local_session_key)
            stanzas = stanzas.filter_by_app("Splunk_TA_vmware_inframon")
            stanzas._owner = "nobody"

            # preparing response from stanza list
            nodes = {str(stanza.host): {"host_path": stanza.host, "username": stanza.user,
                                        "credential_validation": stanza.credential_validation,
                                        "addon_validation": stanza.addon_validation, "heads": stanza.heads,
                                        "pool_name": stanza.pool_name,
                                        "last_connectivity_checked": stanza.last_connectivity_checked.strftime(
                                            "%Y-%m-%dT%H:%M:%S.%f")} for stanza in stanzas}

            conf_info["data"]["nodes"] = json.dumps(nodes)

        except Exception as e:
            logger.exception(e)
            raise e

    def handleEdit(self, conf_info):
        """when POST request is done with the target on endpoint, this method is called.
        All the required parameters for this method is settled up in setup() method."""
        try:
            args = self.callerArgs

            # target_node is node to be edited.
            target_node = self.callerArgs.id
            local_session_key = self.getSessionKey()

            # getting passed arguments.
            # node_path is a node given as a argument to edit.
            node_path = args.get("node")
            username = args.get("username")
            auth_token = args.get("auth_token")
            legacy_password = args.get("password")
            if (auth_token == [None] or auth_token is None) and legacy_password not in ([None], None):
                _admin_event(
                    "warning",
                    "dcn.edit",
                    "observed",
                    "DCN edit received deprecated password field and will treat it as auth token",
                    node=target_node,
                    reason="deprecated_password_field",
                )
                auth_token = legacy_password
            requested_auth_token = _single_value(auth_token)
            heads = args.get("heads")
            pool_name = args.get("pool_name")
            requested_pool_name = _single_value(pool_name)
            _admin_log(
                "info",
                "DCN edit requested",
                {"event": "dcn.edit", "status": "start", "heads": _single_value(heads)},
                node=target_node,
                pool_name=requested_pool_name,
            )

            # target_node is checked explicitly to not change validate_dcn
            if target_node:
                validated_node_path = re.search(
                    "^\s*https?:\/\/[A-Za-z0-9\.\-_]+:\d+\/?\s*$", target_node)
                if validated_node_path is None:
                    _admin_event(
                        "error",
                        "dcn.edit",
                        "fail",
                        "DCN edit rejected because the current node name is invalid",
                        node=target_node,
                        pool_name=requested_pool_name,
                        reason="invalid_current_node",
                    )
                    raise RestError(400, "Node name passed to edit worker node is not valid.")
                else:
                    node_stanza = HydraNodeStanza.from_name(target_node, "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                            session_key=local_session_key)

            else:
                _admin_event(
                    "error",
                    "dcn.edit",
                    "fail",
                    "DCN edit rejected because no current node name was supplied",
                    pool_name=requested_pool_name,
                    reason="missing_current_node",
                )
                raise RestError(400, "No node name passed to edit, cannot edit nothing!")

            # checking if stanza with the given new name of stanza exists.
            proposed_node_path = node_path[0] if isinstance(node_path, list) else node_path
            to_node_stanza = HydraNodeStanza.from_name(str(proposed_node_path), "Splunk_TA_vmware_inframon", host_path=local_host_path,
                                                       session_key=local_session_key)
            stored_cred = False
            # checking that stanza to be edited must exists and new name provided to edit must not exists
            if not node_stanza:
                response = {"status": "invalid", "message": "No stanza with the given name exists.",
                            "credential_validation": False, "addon_validation": False}
            elif to_node_stanza and str(proposed_node_path) != target_node:
                response = {"status": "invalid", "message": "Stanza with the given new name already exists.",
                            "credential_validation": False, "addon_validation": False}
            else:
                # getting credentials of stanza currently being edited.
                _admin_event(
                    "debug",
                    "dcn.edit",
                    "observed",
                    "DCN edit loaded stored credential for the current node",
                    node=target_node,
                    pool_name=requested_pool_name,
                    token_principal=node_stanza.user,
                )
                stored_cred = SplunkStoredCredential.from_name(
                    SplunkStoredCredential.build_name(node_stanza.host, node_stanza.user), app="Splunk_TA_vmware_inframon",
                    owner="nobody", host_path=local_host_path, session_key=local_session_key)
                current_auth_token = stored_cred.clear_password if stored_cred else ""
                auth_token_supplied = _has_value(requested_auth_token)
                effective_auth_token = requested_auth_token if auth_token_supplied else current_auth_token
                if not auth_token_supplied:
                    if not _has_value(effective_auth_token):
                        response = {"status": "invalid", "message": "No stored auth token exists for this DCN. Provide a token to continue.",
                                    "credential_validation": False, "addon_validation": False}
                    else:
                        _admin_log(
                            "info",
                            "DCN edit will reuse stored auth token",
                            {"event": "dcn.edit", "status": "reused_credentials"},
                            node=target_node,
                            pool_name=requested_pool_name,
                        )
                        response = ru.validate_dcn(node_path, effective_auth_token, heads, pool_name, local_session_key, logger,
                                                   legacy_username=username)
                else:
                    # validating given inputs
                    response = ru.validate_dcn(node_path, effective_auth_token, heads, pool_name, local_session_key, logger,
                                               legacy_username=username)

            if response["status"] == "invalid":
                conf_info["data"]["message"] = str(response['message'])
                raise RestError(400, str(response['message']))
            else:
                # adding validation response
                conf_info["data"]["validation_status"] = response["status"]
                conf_info["data"]["validation_message"] = response["message"]

                node_path = node_path[0] if isinstance(node_path, list) else node_path
                heads = int(heads[0] if isinstance(heads, list) else heads)
                pool_name = pool_name[0] if isinstance(pool_name, list) else pool_name
                token_principal = response.get("token_principal") or node_stanza.user or "token_user"

                # old auth token is saved for later use.
                old_auth_token = ""
                if stored_cred:
                    old_auth_token = stored_cred.clear_password
                effective_auth_token = requested_auth_token if _has_value(requested_auth_token) else old_auth_token

                cred_deleted = False
                old_username = node_stanza.user
                old_pool_name = node_stanza.pool_name

                # first checking if stanza name is changed, in that case
                # old stanza will be deleted and new one will be created.
                if target_node != node_path:
                    _admin_event(
                        "info",
                        "dcn.edit",
                        "observed",
                        "DCN edit is renaming the node and rebuilding the stanza",
                        node=target_node,
                        pool_name=old_pool_name,
                        reason="node_renamed",
                        new_node=node_path,
                    )

                    if stored_cred:
                        _admin_event(
                            "info",
                            "dcn.credential.delete",
                            "start",
                            "DCN edit is removing obsolete auth token mapping",
                            node=target_node,
                            pool_name=old_pool_name,
                            token_principal=old_username,
                        )
                        if stored_cred.passive_delete():
                            cred_deleted = True
                            _admin_event(
                                "info",
                                "dcn.credential.delete",
                                "success",
                                "DCN edit removed obsolete auth token mapping",
                                node=target_node,
                                pool_name=old_pool_name,
                                token_principal=old_username,
                            )
                        else:
                            _admin_event(
                                "warning",
                                "dcn.credential.delete",
                                "fail",
                                "DCN edit could not remove obsolete auth token mapping",
                                node=target_node,
                                pool_name=old_pool_name,
                                reason="credential_delete_failed",
                                token_principal=old_username,
                            )

                    if not node_stanza.passive_delete():
                        _admin_event(
                            "error",
                            "dcn.delete",
                            "fail",
                            "DCN edit failed while deleting the original node stanza",
                            node=target_node,
                            pool_name=old_pool_name,
                            reason="delete_stanza_failed",
                        )
                        raise RestError(500, "Failed to delete node {0}".format(target_node))

                    # disabling of inputs only takes place when node is successfully deleted.
                    # For disabling all the inputs(heads), @heads parameter is given as zero.
                    ru.enable_heads_on_dcn(old_auth_token, 0, local_session_key, target_node, old_pool_name, logger)
                    node_stanza = HydraNodeStanza(
                        "Splunk_TA_vmware_inframon", "nobody", node_path, sessionKey=local_session_key,
                        host_path=local_host_path)

                credentials_changed = (
                    target_node != node_path or
                    node_stanza.user != token_principal or
                    (_has_value(requested_auth_token) and old_auth_token != effective_auth_token)
                )
                if credentials_changed:
                    _admin_event(
                        "info",
                        "dcn.credential.save",
                        "start",
                        "DCN edit is updating auth token mapping",
                        node=node_path,
                        pool_name=pool_name,
                        token_principal=token_principal,
                        credentials_changed=True,
                    )
                    # this is for deleting the old creds stanza when principal is changed.
                    if not cred_deleted and old_username:
                        prev_realm = target_node if target_node != node_path else node_path
                        prev_cred = SplunkStoredCredential.from_name(
                            SplunkStoredCredential.build_name(prev_realm, str(old_username)),
                            app="Splunk_TA_vmware_inframon",
                            owner="nobody",
                            host_path=local_host_path,
                            session_key=local_session_key)
                        if prev_cred:
                            if not prev_cred.passive_delete():
                                _admin_event(
                                    "warning",
                                    "dcn.credential.delete",
                                    "fail",
                                    "DCN edit could not delete replaced auth token mapping",
                                    node=prev_realm,
                                    pool_name=pool_name,
                                    reason="credential_delete_failed",
                                    token_principal=old_username,
                                )
                            else:
                                _admin_event(
                                    "info",
                                    "dcn.credential.delete",
                                    "success",
                                    "DCN edit deleted replaced auth token mapping",
                                    node=prev_realm,
                                    pool_name=pool_name,
                                    token_principal=old_username,
                                )

                    new_cred = SplunkStoredCredential("Splunk_TA_vmware_inframon", "nobody", token_principal,
                                                      sessionKey=local_session_key, host_path=local_host_path)
                    new_cred.realm = node_path
                    new_cred.password = effective_auth_token
                    new_cred.username = token_principal

                    if not new_cred.passive_save():
                        _admin_event(
                            "error",
                            "dcn.credential.save",
                            "fail",
                            "DCN edit failed to save auth token",
                            node=node_path,
                            pool_name=pool_name,
                            reason="credential_save_failed",
                            token_principal=token_principal,
                        )
                    else:
                        _admin_event(
                            "info",
                            "dcn.credential.save",
                            "success",
                            "DCN edit saved auth token",
                            node=node_path,
                            pool_name=pool_name,
                            token_principal=token_principal,
                        )

                node_stanza.host = node_path
                node_stanza.user = token_principal
                node_stanza.pool_name = pool_name
                node_stanza.credential_validation = response['credential_validation']
                node_stanza.addon_validation = response['addon_validation']
                node_stanza.last_connectivity_checked = response["last_connectivity_checked"]

                # changing in the inputs of stanza as number of heads is changed.
                if node_stanza.heads != heads:
                    node_stanza.heads = heads
                    if response["credential_validation"]:
                        ru.enable_heads_on_dcn(effective_auth_token, heads, local_session_key, node_path, pool_name, logger)

                if node_stanza.passive_save():
                    ru.set_conf_modification_time(pool_name, entity_type, local_session_key, logger)
                    if pool_name != old_pool_name:
                        # removing sessions residing on DCN
                        ru.clear_session(node_path, effective_auth_token, local_session_key, logger)
                        ru.set_conf_modification_time(old_pool_name, entity_type, local_session_key, logger)
                    _admin_log(
                        "info",
                        "DCN edited",
                        {
                            "event": "dcn.edit",
                            "status": "success",
                            "heads": heads,
                            "credential_validation": response["credential_validation"],
                            "addon_validation": response["addon_validation"],
                            "token_rotated": _has_value(requested_auth_token),
                            "node_renamed": target_node != node_path,
                        },
                        node=node_path,
                        pool_name=pool_name,
                    )
                    conf_info["data"]["status"] = "200"
                    conf_info["data"]["message"] = "Stanza: {0} edited successfully.".format(target_node)
                else:
                    _admin_log(
                        "error",
                        "DCN edit failed while saving stanza",
                        {"event": "dcn.edit", "status": "fail", "reason": "save_stanza_failed"},
                        node=node_path,
                        pool_name=pool_name,
                    )
                    raise RestError(500, "Error in editing node stanza: {0}".format(target_node))

        except Exception as e:
            _admin_log(
                "exception",
                "DCN edit failed unexpectedly",
                {"event": "dcn.edit", "status": "fail", "reason": "exception", "error": str(e)},
                node=self.callerArgs.id,
            )
            raise e


admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
