import sys

# add nba bin to sys.path so we can use nbalib package
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'network_behavior_analytics', 'bin']))

import splunk.rest

from nbalib import validators
from nbalib import logger
from nbalib import confs
from nbalib import rest
from nbalib import api

from nbalib.asoc3.six.moves import urllib_parse
from nbalib.asoc3 import six

class APIMessages(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        config = confs.Config(self.sessionKey)
        api_messages = api.Messages.get(config)

        api_messages = self._append_no_data(api_messages, config)
        api_messages = self._append_no_api_key(api_messages)

        rest.Response.set(self.response, {'messages': api_messages})

    def _append_no_data(self, api_messages, config):
        data_sections = []
        for section_name in validators.Sections.data:
            self._append_no_data_section(section_name, data_sections, config)

        if len(data_sections) == len(validators.Sections.data):
            api_messages.append({
                'body': "No data to process. Please check data provider health via the Data Location "
                        "tab and review your monitoring scope via the Groups tab.",
                'level': api.Messages.ERROR,
            })

        return api_messages

    @staticmethod
    def _append_no_data_section(section_name, data_sections, config):
        try:
            no_data_counter = int(config.get_from_stanza('no_data_counter', stanza=section_name))
            master_node = config.is_enabled('master_node', default=True)
        except:
            no_data_counter = 0
            master_node = True

        if master_node and no_data_counter >= api.NO_DATA_THRESHOLD:
            data_sections.append(section_name)

    def _append_no_api_key(self, api_messages):
        try:
            sp = confs.StoragePasswords(self.sessionKey)
            api_key = sp.get_api_key()
        except confs.PerrmisionException:
            return api_messages
        except Exception as exc:
            api_messages.append({
                'level': api.Messages.ERROR,
                'body': str(exc),
            })
            return api_messages

        if isinstance(api_key, six.string_types):
            if not api_key.strip():
                api_messages.append({
                    'body': "No API key found. To enable scoring of your data please generate a free "
                            "key via the Settings tab.",
                    'level': api.Messages.WARN,
                })

        return api_messages


class APIAccountStatus(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        try:
            config = confs.Config(self.sessionKey)
            account_status = self._get_status(config)
        except:
            account_status = self._default_status()

        rest.Response.set(self.response, account_status)

    def handle_POST(self):
        api_key = self.args.get('api_key', '').strip()
        if not api_key:
            rest.Response.error(self.response, "API key could not be empty.")
            return

        try:
            api.ApiKeyStorage.save(api_key, self.sessionKey)
        except Exception:
            rest.Response.error(self.response, "Unable to save API key status, please save your API key again.")
            return

        try:
            config = confs.Config(self.sessionKey)
        except:
            msg = "Unable to open configuration file, please save your API key again."
            rest.Response.error(self.response, msg)
            return

        config_account_status = self._get_status(config)
        rest.Response.set(self.response, config_account_status)

    def _get_status(self, config):
        try:
            sp = confs.StoragePasswords(self.sessionKey)
            api_key = sp.get_api_key()

            valid = config.is_enabled("api_key_valid")
            registered = config.is_enabled("api_key_registered")

            status = self._create_status(api_key, valid, registered)
        except confs.PerrmisionException:
            status = self._default_status()
            status['not_admin'] = True
        except:
            status = self._default_status()

        return status

    def _default_status(self):
        return self._create_status("", False, False)

    @staticmethod
    def _create_status(key, valid, registered, not_admin=False):
        return {'key': key if key else "", 'valid': valid, 'registered': registered, 'not_admin': not_admin}


class APIKeyRequest(splunk.rest.BaseRestHandler):
    def handle_POST(self):
        details, invalid_fields = self.parse_details(self.args)
        if invalid_fields:
            rest.Response.error_fields(self.response, invalid_fields)
            return

        if not validators.Permissions.is_config_writable(self.sessionKey):
            rest.Response.error(self.response, logger.MessageConfigNotWritable().ui_message)
            return

        alphasoc_api = api.API(self.sessionKey)
        response_generate = alphasoc_api.key_request()

        if response_generate.has_error():
            rest.Response.error(self.response, response_generate.error)
            return

        if not response_generate.key:
            rest.Response.error(self.response, "Licensing server didn't return the key.")
            return

        api_key = response_generate.key
        response_body = {'key': api_key}

        response_register = alphasoc_api.account_register(api_key, details)
        if response_register.has_error():
            response_body['error'] = response_register.error
            rest.Response.set(self.response, response_body, code=400)
            return

        rest.Response.set(self.response, response_body)

    @staticmethod
    def parse_details(details_args):
        required_fields = ['name', 'organization', 'email']
        details = {'phone': ""}

        invalid_fields = {}
        for field in required_fields:
            details[field] = details_args.get(field, "").strip()[:255]
            if not details[field]:
                invalid_fields[field] = 'This field is required'
                continue

            if field == 'email' and not validators.Email.is_valid(details[field]):
                invalid_fields[field] = 'Enter a valid e-mail address'

        details['phone'] = details_args.get('phone', "").strip()[:255]

        return details, invalid_fields


class APIKeyReset(splunk.rest.BaseRestHandler):
    def handle_POST(self):
        email = self.args.get('email', '').strip()
        if not validators.Email.is_valid(email):
            rest.Response.error(self.response, "Email address is invalid.")
            return

        alphasoc_api = api.API(self.sessionKey)
        response = alphasoc_api.key_reset(email)

        if response.has_error():
            rest.Response.error(self.response, response.error)
            return

        rest.Response.set(self.response, {})


class APIAccountRegister(splunk.rest.BaseRestHandler):
    def handle_POST(self):
        details, invalid_fields = APIKeyRequest.parse_details(self.args)
        if invalid_fields:
            rest.Response.error_fields(self.response, invalid_fields)
            return

        try:
            sp = confs.StoragePasswords(self.sessionKey)
            api_key = sp.get_api_key()
        except:
            rest.Response.error(self.response, "Activation requires a valid API key.")
            return

        alphasoc_api = api.API(self.sessionKey)
        response = alphasoc_api.account_register(api_key, details)

        if response.has_error():
            rest.Response.error(self.response, response.error)
            return

        # Make additional account status request to get a new messages from API.
        try:
            account_status = alphasoc_api.account_status(api_key)
            self._update_config_values(account_status)
        except:
            pass

        rest.Response.set(self.response, {})

    def _update_config_values(self, account_status):
        config = confs.Config(self.sessionKey)
        config.begin_batch()

        config.set('api_key_valid', account_status.valid)
        config.set('api_key_registered', account_status.registered)

        api.Messages.set(account_status.messages, config)

        config.commit()


class APIUrl(splunk.rest.BaseRestHandler):
    def handle_GET(self):
        try:
            config = confs.Config(self.sessionKey)
            url = config.get('api_url', "")
        except:
            url = ""

        rest.Response.set(self.response, {'url': url})

    def handle_POST(self):
        url = self.args.get('url', "")

        if not isinstance(url, six.string_types):
            rest.Response.error(self.response, "URL parameter is invalid.")
            return

        url = url.strip()
        if not url:
            rest.Response.error(self.response, "URL parameter is required.")
            return

        parts = urllib_parse.urlsplit(url)
        if parts.scheme != "https":
            rest.Response.error(self.response, "API communications requires HTTPS protocol.")
            return
        elif not parts.scheme:
            rest.Response.error(self.response, "API URL must include the protocol (eg. http://).")
            return

        if not url.endswith("/"):
            url += "/"

        try:
            config = confs.Config(self.sessionKey)
            config.set('api_url', url)
        except:
            rest.Response.error(self.response, "Unable to save API address in configuration file.")
            return

        rest.Response.set(self.response, {})
