import logging
import os
import sys
import uuid
import splunk.admin as admin
import environment_searches_schema
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import re
import errno
import base_eai_handler
import log_helper
import time
from splunk.clilib.bundle_paths import make_splunkhome_path
from io import open
import csv

if sys.platform == 'win32':
    import msvcrt

    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

# Setup the handler
logger = log_helper.setup(logging.INFO, 'EnvironmentSearchesEAIHandler', 'environment_searches_handler.log')

class EnvironmentSearchesEAIHandler(base_eai_handler.BaseEAIHandler):
    def setup(self):
        # Add our supported args
        for arg in environment_searches_schema.ALL_FIELDS:
            self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """
        Called when user invokes the "list" action.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environment search list requested.')

        # Fetch from environment_searches conf handler
        environment_searches_conf_handler_path = self.get_conf_handler_path_name('environment_searches', self.userName)
        environment_searches_eai_response_payload = self.simple_request_eai(environment_searches_conf_handler_path, 'list', 'GET', get_args={'count': -1})

        enable_metrics_search = self.get_param('enable_metrics_search', default='0')
        if enable_metrics_search == '0':
            link_alternate_metrics_map = {}
        else:
            poller_metrics_earliest_time = self.get_param('poller_metrics_earliest_time', default='-1')
            if poller_metrics_earliest_time == '-1':
                # Fetch the formatted poller metrics lookback time
                poller_metrics_formatted_earliest_time = self.formatted_poller_metrics_earliest_time_fetch()
            else:
                # Format the poller_metrics_earliest_time override provided in the GET param
                poller_metrics_formatted_earliest_time = '-%ss' % poller_metrics_earliest_time

            # Fetch poller metrics
            link_alternate_metrics_map = self.oneshot_metrics_search(poller_metrics_formatted_earliest_time, self.appName)

        # Fetch all HEC tokens and token metadata
        # Make a map of link alternate to token metadata
        hec_token_path = '/servicesNS/nobody/%s/data/inputs/http' % self.appName
        hec_tokens_eai_response_payload = self.simple_request_eai(
            hec_token_path, 'read', 'GET', get_args={'count': -1})

        hec_token_entries = hec_tokens_eai_response_payload.get('entry', [])

        hec_token_entry_map = {}

        for hec_token_entry in hec_token_entries:
            hec_token_entry_map[hec_token_entry['links'].get('alternate')] = hec_token_entry

        hec_global_enabled_path = '/servicesNS/nobody/%s/data/inputs/http/http' % self.appName

        hec_global_enabled_eai_response_payload = self.simple_request_eai(
            hec_global_enabled_path, 'read', 'GET')

        hec_global_disabled = hec_global_enabled_eai_response_payload['entry'][0]['content'].get('disabled', '')

        # Fetch all search templates and create a map of template name to actual entry
        # This is to avoid making an http round trip for every template
        search_templates_eai_response_payload = self.simple_request_eai(self.get_conf_handler_path_name('environment_search_templates', app='-'), 'read', 'GET', get_args={'count': -1})

        search_templates_entries = search_templates_eai_response_payload.get('entry', [])

        search_template_entry_map = {}

        for search_template_entry in search_templates_entries:
            search_template_entry_map[search_template_entry['links'].get('alternate')] = search_template_entry

        for environment_search in environment_searches_eai_response_payload['entry']:
            environment_search_type = environment_search['content'].get('type')
            environment_search_string = environment_search['content'].get('search', '')
            if environment_search_type == 'inline':
                environment_search['content']['search_string'] = environment_search_string
            elif environment_search_type == 'template':
                search_template = search_template_entry_map.get(environment_search_string)
                if search_template:
                    environment_search['content']['search_string'] = search_template['content'].get('search_string', '')
                    if 'label' not in environment_search['content'] or environment_search['content']['label'] == '':
                        environment_search['content']['label'] = search_template.get('name', '')

            # Get metadata for HEC token
            hec_token_link_alternate = environment_search['content'].get('hec_token_link_alternate', '')
            environment_search['content']['hec_token_value'] = ''
            environment_search['content']['hec_token_enabled'] = 0
            hec_token_entry = hec_token_entry_map.get(hec_token_link_alternate)
            if hec_token_entry:
                environment_search['content']['hec_token_value'] = hec_token_entry['content'].get('token', '')
                environment_search['content']['hec_token_enabled'] = hec_token_entry['content'].get('disabled', '')
                environment_search['content']['hec_token_name'] = hec_token_entry.get('name', '')

            # Parse lookup name from link alternate
            lookup_link_alternate = environment_search['content'].get('lookup_link_alternate', '')
            if lookup_link_alternate:
                environment_search['content']['lookup_name'] = lookup_link_alternate.split('/data/lookup-table-files/')[1]

            # Add poller logging metrics
            environment_search_link_alternate = (environment_search['links']['alternate']).replace('/configs/conf-environment_searches/', '/environment_searches/')
            environment_search_entry = link_alternate_metrics_map.get(environment_search_link_alternate)

            if environment_search_entry:
                environment_search['content']['job_run_duration'] = link_alternate_metrics_map[environment_search_link_alternate].get('job_run_duration', '')
                environment_search['content']['script_run_duration'] = link_alternate_metrics_map[environment_search_link_alternate].get('script_run_duration', '')
                environment_search['content']['script_run_time'] = link_alternate_metrics_map[environment_search_link_alternate].get('_time', '')
                environment_search['content']['results_count'] = link_alternate_metrics_map[environment_search_link_alternate].get('results_count', '')
                environment_search['content']['results_count_sparkline'] = link_alternate_metrics_map[
                    environment_search_link_alternate].get('sparkline', '')
                environment_search['content']['report_search'] = link_alternate_metrics_map[
                    environment_search_link_alternate].get('report_search', '')
                environment_search['content']['script_status_code'] = link_alternate_metrics_map[
                    environment_search_link_alternate].get('status_code', '')
                environment_search['content']['script_message'] = link_alternate_metrics_map[
                    environment_search_link_alternate].get('message', '')
                environment_search['content']['script_timestamp'] = link_alternate_metrics_map[
                        environment_search_link_alternate].get('_time', '')
            else:
                environment_search['content']['job_run_duration'] = ''
                environment_search['content']['script_run_duration'] = ''
                environment_search['content']['script_run_time'] = ''
                environment_search['content']['results_count'] = ''
                environment_search['content']['results_count_sparkline'] = ''
                environment_search['content']['report_search'] = ''
                environment_search['content']['script_status_code'] = ''
                environment_search['content']['script_message'] = ''
                environment_search['content']['script_timestamp'] = ''

            environment_search['content']['hec_global_disabled'] = hec_global_disabled

        self.set_conf_info_from_eai_payload(confInfo, environment_searches_eai_response_payload)

        # Fetch from savedsearches handler and set specified keys
        savedsearches_handler_path = '/servicesNS/nobody/%s/saved/searches' % self.appName
        savedsearches_eai_response_payload = self.simple_request_eai(savedsearches_handler_path, 'list', 'GET',
                                                              get_args={'count': -1})

        self.set_conf_info_from_savedsearches_eai_payload_filtered(confInfo, savedsearches_eai_response_payload)

        # Fetch indices
        index_handler_path = '/servicesNS/-/%s/data/indexes' % self.appName
        indexes_eai_response_payload = self.simple_request_eai(index_handler_path, 'list', 'GET',
                                                               get_args={'count': -1})

        # For every index find a matching input that is an environment_search poller
        # This is to avoid making an http round trip for every entry
        index_entries = indexes_eai_response_payload.get('entry', [])
        index_link_alternate_entry_map = {}

        # Create mapping of index names to their content
        for index_entry in index_entries:
            index_link_alternate_entry_map[index_entry['links']['alternate']] = index_entry

        for environment_search in environment_searches_eai_response_payload['entry']:
            environment_search_index_link_alternate = environment_search['content']['index_link_alternate']
            environment_search_name = environment_search['name']

            if (environment_search_index_link_alternate in index_link_alternate_entry_map):
                index_entry_content = index_link_alternate_entry_map[environment_search_index_link_alternate].get('content', {})
                index_entry_name = index_link_alternate_entry_map[environment_search_index_link_alternate].get('name')
                if environment_search_name in confInfo:
                    confInfo[environment_search_name]['index'] = index_entry_name
                    confInfo[environment_search_name]['index_total_event_count'] = index_entry_content.get('totalEventCount')
                    confInfo[environment_search_name]['index_event_min_time'] = index_entry_content.get('minTime')
                    confInfo[environment_search_name]['index_event_max_time'] = index_entry_content.get('maxTime')
                    confInfo[environment_search_name]['index_current_db_size_mb'] = index_entry_content.get('currentDBSizeMB')

        # Fetch environments
        environment_handler_path = '/servicesNS/%s/%s/environments' % ('nobody', self.appName)
        environment_eai_response_payload = self.simple_request_eai(environment_handler_path, 'list', 'GET',  get_args={'count': -1})
        link_alternate_content_map = {}

        # Build map of link alternates to actual environment content
        for environment in environment_eai_response_payload['entry']:
            link_alternate = environment['links']['alternate']
            environment['content'].update({'environment_name': environment['name']})
            link_alternate_content_map[link_alternate] = environment['content']

        for environment_search in confInfo:
            # Grab the environment content associated with a particular link alternate
            if (confInfo[environment_search].get('environment_link_alternate') in link_alternate_content_map):
                environment_content = link_alternate_content_map[confInfo[environment_search]['environment_link_alternate']]
            else:
                continue

            confInfo[environment_search]['mgmt_scheme_host_port'] = environment_content.get('mgmt_scheme_host_port', '')
            confInfo[environment_search]['username'] = environment_content.get('username', '')
            confInfo[environment_search]['environment_name'] = environment_content.get('environment_name', '')
            confInfo[environment_search]['splunk_web_uri'] = environment_content.get('splunk_web_uri', '')
            confInfo[environment_search]['hec_url'] = environment_content.get('hec_url', '')
            confInfo[environment_search]['hec_token'] = environment_content.get('hec_token', '')

            # Check for label
            confInfo[environment_search]['label'] = confInfo[environment_search].get('label', '')

    def handleCreate(self, confInfo):
        """
        Called when user invokes the 'create' action.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environment search creation requested.')

        # Validate and extract correct POST params
        params = self.validate_search_schema_params()

        # Generate a reusable name for objects created by the handler (index, HEC token, lookup, etc.)
        environments_eai_response_payload = self.simple_request_eai(params['environment_link_alternate'], 'read', 'GET')
        mgmt_scheme_host_port = environments_eai_response_payload['entry'][0]['content']['mgmt_scheme_host_port']

        # Build a standardized name for an environment search associated objects (facilitates debugging)
        mothership_object_name = 'mothership_%s_%s' % ( self.uri_to_fs_safe(mgmt_scheme_host_port), self.index_name_formatter(params.get('name')))
        # Ensure the name is no longer than 100 characters (saved search name length constraint)
        mothership_object_name = mothership_object_name.lower()[-100:]

        # Index creation
        if params.get('index_link_alternate') is None:
            logger.info('No index provided, creating and assigning one.')

            index_link_alternate = self.existing_index_link_alternate(self.appName, 'nobody', mothership_object_name)

            if not index_link_alternate:
                # create_index will set params['index_link_alternate'] to the created index's link alternate
                self.create_index(mothership_object_name, params)
            else:
                params['index_link_alternate'] = index_link_alternate

        if (params['type'] == 'template'):
            # Confirm that selected the template exists
            self.confirm_template(params)

        # HEC token creation
        self.create_hec_token(mothership_object_name, params)

        # Savedsearch creation
        """
        There is a circular dependency between the savedsearch creation (needs the environment search link alternate) and
        the environment search conf entry (needs the savedsearch link alternate)

        Create most of the saved search now (disabled). Edit and enable the search after creating the
        conf entry.
        """

        self.create_savedsearch(mothership_object_name, params)

        # Lookup creation
        if params.get('lookup_link_alternate') is None:
            logger.info('No lookup provided, creating and assigning one.')

            self.create_lookup(mothership_object_name, params)

        # environment_search.conf creation and response
        self.create_environment_searches_conf(params)

        # Grab response from list handler for accurate link_alternate.
        environment_search_rest_path = '/servicesNS/%s/%s/environment_searches/%s' % (
        'nobody', self.appName, six.moves.urllib.parse.quote_plus(params['name']))
        environment_search_eai_response_payload = self.simple_request_eai(environment_search_rest_path, 'read', 'GET')
        environment_search_link_alternate = environment_search_eai_response_payload['entry'][0]['links'][
                'alternate']

        # Savedsearch fix (set provided disabled status and update search string with valid environment_search_link_alternate)
        saved_search_eai_response_payload = self.fix_savedsearch(params.get('savedsearch_link_alternate'), environment_search_link_alternate, params.get('disabled'))

        # Savedsearch dispatch; create a search job and archive results
        if saved_search_eai_response_payload['entry'][0]['content']['disabled'] == 0:
            self.dispatch_savedsearch(params.get('savedsearch_link_alternate'))

        # Always populate entry content from request to list handler.
        environment_searches_rest_path = '/servicesNS/%s/%s/environment_searches/%s' % (
            'nobody', self.appName, six.moves.urllib.parse.quote_plus(params['name']))
        environment_searches_eai_response_payload = self.simple_request_eai(environment_searches_rest_path, 'read', 'GET')
        self.set_conf_info_from_eai_payload(confInfo, environment_searches_eai_response_payload)

    def handleEdit(self, confInfo):
        """
        Called when user invokes the 'edit' action. Index modification is not supported through this endpoint. Both the
        scripted input and the environment_searches.conf stanza will be overwritten on ANY call to this endpoint.

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environment search edit requested.')

        params = self.validate_search_schema_params()
        conf_stanza = six.moves.urllib.parse.quote_plus(params.get('name'))
        conf_handler_path = '%s/%s' % (self.get_conf_handler_path_name('environment_searches', 'nobody'), conf_stanza)

        # Create post args - remove name to ensure edit instead of create
        environment_searches_conf_postargs = {
            'environment_link_alternate': params['environment_link_alternate'],
            'search': params['search'],
        }

        if 'label' in params and params['type'] == 'inline':
            environment_searches_conf_postargs['label'] = params['label']
        if 'type' in params:
            if params['type'] == 'template':
                environment_searches_conf_postargs['label'] = ''
            environment_searches_conf_postargs['type'] = params['type']

        # Edit environment_search.conf
        environment_searches_eai_response_payload = self.simple_request_eai(conf_handler_path, 'edit', 'POST',
                                                                    environment_searches_conf_postargs)

        # Always populate entry content from request to list handler.
        environment_searches_rest_path = '/servicesNS/%s/%s/environment_searches/%s' % (
        'nobody', self.appName, six.moves.urllib.parse.quote_plus(params['name']))
        environment_searches_eai_response_payload = self.simple_request_eai(environment_searches_rest_path, 'read', 'GET')
        self.set_conf_info_from_eai_payload(confInfo, environment_searches_eai_response_payload)
        environment_searches_link_alternate = environment_searches_eai_response_payload['entry'][0]['links'][
            'alternate']

        # Savedsearch edit - after environment_search.conf update because script may have a dependency
        savedsearch_postargs = {}

        savedsearch_handler_path = environment_searches_eai_response_payload['entry'][0]['content']['savedsearch_link_alternate']

        if 'disabled' in params:
            savedsearch_postargs['disabled'] = 1 if params['disabled']=='True' else 0

        if 'interval' in params:
            minutes = int(int(params.get('interval')) / 60)
            cron_schedule = '*/%s * * * *' % str(minutes)

            savedsearch_postargs['args.interval'] = params.get('interval')
            savedsearch_postargs['cron_schedule'] = cron_schedule

        if 'cron_schedule' in params:
            cron_schedule = params["cron_schedule"]
            savedsearch_postargs['cron_schedule'] = cron_schedule
            savedsearch_postargs['args.interval'] = ''


        savedsearch_eai_response_payload = self.simple_request_eai(savedsearch_handler_path, 'edit', 'POST', savedsearch_postargs)

        if savedsearch_eai_response_payload['entry'][0]['content']['disabled'] is False:
            # Savedsearch dispatch; create a search job and archive results
            self.dispatch_savedsearch(savedsearch_handler_path)

    def handleRemove(self, confInfo):
        """
        Called when user invokes the 'remove' action. Removes the requested stanza from inputs.conf (scripted input) and
        removes the requested stanza from environment_searches.conf

        Arguments
        confInfo -- The object containing the information about what is being requested.
        """
        logger.info('Environment search removal requested.')

        name = self.callerArgs.id
        conf_stanza = six.moves.urllib.parse.quote_plus(name)
        environment_search_rest_path = '/servicesNS/%s/%s/environment_searches/%s' % ('nobody', self.appName, conf_stanza)

        # Grab the link alternate from the environment_searches GET response payload before it gets deleted
        environment_search_eai_response_payload = self.simple_request_eai(environment_search_rest_path, 'read', 'GET')
        environment_search_hec_token_link_alternate = environment_search_eai_response_payload['entry'][0]['content']['hec_token_link_alternate']
        environment_search_savedsearch_link_alternate = environment_search_eai_response_payload['entry'][0]['content']['savedsearch_link_alternate']

        # Delete HEC token
        try:
            hec_token_eai_response_payload = self.simple_request_eai(environment_search_hec_token_link_alternate, 'remove', 'DELETE')
        except Exception as e:
            logger.error('Could not delete associated HEC token %s.' % environment_search_hec_token_link_alternate)

        # Delete savedsearches.conf stanza
        try:
            savedsearch_eai_response_payload = self.simple_request_eai(environment_search_savedsearch_link_alternate, 'remove', 'DELETE')
        except Exception as e:
            logger.error('Could not delete associated saved search %s.' % environment_search_savedsearch_link_alternate)

        # Delete environment_searches.conf stanza
        conf_handler_path = '%s/%s' % (self.get_conf_handler_path_name('environment_searches'),  conf_stanza)
        try:
            environment_searches_eai_response_payload = self.simple_request_eai(conf_handler_path, 'remove', 'DELETE')
        except Exception as e:
            logger.error('Could not delete associated environment search %s.' % environment_search_rest_path)

        self.set_conf_info_from_eai_payload(confInfo, environment_searches_eai_response_payload)

    def confirm_template(self, params):
        """
        Confirm that the template provided in the request is valid

        Arguments
        params -- The list of parameters in the environment_searches.conf entry
        """
        try:
            template_endpoint = params['search']
            environment_search_templates_eai_response_payload = self.simple_request_eai(
                template_endpoint,
                'read', 'GET')
        except Exception as e:
            logger.error(e)
            raise admin.ServiceUnavailableException('Provided template does not exist. %s' % e)

    def create_savedsearch(self, mothership_object_name, params):
        """
        Creates a savedsearch using the provided parameters

        Arguments
        mothership_object_name -- The standard mothership knowledge object name for objects created by the create handler
        environment_searches_link_alternate -- The link alternate of the environment_searches.conf entry
        params -- The list of parameters in the environment_searches.conf entry
        """

        # Convert interval to a cron schedule
        # If there is not interval and corn schedule found, give it a default value

        interval = params.get('interval')
        if interval:
            minutes = int(int(interval)/60)
            cron_schedule = '*/%s * * * *' % str(minutes)
        elif params.get('cron_schedule'):
            cron_schedule = params.get('cron_schedule')
        else:
            cron_schedule = '*/5 * * * *'

        savedsearch_postargs = {
            'name': mothership_object_name,
            'search': '| environmentpoller environment_search_link_alternate=placeholder',
            'cron_schedule': cron_schedule,
            'disabled': 1,
            'is_scheduled': 1,
            'args.interval': interval,
        }
        savedsearch_rest_path = '/servicesNS/nobody/%s/saved/searches' % self.appName
        savedsearch_eai_response_payload = self.simple_request_eai(savedsearch_rest_path, 'create', 'POST', savedsearch_postargs)

        savedsearch_link_alternate = savedsearch_eai_response_payload['entry'][0]['links']['alternate']

        params['savedsearch_link_alternate'] = savedsearch_link_alternate

    def fix_savedsearch(self, savedsearch_link_alternate, environment_search_link_alternate, disabled):
        """
        Creates a savedsearch using the provided parameters

        Arguments
        savedsearch_link_alternate -- The link alternate of the savedsearches.conf entry
        params -- The list of parameters in the environment_searches.conf entry
        """

        savedsearch_postargs = {
            'search': '| environmentpoller environment_search_link_alternate=%s' % environment_search_link_alternate,
            'disabled': 1 if disabled=='True' else 0,
        }

        return self.simple_request_eai(savedsearch_link_alternate, 'update', 'POST', savedsearch_postargs)


    def dispatch_savedsearch(self, savedsearch_link_alternate):
        """
        Dispatches the associated saved search retrieving results from remote machine and storing locally.

        Arguments
        savedsearch_link_alternate -- The link alternate of the savedsearches.conf entry
        """
        self.simple_request_eai('%s/dispatch' % savedsearch_link_alternate, 'update', 'POST')

    def create_lookup(self, mothership_object_name, params):
        """
        Creates a lookup using the provided parameters. Also updates the permissions on the lookup to admin read only
        and splunk-system-user (the scripted input) read and write.

        Arguments
        mothership_object_name -- The standard mothership knowledge object name for objects created by the create handler
        params -- The list of parameters in the environment_searches.conf entry
        """
        lookup_path = '/servicesNS/nobody/%s/data/lookup-table-files' % self.appName
        file_placeholder_value = 'filename,status\n%s,PLACEHOLDER LOOKUP NOT YET OVERWRITTEN\n' % mothership_object_name
        placeholder = [['filename', 'status'], [mothership_object_name, 'PLACEHOLDER LOOKUP NOT YET OVERWRITTEN']]

        hex_uuid = str(uuid.uuid4().hex)
        lookup_tmp_file = '%s.csv' % hex_uuid
        lookup_tmp = make_splunkhome_path(['var', 'run', 'splunk', 'lookup_tmp'])

        try:
            os.makedirs(lookup_tmp)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(lookup_tmp):
                pass
            else:
                raise

        lookup_tmp_path = os.path.join(lookup_tmp, lookup_tmp_file)

        with open(lookup_tmp_path, 'wb') as csvfile:
            # writer = csv.writer(csvfile)
            # writer.writerows(placeholder)
            csvfile.write(file_placeholder_value.encode('utf-8'))

        lookup_postargs = {
            'eai:data': lookup_tmp_path,
            'name': '%s.csv' % mothership_object_name
        }

        lookup_eai_response_payload = self.simple_request_eai(lookup_path, 'create', 'POST',
                                                              lookup_postargs)

        lookup_link_alternate = lookup_eai_response_payload['entry'][0]['links']['alternate']

        params['lookup_link_alternate'] = lookup_link_alternate

        # Lookup permission update
        lookup_permissions_path = '%s/%s' % (lookup_link_alternate, 'acl')
        lookup_permissions_postargs = {
            'sharing': 'app',
            'owner': 'nobody',
            'perms.read': 'admin,splunk-system-role',
            'perms.write': 'splunk-system-role'
        }

        lookup_permissions_eai_response_payload = self.simple_request_eai(lookup_permissions_path, 'create', 'POST',
                                                                          lookup_permissions_postargs)

    def create_environment_searches_conf(self, params):
        """
        Creates an environment_searches.conf entry using the provided parameters.

        Arguments
        params -- The list of parameters in the environment_searches.conf entry
        """
        environment_searches_conf_postargs = {
            'name': params['name'],
            'search': params['search'],
            'environment_link_alternate': params['environment_link_alternate'],
            'type': params['type'],
            'hec_token_link_alternate': params['hec_token_link_alternate'],
            'lookup_link_alternate': params['lookup_link_alternate'],
            'index_link_alternate': params['index_link_alternate'],
            'savedsearch_link_alternate': params['savedsearch_link_alternate']
        }

        if (params['type'] == 'template'):
            if ('label' in params):
                environment_searches_conf_postargs['label'] = params['label']
        elif (params['type'] == 'inline'):
            if ('label' not in params):
                # Set label to GUID
                environment_searches_conf_postargs['label'] = params['name']
            else:
                environment_searches_conf_postargs['label'] = params['label']
        else:
            raise admin.ServiceUnavailableException('Search type is unsupported.')

        if 'hec_endpoint' in params and 'hec_token' in params:
            environment_searches_conf_postargs['hec_endpoint'] = params['hec_endpoint']
            environment_searches_conf_postargs['hec_token'] = params['hec_token']

        if 'sourcetype' in params:
            environment_searches_conf_postargs['sourcetype'] = params['sourcetype']

        environment_searches_eai_response_payload = self.simple_request_eai(
            self.get_conf_handler_path_name('environment_searches'),
            'create', 'POST', environment_searches_conf_postargs)

    def create_hec_token(self, mothership_object_name, params):
        """
        Creates a HTTP Event collector token using the provided parameters.

        Arguments
        mothership_object_name -- The standard mothership knowledge object name for objects created by the create handler
        params -- The list of parameters in the environment_searches.conf entry
        """
        hec_token_path = '/servicesNS/nobody/%s/data/inputs/http' % self.appName
        index_name = self.index_name_from_link_alternate(params.get('index_link_alternate'))

        hec_token_postargs = {
            'name': mothership_object_name,
            'disabled': '0',
            'index': index_name,
            'indexes': [index_name]
        }

        hec_eai_response_payload = self.simple_request_eai(hec_token_path, 'create', 'POST',
                                                           hec_token_postargs)
        params['hec_token_link_alternate'] = hec_eai_response_payload['entry'][0]['links']['alternate']

    def create_index(self, mothership_object_name, params):
        """
        Creates an index using the provided parameters.

        Arguments
        mothership_object_name -- The standard mothership knowledge object name for objects created by the create handler
        params -- The list of parameters in the environment_searches.conf entry
        """
        # Takes name and mgmt_scheme_host_port and adds to a leading mothership namespace
        logger.info('No index provided, creating and assigning one.')

        index_rest_path = '/servicesNS/-/%s/data/indexes' % self.appName
        index_postargs = {
            'name': mothership_object_name,
            'enableDataIntegrityControl': '0',
            'enableTsidxReduction': '0'
        }
        try:
            indexes_eai_response_payload = self.simple_request_eai(index_rest_path, 'create', 'POST',
                                                                   index_postargs)
        except admin.AlreadyExistsException as e:
            raise admin.ServiceUnavailableException('Index already exists. %s' % e)

        params['index_link_alternate'] = indexes_eai_response_payload['entry'][0]['links']['alternate']

    def existing_index_link_alternate(self, app, owner, name):

        index_rest_path = '/servicesNS/%s/%s/data/indexes' % (owner, app)

        try:
            indexes_eai_response_payload = self.simple_request_eai(index_rest_path + '/' + name, 'read', 'GET')
        except Exception as e:
            return None

        return indexes_eai_response_payload['entry'][0]['links']['alternate']


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

    def validate_search_schema_params(self):
        """
        Validates raw request params against the search schema
        """
        schema = environment_searches_schema.search_schema
        params = self.get_params(schema=environment_searches_schema, filter=environment_searches_schema.SEARCH_FIELDS)
        return self.validate_params(schema, params)

    def index_name_formatter(self, name):
        """
        Returns a index safe name string by replacing non supported characters

        Arguments:
        name -- The name to format into an index safe string
        """
        return re.sub('[^0-9a-zA-Z_\-]', '_', name)

    def index_name_from_link_alternate(self, index_link_alternate):
        """
        Returns the index name by parsing the index link alternate

        Arguments
        index_link_alternate -- The link alternate of the index to parse name from
        """
        return six.moves.urllib.parse.unquote(index_link_alternate.split('/')[-1])

    def uri_to_fs_safe(self, uri):
        """
        Returns a unique, readable index name based on the mgmt_scheme_host_port input parameter

        Arguments
        uri -- The mgmt_scheme_host_port value that will be reformatted as an index name
        """
        return uri.replace('://', '_').replace('/', '_').replace(':', '_').replace('.', '_').lower()

    def set_conf_info_from_savedsearches_eai_payload_filtered(self, confInfo, payload):
        """
        Takes the mutable confInfo object and sets the content to that found from
        the list of inputs list response entry content children, using the provided filters

        Arguments
        confInfo -- The object containing the information about what is being requested.
        payload -- Parsed EAI response from an EAI output_mode=json response.
        filters -- a list of strings representing entryContentKeys that will updated in confInfo
        """

        # Create list of all link alternates in confInfo
        savedsearch_link_alternates_map = {}

        for conf_entry_name in confInfo:
            savedsearch_link_alternate = confInfo[conf_entry_name].get('savedsearch_link_alternate')
            if savedsearch_link_alternate:
                savedsearch_link_alternates_map[savedsearch_link_alternate] = conf_entry_name

        # Loop through existing inputs
        entries = payload.get('entry', [])
        for entry in entries:
            entry_content = entry.get('content')
            entry_links = entry.get('links')

            savedsearch_link_alternate = entry_links['alternate']

            if not savedsearch_link_alternate:
                continue

            # if this scripted input was created by Mothership/or is associated with an environment_searches.conf stanza
            if savedsearch_link_alternate in savedsearch_link_alternates_map:
                conf_entry_name = savedsearch_link_alternates_map[savedsearch_link_alternate]

                confInfo[conf_entry_name]['interval'] = str(entry_content.get('args.interval', ''))
                confInfo[conf_entry_name]['disabled'] = str(entry_content.get('disabled', ''))
                confInfo[conf_entry_name]['cron_schedule'] = str(entry_content.get('cron_schedule', ''))

                next_scheduled_time = str(entry_content.get('next_scheduled_time', ''))

                if next_scheduled_time != '':
                    try:
                        date_format = '%Y-%m-%d %H:%M:%S %Z'
                        confInfo[conf_entry_name]['next_scheduled_time'] = str(int(time.mktime(time.strptime(next_scheduled_time, date_format)))) + '000'
                    except Exception as e:
                        confInfo[conf_entry_name]['next_scheduled_time'] = ''

        return confInfo

    def is_environment_searches_input(self, name):
        """
        Returns if an input entry is environment_search supported or not.

        Arguments
        name -- The entry stanza name for the input.
        """
        return name.startswith(environment_searches_schema.INPUT_ROOT_NAME) and len(name.split(' ')) == 2

    def is_mothership_savedsearch(self, name):
        """
        Returns if an input entry is environment_search supported or not.

        Arguments
        name -- The entry stanza name for the input.
        """
        return name.startswith('mothership')

    def parse_input_name(self, name):
        """
        Returns the matching environment_search stanza name and link alternate.

        Arguments
        name -- The entry stanza name for the input.
        """
        parsed = {}
        if self.is_environment_searches_input(name):
            parts = name.split(' ')
            parsed['environment_search_name'] = parts[1].split('/')[-1]
            parsed['environment_searches_link_alternate'] = parts[1]
        return parsed

    def parse_raw_name_from_input_name(self, full_name):
        """
        Returns the raw (decoded) name used as the environment_searches.conf stanza from the provided
        link alternate.

        Arguments
        full_name -- The full input stanza name to parse out a raw (decoded) name from
        """
        encoded_name = self.parse_input_name(full_name)

        if encoded_name:
            return six.moves.urllib.parse.unquote_plus(encoded_name['environment_search_name'])
        return None

    def parse_savedsearch_name(self, name):
        """
        Returns the matching environment_search stanza name and link alternate.

        Arguments
        name -- The entry stanza name for the input.
        """
        parsed = {}
        if self.is_mothership_savedsearch(name):
            parts = name.split('_')
            parsed['environment_search_name'] = parts[len(parts)-1]

        return parsed

    def parse_raw_name_from_savedsearch_name(self, full_name):
        """
        Returns the raw (decoded) name used as the environment_searches.conf stanza from the provided
        link alternate.

        Arguments
        full_name -- The full input stanza name to parse out a raw (decoded) name from
        """

        encoded_name = self.parse_savedsearch_name(full_name)

        if encoded_name:
            return six.moves.urllib.parse.unquote_plus(encoded_name['environment_search_name'])
        return None

admin.init(EnvironmentSearchesEAIHandler, admin.CONTEXT_NONE)
