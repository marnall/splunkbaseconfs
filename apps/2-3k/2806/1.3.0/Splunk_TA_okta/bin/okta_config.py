import logging
import os

from splunktalib.common import log
from splunktalib.conf_manager.conf_manager import ConfManager
from splunktalib.credentials import CredentialManager

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)


class OktaConfigException(Exception):
    "Exception for Okta config manager errors"
    pass


def check_conf_mgr_result(success, msg):
    """
    Check the result and throw exception if needed
    """
    if success:
        return
    _LOGGER.error(msg)
    raise OktaConfigException(msg)


class OktaConfig(object):
    def __init__(self, splunk_uri, session_key, checkpoint_dir):
        self.session_key = session_key
        self.conf_mgr = ConfManager(splunk_uri,
                                    session_key,
                                    app_name="Splunk_TA_okta")
        self.cred_mgr = CredentialManager(session_key=session_key,
                                          splunkd_uri=splunk_uri,
                                          app="Splunk_TA_okta")
        self.checkpoint_dir = checkpoint_dir

        self.data_input_type = "okta"
        self.conf_file_name = "okta"
        self.conf_proxy_stanza_name = "okta_proxy"
        self.conf_log_stanza_name = "okta_loglevel"
        self.conf_okta_server_stanza_name = "okta_server"
        self.cred_proxy_stanza_name = "__Splunk_TA_okta_proxy__"
        self.cred_okta_server_stanza_name = "__Splunk_TA_okta_server__"

        self.encrypted_display_str = "********"

        self.fields_proxy = ("proxy_enabled", "proxy_username", "proxy_type",
                             "proxy_password", "proxy_url", "proxy_port",
                             "proxy_rdns")

        self.fields_log = ("loglevel")

        self.fields_okta_server = ("custom_cmd_enabled", "okta_server_url",
                                   "okta_server_token")

        self.fields_data_input = ("metrics", "page_size", "start_date", "url",
                                  "token", "disabled", "interval", "source",
                                  "sourcetype", "index", "host", "batch_size")

    def get_cred_stanza_name(self, name):
        check_conf_mgr_result(name, "The stanza name is None.")
        return "".join(("__Splunk_TA_okta_inputs_", name))

    def _encrypt_stanza_if_needed(self, cred_stanza, conf_stanza, key_values,
                                  encrypt_fields, check_field):
        """
        Encrypt stanza if the `encrypt_fields` is not encrypted. If the
        `check_field` is not exist, remove the old credential and clear the
        `encrypt_fields` in conf file. Otherwise check if the stanza is
        encrypted or not, is not encrypted then do encrypt and replace
        the sensitive fields with encrypted string in conf file.

        :param cred_stanza: stanza name in passwords.conf.
        :param conf_stanza: stanza name in okta.conf.
        :param key_values: values of stanza as `dict`.
        :param encrypt_fields: iterable fields need to encrypt.
        :param check_field: field used to check if necessary info is exist.
        """
        if not key_values.get(check_field, ''):
            _LOGGER.info('[%s] %s is empty, delete the encrypted %s',
                         cred_stanza, check_field, ','.join(encrypt_fields))
            self._delete_credential(cred_stanza)

            for k in encrypt_fields:
                key_values[k] = ''
            self._set_raw_stanza(conf_stanza, key_values, stanza_type='conf')
            return

        conf = self._get_raw_stanza(conf_stanza)
        if self.encrypted_display_str \
                in [conf.get(ef, '') for ef in encrypt_fields]:
            _LOGGER.info('[%s] is already been encrypted, cancel encrypting',
                         conf_stanza)
            return

        self._set_raw_stanza(cred_stanza,
                             {k: key_values[k] for k in encrypt_fields},
                             stanza_type="cred")

        _LOGGER.info("Finish encryption. Set them to %s",
                     self.encrypted_display_str)

        for k in encrypt_fields:
            key_values[k] = self.encrypted_display_str
        self._set_raw_stanza(conf_stanza, key_values, stanza_type='conf')

        _LOGGER.info("Updating [%s] success", conf_stanza)

    def update_okta_conf(self, key_values):
        _LOGGER.info("Update okta.conf")
        key_values = key_values.copy()

        stanzas = [(self.cred_proxy_stanza_name, self.conf_proxy_stanza_name,
                    ['proxy_username', 'proxy_password'], 'proxy_username'),
                   (self.cred_okta_server_stanza_name,
                    self.conf_okta_server_stanza_name,
                    ['okta_server_url', 'okta_server_token'],
                    'okta_server_url')]
        for cred, conf, efs, cf in stanzas:
            try:
                self._encrypt_stanza_if_needed(cred, conf, key_values, efs, cf)
            except OktaConfigException:
                _LOGGER.error("Failure on encrypting stanza", exc_info=1)

    def update_input_conf(self, stanza_name, key_values):
        _LOGGER.info("Update inputs.conf")
        key_values = key_values.copy()
        if key_values.get("eai:acl"):
            app_name = key_values.get("eai:acl").get("app")
        else:
            app_name = "Splunk_TA_okta"
        self._set_raw_stanza(stanza_name,
                             key_values,
                             stanza_type="data_input",
                             app_name=app_name)

    def get_okta_conf(self):
        conf_stanza_log = self._get_raw_stanza(self.conf_log_stanza_name)
        log.Logs().set_level(conf_stanza_log.get("loglevel", "INFO"))
        conf_stanza_proxy = self._get_raw_stanza(self.conf_proxy_stanza_name)
        conf_stanza_okta_server = self._get_raw_stanza(
            self.conf_okta_server_stanza_name)
        username = conf_stanza_proxy.get("proxy_username", "")
        password = conf_stanza_proxy.get("proxy_password", "")

        _LOGGER.info("Try to get encrypted proxy username & password")

        if self.encrypted_display_str in (username, password):
            encrypted_proxy_user_pwd = self._get_raw_stanza(
                self.cred_proxy_stanza_name,
                stanza_type="cred")
            decrypted_username = encrypted_proxy_user_pwd.get(
                self.cred_proxy_stanza_name)['proxy_username']
            decrypted_password = encrypted_proxy_user_pwd.get(
                self.cred_proxy_stanza_name)['proxy_password']
            conf_stanza_proxy["proxy_username"] = decrypted_username \
                if username == self.encrypted_display_str else username
            conf_stanza_proxy["proxy_password"] = decrypted_password \
                if password == self.encrypted_display_str else password

        server_url = conf_stanza_okta_server.get("okta_server_url", "")
        server_token = conf_stanza_okta_server.get("okta_server_token", "")
        _LOGGER.info("Try to get encrypted okta server url & token.")
        if self.encrypted_display_str in (server_url, server_token):
            encrypted_server_url_token = self._get_raw_stanza(
                self.cred_okta_server_stanza_name,
                stanza_type="cred")
            decrypted_server_url = encrypted_server_url_token.get(
                self.cred_okta_server_stanza_name)['okta_server_url']
            decrypted_server_token = encrypted_server_url_token.get(
                self.cred_okta_server_stanza_name)['okta_server_token']
            conf_stanza_okta_server["okta_server_url"] = decrypted_server_url \
                if server_url == self.encrypted_display_str else server_url
            conf_stanza_okta_server["okta_server_token"] = decrypted_server_token \
                if server_token == self.encrypted_display_str else server_token
        conf_stanza_proxy.update(conf_stanza_log)
        conf_stanza_proxy.update(conf_stanza_okta_server)
        return conf_stanza_proxy

    def update_data_input(self, name, key_values, check_success=True):
        _LOGGER.info("Update data input [%s]", name)
        update_cnt = {
            'interval':key_values.get('interval'),
            'token': key_values.get('token'),
            'metrics': key_values.get('metrics'),
            'url': key_values.get('url')
        }
        if key_values.get('start_date'):
            update_cnt['start_date'] = key_values.get('start_date')
        if key_values.get("eai:acl"):
            app_name = key_values.get("eai:acl").get("app")
        else:
            app_name = "Splunk_TA_okta"
        try:
            self.conf_mgr.update_data_input("okta", name, update_cnt, app_name)
            for item in filter(lambda x: x in key_values.keys(),['interval', 'token', 'start_date']):
                _LOGGER.info('Set {0} of the stanza {1} in inputs.conf to be {2}'
                             .format(item, name, key_values.get(item)))
        except Exception:
            _LOGGER.error('Failed to update the stanza {} in inputs.conf'.format(name))
            return False
        return True

    def remove_expired_credentials(self):
        inputs = self._get_raw_stanza(stanza_type="data_input",
                                      check_exist=False) or ()
        creds = self._get_raw_stanza(stanza_type="cred", check_exist=False)
        input_names = set(self.get_cred_stanza_name(data_input.get("stanza")) \
                          for data_input in inputs)
        for name in creds:
            if name.startswith(
                    "__Splunk_TA_okta_inputs") and name not in input_names:
                _LOGGER.info(
                    "Remove credential %s since related data input has been deleted",
                    name)
                self._delete_credential(name)

    def remove_expired_ckpt(self):
        inputs = self._get_raw_stanza(stanza_type="data_input",
                                      check_exist=False)
        if inputs:
            ckpt_names = set("okta_{}.ckpt".format(data_input.get('stanza'))
                             for data_input in inputs)

            files = os.listdir(self.checkpoint_dir)
            for name in files:
                ckpt_path = os.path.join(self.checkpoint_dir, name)
                if name.startswith("okta_") and name.endswith(".ckpt") and \
                                name not in ckpt_names and os.path.isfile(ckpt_path):
                    _LOGGER.info(
                        "Remove checkpoint %s since related data input has been deleted",
                        ckpt_path)
                    try:
                        os.remove(ckpt_path)
                    except:
                        _LOGGER.error("Cannot remove checkpoint file %s",
                                      ckpt_path)

    def get_data_input(self, name):
        _LOGGER.info("Get data input by name %s", name)
        input_stanza = self._get_raw_stanza(name, stanza_type="data_input")
        input_stanza["url"] = input_stanza.get("url", "").strip().lower()
        if not input_stanza.get("metrics", "") == "refresh_token":
            token = input_stanza.get("token", "")
            input_stanza['raw_token'] = token
            if token == self.encrypted_display_str:
                encrypted_token = self._get_encrypted_token(name, check_exist=False)
                if not encrypted_token:
                    check_conf_mgr_result(False, "Cannot get the encrypted token")
                input_stanza["token"] = encrypted_token

        return input_stanza

    def encrypt_data_input(self, name, key_values, check_success=True):
        success = self._encrypt_data_input(name, key_values)
        if not success:
            if check_success:
                msg = "Failed to encrypt token for data input [{}]".format(name)
                check_conf_mgr_result(False, msg)
            else:
                return False
        return True

    def _delete_credential(self, name):
        return self.cred_mgr.delete(name)

    def _encrypt_data_input(self, name, key_values, check_success=True):
        token = key_values.get("token", "")

        if not token:
            return False

        name = self.get_cred_stanza_name(name)
        success = self._set_raw_stanza(name, {"token": token},
                                       stanza_type="cred", check_success=check_success)

        key_values["token"] = self.encrypted_display_str

        return success

    def _get_encrypted_token(self, name, check_exist=True):
        name = self.get_cred_stanza_name(name)
        decrypt = self._get_raw_stanza(name,
                                       stanza_type="cred",
                                       check_exist=check_exist)
        if decrypt:
            return decrypt.get(name).get("token")
        return None

    def _get_raw_stanza(self,
                        stanza_name=None,
                        stanza_type="conf",
                        check_exist=True):
        stanza_type = stanza_type.strip().lower()
        if stanza_type == "conf":
            stanza = self.conf_mgr.get_conf(self.conf_file_name, stanza_name)
        elif stanza_type == "data_input":
            stanza = self.conf_mgr.get_data_input(self.data_input_type,
                                                  stanza_name)
        else:
            stanza = self.cred_mgr.get_clear_password(stanza_name)

        if check_exist:
            check_conf_mgr_result(
                stanza, "Failed to get stanza {0} by {1} manager.".format(
                    stanza_name, stanza_type))
        return stanza

    def _check_key_value_for_stanza(self, k, v, stanza_name):
        if v is None:
            return False
        candidates = [(self.fields_log, self.conf_log_stanza_name),
                      (self.fields_proxy, self.conf_proxy_stanza_name),
                      (self.fields_okta_server,
                       self.conf_okta_server_stanza_name)]
        return any([k in fields and stanza_name == stanza
                    for fields, stanza in candidates])

    def _set_raw_stanza(self,
                        stanza_name,
                        key_values,
                        stanza_type="conf",
                        app_name=None,
                        check_success=True):
        app_name = app_name or "Splunk_TA_okta"
        stanza_type = stanza_type.strip().lower()

        new_values = {}
        if stanza_type == "conf":
            for k, v in key_values.items():
                if self._check_key_value_for_stanza(k, v, stanza_name):
                    new_values[k] = v
            success = self.conf_mgr.set_stanza(self.conf_file_name,
                                               stanza_name, new_values)
        elif stanza_type == "data_input":
            for k, v in key_values.items():
                if v is not None and k in self.fields_data_input:
                    new_values[k] = v
            success = self.conf_mgr.set_data_input_stanza(
                self.data_input_type, stanza_name, new_values, app_name)
        else:
            success = self.cred_mgr.update({stanza_name: key_values})

        if check_success:
            check_conf_mgr_result(
                success, "Failed to update stanza {0} by {1} manager.".format(
                    stanza_name, stanza_type))

        return success
