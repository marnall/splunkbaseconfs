import logging
import os
import sys
import uuid
import splunk.admin as admin
import environments_schema
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import hashlib
import base_eai_handler
import log_helper

if sys.platform == 'win32':
    import msvcrt

    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

# Setup the handler
logger = log_helper.setup(logging.INFO, 'EnvironmentsEAIHandler', 'environments_handler.log')

class EnvironmentsEAIHandler(base_eai_handler.BaseEAIHandler):
    def setup(self):
        # Add our supported args
        for arg in environments_schema.ALL_FIELDS:
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """
        Called when user invokes the "list" action.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environments list requested.')

        enable_metrics_search = self.get_param('enable_metrics_search', default='0')
        if enable_metrics_search == '0':
            environment_link_alternate_errors_status_map = {}
        else:
            poller_metrics_earliest_time = self.get_param('poller_metrics_earliest_time', default='-1')
            if poller_metrics_earliest_time == '-1':
                # Fetch the formatted poller metrics lookback time
                poller_metrics_formatted_earliest_time = self.formatted_poller_metrics_earliest_time_fetch()
            else:
                # Format the poller_metrics_earliest_time override provided in the GET param
                poller_metrics_formatted_earliest_time = '-%ss' % poller_metrics_earliest_time

            # Fetch error metrics and most recent network status
            environment_link_alternate_errors_status_map = self.oneshot_metrics_search(poller_metrics_formatted_earliest_time, self.appName, is_environment=True)

        # Fetch from environments conf handler
        conf_handler_path = self.get_conf_handler_path_name('environments', 'nobody')
        environments_eai_response_payload = self.simple_request_eai(conf_handler_path, 'list', 'GET', get_args={'count': -1})

        # Add link alternate (without mgmt, scheme, host, port) to list response
        for environment in environments_eai_response_payload['entry']:
            environment_link_alternate = environment['links']['alternate'].replace('/configs/conf-environments/', '/environments/')
            environment['content']['environment_link_alternate'] = environment_link_alternate

            environment_errors_status_entry = environment_link_alternate_errors_status_map.get(environment_link_alternate)

            if environment_errors_status_entry:
                environment['content']['network_error_count_sparkline'] = environment_link_alternate_errors_status_map[
                    environment_link_alternate].get('sparkline', '')
                environment['content']['most_recent_environment_status'] = environment_link_alternate_errors_status_map[
                    environment_link_alternate].get('status_code', '')
                environment['content']['most_recent_environment_message'] = environment_link_alternate_errors_status_map[
                    environment_link_alternate].get('message', '')
                environment['content']['most_recent_environment_timestamp'] = environment_link_alternate_errors_status_map[
                    environment_link_alternate].get('_time', '')
            else:
                environment['content']['network_error_count_sparkline'] = ''
                environment['content']['most_recent_environment_status'] = ''
                environment['content']['most_recent_environment_message'] = ''
                environment['content']['most_recent_environment_timestamp'] = ''

            environment['content']['environment_name'] = environment['name']

            # Check for tags
            environment['content']['tags'] = environment['content'].get('tags', '')

            # Check for password_link_alternate
            environment['content']['password_link_alternate'] = environment['content'].get('password_link_alternate', '')

            # Check for splunk_web_uri
            environment['content']['splunk_web_uri'] = environment['content'].get('splunk_web_uri', '')

        self.set_conf_info_from_eai_payload(confInfo, environments_eai_response_payload)

    def handleCreate(self, confInfo):
        """
        Called when user invokes the "create" action.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environments creation requested.')

        # Validate and extract correct POST params
        server_params = self.validate_server_schema_params()
        auth_params = self.validate_auth_schema_params()
        params = auth_params.copy()
        params.update(server_params)

        # Password creation
        password_link_alternate = self.password_create(params['username'], params['password'])

        # environments.conf creation and response
        post_args = {
            'name': params['name'],
            'mgmt_scheme_host_port': params['mgmt_scheme_host_port'],
            'username': params['username'],
            'splunk_web_uri': params['splunk_web_uri'],
            'tags': params['tags'],
            'password_link_alternate': password_link_alternate,
            'hec_url': params['hec_url'],
            'hec_token': params['hec_token']
        }
        environments_eai_response_payload = self.simple_request_eai(self.get_conf_handler_path_name('environments'),
                                                                    'create', 'POST', post_args)

        # Always populate entry content from request to list handler.
        environments_rest_path = '/servicesNS/%s/%s/environments/%s' % (
            'nobody', self.appName, six.moves.urllib.parse.quote_plus(params['name']))
        environments_eai_response_payload = self.simple_request_eai(environments_rest_path, 'read', 'GET')

        self.set_conf_info_from_eai_payload(confInfo, environments_eai_response_payload)

        # Apply all current app environment searches if requested by params
        if ('search_template_link_alternates' in params and params['search_template_link_alternates'] != ''):
            self.bulk_create_environment_searches_from_template(environments_eai_response_payload['entry'][0]['links']['alternate'], params['search_template_link_alternates'].split(','))

    def handleEdit(self, confInfo):
        """
        Called when user invokes the 'edit' action. Index modification is not supported through this endpoint. Both the
        scripted input and the environments.conf stanza will be overwritten on ANY call to this endpoint.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environment edit requested.')

        name = self.callerArgs.id
        conf_stanza = six.moves.urllib.parse.quote_plus(name)
        params = self.validate_server_schema_params()
        conf_handler_path = '%s/%s' % (self.get_conf_handler_path_name('environments', 'nobody'), conf_stanza)

        environments_eai_response_payload = self.simple_request_eai(conf_handler_path, 'list', 'GET', get_args={'count': -1})
        old_username = environments_eai_response_payload['entry'][0]['content']['username']
        old_password_link_alternate = environments_eai_response_payload['entry'][0]['content']['password_link_alternate']

        # Create post args - remove name to ensure edit instead of create
        environments_conf_postargs = {
            'mgmt_scheme_host_port': params['mgmt_scheme_host_port'],
            'splunk_web_uri': params['splunk_web_uri'],
            'username': params['username'],
            'tags': params['tags'],
            'hec_url': params['hec_url'],
            'hec_token': params['hec_token']
        }

        # Change password if provided in params
        if old_username != params['username']:
            if self.get_param('password'):
                # New username and password provided
                auth_params = self.validate_auth_schema_params()
                params.update(auth_params)
                # Edit passwords.conf stanza
                environments_conf_postargs['password_link_alternate'] = self.password_edit(old_password_link_alternate, params['username'], params['password'])
            else:
                # Can't change username without providing password
                raise admin.InternalException('Password must be provided on username change.')
        if (old_username == params['username'] and self.get_param('password')):
            # Password update to existing username
            auth_params = self.validate_auth_schema_params()
            params.update(auth_params)
            # Edit passwords.conf stanza
            environments_conf_postargs['password_link_alternate'] = self.password_edit(old_password_link_alternate, params['username'], params['password'])

        # Edit environments.conf
        environments_eai_response_payload = self.simple_request_eai(conf_handler_path, 'edit', 'POST',
                                                                    environments_conf_postargs)

        # Always populate entry content from request to list handler.
        environments_rest_path = '/servicesNS/%s/%s/environments/%s' % ('nobody', self.appName, conf_stanza)
        environments_eai_response_payload = self.simple_request_eai(environments_rest_path, 'read', 'GET')
        self.set_conf_info_from_eai_payload(confInfo, environments_eai_response_payload)

    def handleRemove(self, confInfo):
        """
        Called when user invokes the 'remove' action. Removes the requested stanza from inputs.conf (scripted input),
        removes the requested stanza from environments.conf, and removes all associated searches

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environments removal requested.')

        name = self.callerArgs.id
        conf_stanza = six.moves.urllib.parse.quote_plus(name)

        # Grab the link alternate and username from the environments GET response payload before it gets deleted
        environments_rest_path = '/servicesNS/%s/%s/environments/%s' % ('nobody', self.appName, conf_stanza)
        environments_eai_response_payload = self.simple_request_eai(environments_rest_path, 'read', 'GET')
        environments_link_alternate = environments_eai_response_payload['entry'][0]['links']['alternate']
        password_link_alternate = environments_eai_response_payload['entry'][0]['content']['password_link_alternate']

        # Loop through environment searches and delete any search with a matching environment id
        environment_searches_rest_path = '/servicesNS/%s/%s/environment_searches' % ('nobody', self.appName)
        environment_searches_eai_response_payload = self.simple_request_eai(environment_searches_rest_path, 'read', 'GET', get_args={'count': -1})
        environment_searches = environment_searches_eai_response_payload.get('entry', [])

        for environment_search in environment_searches:
            if environments_link_alternate == environment_search['content']['environment_link_alternate']:
                # Delete the any search that is mapped to the environment we are deleting
                environment_searches_delete_path = '%s/%s' % (
                environment_searches_rest_path, six.moves.urllib.parse.quote_plus(environment_search['name']))
                try:
                    environment_searches_eai_response_payload = self.simple_request_eai(
                        environment_searches_delete_path, 'remove', 'DELETE')
                except Exception as e:
                    logger.error('Could not delete environment search %s.' % environment_searches_delete_path)

        # Delete passwords.conf stanza
        try:
            self.password_delete(password_link_alternate)
        except Exception as e:
            logger.error('Could not delete associated credentials storage %s.' % password_link_alternate)

        # Delete environments.conf stanza
        conf_handler_path = '%s/%s' % (self.get_conf_handler_path_name('environments'), conf_stanza)
        environments_eai_response_payload = self.simple_request_eai(conf_handler_path, 'remove', 'DELETE')
        self.set_conf_info_from_eai_payload(confInfo, environments_eai_response_payload)

    def formatted_poller_metrics_earliest_time_fetch(self):
        """
        Returns the lookback metrics search time in -(time)s format. The time is stored in the mothership.conf file
        """
        mothership_conf_handler_path = self.get_conf_handler_path_name('mothership', self.userName, app=self.appName)
        mothership_conf_handler_settings_path = '%s/settings' % mothership_conf_handler_path
        mothership_eai_response_payload = self.simple_request_eai(mothership_conf_handler_settings_path,
                                                                  'list', 'GET')
        poller_metrics_earliest_time = mothership_eai_response_payload['entry'][0]['content'][
            'poller_metrics_earliest_time']
        poller_metrics_formatted_earliest_time = '-%ss' % poller_metrics_earliest_time

        return poller_metrics_formatted_earliest_time

    def password_edit(self, password_link_alternate, new_username, password):
        """
        Edits a password entry using the storage/passwords endpoint. This endpoint will first delete the existing
        entry, then creates a new one.

        Arguments
        password_link_alternate -- The link alternate of the password entry
        password -- The actual password which will be encrypted and stored in passwords.conf
        """
        self.password_delete(password_link_alternate)
        return self.password_create(new_username, password)

    def password_delete(self, password_link_alternate):
        """
        Deletes a password entry using the storage/passwords endpoint.

        Arguments
        password_link_alternate -- The link alternate of the password entry
        """
        passwords_conf_payload = self.simple_request_eai(password_link_alternate, 'remove', 'DELETE')

    def hash_len_confirm(self, password, password_after, password_orig_hash, password_after_hash):
        """
        Confirms length of plaintext password matches retrieved decrypted password. Also compares the hashes of
        the initial and retrieved passwords.

        Arguments
        password -- The actual password which was encrypted and stored in passwords.conf
        password_after -- The decrypted password retrieved from passwords.conf
        password_orig_hash -- The hash of the actual password which was encrypted and stored in passwords.conf
        password_after_hash -- The hash of the decrypted password retrieved from passwords.conf
         """
        assert len(password_after) == len(password)
        assert password_orig_hash == password_after_hash

    def password_create(self, username, password):
        """
        Creates a password entry using the storage/passwords endpoint. This endpoint will validate successful creationof the password by comparing length and hashes of the provided password and the retrieved cleartext password. Password realm will include a unique GUID.

        Arguments
        username -- The username associated with the provided password
        password -- The actual password which will be encrypted and stored in passwords.conf
        """
        m = hashlib.md5()
        m.update(password.encode('utf-8'))
        password_orig_hash = m.hexdigest()

        realm = str(uuid.uuid4().hex)

        passwords_conf_postargs = {
            'realm': realm,
            'name': username,
            'password': password
        }

        passwords_rest_path = '/servicesNS/%s/%s/storage/passwords/' % ('nobody', self.appName)

        # Create password
        passwords_conf_payload = self.simple_request_eai(passwords_rest_path, 'create', 'POST', passwords_conf_postargs)
        password_link_alternate = passwords_conf_payload['entry'][0]['links']['alternate']

        # Load password to check hash and length
        passwords_conf_payload = self.simple_request_eai(password_link_alternate, 'list', 'GET')
        password_after = passwords_conf_payload['entry'][0]['content']['clear_password']

        m = hashlib.md5()
        m.update(password_after.encode('utf-8'))
        password_after_hash = m.hexdigest()

        try:
            self.hash_len_confirm(password, password_after, password_orig_hash, password_after_hash)
        except Exception as e:
            logger.error(e)
            raise admin.InternalException('Password stored incorrectly %s' % e)

        return password_link_alternate

    def validate_server_schema_params(self):
        """
        Validates raw request params against the server schema
        """
        params = self.get_params(schema=environments_schema, filter=environments_schema.SERVER_FIELDS)
        return self.validate_params(environments_schema.server_schema, params)

    def validate_auth_schema_params(self):
        """
        Validates raw request params against the auth schema
        """
        params = self.get_params(schema=environments_schema, filter=environments_schema.AUTH_FIELDS)
        return self.validate_params(environments_schema.auth_schema, params)


    def bulk_create_environment_searches_from_template(self, environment_link_alternate, search_template_link_alternates):

        for search_template in search_template_link_alternates:
            self.create_environment_search_from_template(search_template, environment_link_alternate)

    def create_environment_search_from_template(self, search_template_link_alternate, environment_link_alternate):
        """
        type: template
        search: search template link alternate
        environment_link_alternate:
        """

        post_args = {
            'name': str(uuid.uuid4()),
            'type': 'template',
            'search': search_template_link_alternate,
            'environment_link_alternate': environment_link_alternate
        }

        environment_searches_rest_path = '/servicesNS/%s/%s/environment_searches' % ('nobody', self.appName)

        environment_searches_eai_response_payload = self.simple_request_eai(environment_searches_rest_path,
                                                                    'create', 'POST', post_args)

    def triple_rainbow(self, uri):
        """
        Returns a triple encoded version of the provided uri. Not used but too hard say goodbye.

        Arguments
        uri -- The uri to triple encode
        """
        return six.moves.urllib.parse.quote_plus(
            six.moves.urllib.parse.quote_plus(six.moves.urllib.parse.quote_plus(uri)))

admin.init(EnvironmentsEAIHandler, admin.CONTEXT_NONE)
