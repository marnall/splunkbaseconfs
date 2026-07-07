# -*- coding: utf-8 -*-
"""Provide a set REST endpoints for the app."""
import os
import sys
import traceback
import json
import csv
import random
import logging
import logging.handlers
from io import StringIO
# Because python...
sys.path.insert(0, os.path.dirname(__file__))
import rfe_rest  # noqa pylint:disable=wrong-import-position
import rfe_enrich  # noqa pylint:disable=wrong-import-position
import rfe_validate  # noqa pylint:disable=wrong-import-position
import rfe_risklists  # noqa pylint:disable=wrong-import-position
from rfe_app_env import RfeAppEnv  # noqa pylint:disable=wrong-import-position
from rfe_samples import SAMPLE_DATA  # noqa pylint:disable=wrong-import-position
import splunk  # nopep8 pylint:disable=import-error,wrong-import-position
if sys.platform == "win32":
    import msvcrt  # pylint:disable=import-error
    # Binary mode is required for persistent mode on Windows.
    # Looked what os.O_BINARY actually was and found on Windows 10,
    # Server 2016 and Server 2019 that the value is 32768.
    # noqa pylint:disable=no-member
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    # noqa pylint:disable=no-member
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    # noqa pylint:disable=no-member
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
#  pylint: disable=import-error, wrong-import-position
# noinspection PyUnresolvedReferences
from splunk.persistconn.application \
    import PersistentServerConnectionApplication  # nopep8
# noinspection PyUnresolvedReferences


class lazy_property(object):
    """Meant to be used for lazy evaluation of an object attribute.

    Property should represent non-mutable data, as it replaces itself.
    """

    def __init__(self, fget):
        """Initialize."""
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        """Return the property."""
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        return value


class RfeError(Exception):
    """Base class for exceptions in this module.

    Attributes:
        message -- the error message
        status -- suggested HTTP return status
    """

    def __init__(self, message, orig_message, code):
        """Initialize."""
        super(RfeError, self).__init__(message)
        self.orig_message = orig_message
        self.code = code


class AuthenticationRfeError(RfeError):
    """Authentication failed."""

    pass


class AuthorizationRfeError(RfeError):
    """Authorization failed."""

    pass


class NoCleartextRfeError(RfeError):
    """The password entry does not contain the clear text password."""

    pass


class StoragePasswordRfeError(RfeError):
    """The password entry does not contain the clear text password."""

    pass


class RestRfeError(RfeError):
    """Unspecific REST error."""

    pass


class RfeHandler(PersistentServerConnectionApplication):
    """A set of REST endpoints for the app."""

    # pylint: disable=unused-argument
    def __init__(self, command_line, command_arg):
        """Initialize."""
        self.logger = self.setup_logging()
        PersistentServerConnectionApplication.__init__(self)

    def handle_alerts_metadata(self, in_dict, app_env):
        """Fetch info about alerts."""
        self.logger.info('handle_alerts_metadata entered.')
        return rfe_rest.alerts_metadata(app_env, app_env.api_key,
                                        self.logger, app_env.verify)

    def handle_validate(self, in_dict, app_env):
        """Handle validate REST calls."""
        self.logger.info('handle_validate entered.')
        validation = rfe_validate.validate(app_env.api_key,
                                           app_env,
                                           self.logger)

        reslist = [{'name': ent['step'],
                    'content': ent}
                   for ent in validation]
        return {
            'entry': reslist
        }

    def handle_lookup(self, in_dict, app_env):
        """Handle lookup calls."""
        self.logger.info('handle_lookup entered.')
        try:
            category, ent = in_dict['path_info'][7:].split('/', 1)
            self.logger.debug('category=%s entity=%s', category, ent)
            query = dict(in_dict['query'])
            # Workaround for URL lookups which can contain an = in the
            # path-info section. This confuses Splunk. Solution is to set
            # path-info to PARAM and supply the URL as a param argument.
            if ent == 'PARAM':
                ent = query['param']
            self.logger.debug('query=%s', query)
            # pylint: disable=no-member
            return rfe_enrich.lookup(category, ent, app_env.api_key, app_env,
                                     self.logger, app_env.verify, **query)
        except ValueError as err:
            self.logger.error('Invalid lookup request: %s',
                              in_dict['path_info'], exc_info=True)
            raise err
        except Exception as err:
            self.logger.error(err, exc_info=True)
            raise err

    def handle_search(self, in_dict, app_env):
        """Handle search calls."""
        self.logger.info('handle_search entered.')
        try:
            if in_dict['path_info'].startswith('search_vulnerabilities'):
                category = 'vulnerability'
            else:
                category = in_dict['path_info'][7:-1]
            self.logger.debug('category=%s', category)
            query = dict(in_dict['query'])
            self.logger.debug('query=%s', query)
            # pylint: disable=no-member
            return rfe_enrich.search(category, app_env.api_key, app_env,
                                     self.logger, app_env.verify, **query)
        except ValueError as err:
            self.logger.error('Invalid lookup request: %s',
                              in_dict['path_info'], exc_info=True)
            raise err
        except Exception as err:
            self.logger.error(err, exc_info=True)
            raise err

    def handle_download_risklist(self, in_dict, app_env):
        """Download a named risk list/fusion.

        Data will be returned as a big blob of data.
        """
        self.logger.info('handle_download_risklist entered.')
        try:
            stanza = in_dict['path_info'].split('/')[1].replace('%20', ' ')
            payload = rfe_risklists.download_risklist(app_env, stanza,
                                                      self.logger)
        except IndexError as err:
            self.logger.info('No stanza attached to the REST API call: %s',
                             err)
            raise
        except Exception as err:
            self.logger.error('failed call to download_risklist: %s', err)
            raise
        if payload:
            return (200, {'links': {},
                          'entry': payload})
        else:
            return 500, {}

    def handle_download_alerts(self, in_dict, app_env):
        """Download alerts.

        Data will be returned as a big blob of data.
        """
        self.logger.info('handle_download_alerts entered.')
        try:
            stanza = in_dict['path_info'].split('/')[1].replace('%20', ' ')
            payload = rfe_rest.fetch_alerts(app_env,
                                            stanza,
                                            self.logger)
        except IndexError as err:
            self.logger.info('No stanza attached to the REST API call: %s',
                             err)
            raise
        except Exception as err:
            self.logger.error('Problem downloading alerts: %s', err)
            raise

        self.logger.info('Alerts with stanza: %s downloaded successfully',
                         stanza)

        return {'links': {},
                'entry': payload}

    def handle_sample_data(self, in_dict, app_env):
        """Return sample data from specified data group.

        A random number between 75 and 125 samples will be returned unless
        the total size of the sample set is smaller in which case the total
        set will be returned.
        """
        self.logger.info('handle_sample_data entered.')
        datatype = None
        for i in in_dict['query']:
            if 'type' in i[0]:
                datatype = i[1]
        self.logger.debug('Type of sampledata: %s', datatype)
        if datatype not in ['ip', 'vuln', 'domain', 'url', 'hash']:
            self.logger.error('Invalid sample data type: %s', datatype)
            raise ValueError
        with StringIO() as sample:
            sample.write(SAMPLE_DATA[datatype])
            sample.seek(0)
            data = [{'name': 'sampledata', 'content': i}
                    for i in csv.DictReader(sample)]
        amount = min(len(data), random.randint(5, 10))
        sample_data = random.sample(data, amount)
        return {'links': {},
                'entry': sample_data}

    def handle_scheduler(self, in_dict, app_env):
        """Download risk lists and alerts."""
        self.logger.info('handle_sheduler entered.')
        rfe_rest.scheduler(app_env, self.logger)
        return {'links': {},
                'entry': [{'name': 'debug',
                           'content': 'success'}]}

    def handle_lookup_alert(self, in_dict, app_env):
        """Fetch the details of an alert."""
        self.logger.info('handle_lookup_alert entered.')
        try:
            alert_id = in_dict['path_info'].split('/')[1]
            payload = rfe_rest.fetch_alert(app_env,
                                           alert_id,
                                           self.logger)
        except IndexError as err:
            self.logger.info('No stanza attached to the REST API call: %s',
                             err)
            raise
        except Exception as err:
            self.logger.error('Problem downloading alerts: %s', err)
            raise

        self.logger.info('Alert with ID: %s downloaded successfully', alert_id)

        return {'links': {},
                'entry': payload}

    def handle_config_get(self, in_dict, app_env):
        """Fetch current configuration."""
        self.logger.info('handle_config_get entered.')

        def fix_data(rl_dict, name):
            rl_dict['name'] = name
            rl_dict.pop('disabled')
            return rl_dict

        def default_last(rl):
            if rl['name'] in ['rf_ip_risklist',
                              'rf_domain_risklist',
                              'rf_hash_risklist',
                              'rf_vulnerability_risklist',
                              'rf_url_risklist']:
                return 1
            return 0

        payload = dict()
        payload['name'] = 'configuration'
        payload['risklists'] = sorted([fix_data(v, k)
                                       for k, v
                                       in app_env.risklists.items()],
                                      key=lambda x: (default_last(x),
                                                     x['name']))
        payload['alerts'] = sorted([fix_data(v, k)
                                    for k, v
                                    in app_env.alerts.items()],
                                   key=lambda x: x['name'])
        payload['api_url'] = app_env.api_url
        payload['proxy'] = {
            'proxy_username':
                app_env.my_config['proxy'].get('proxy_username', ''),
            'proxy_url':
                app_env.my_config['proxy'].get(
                    'proxy_url', ''),
            'proxy_port':
                app_env.my_config['proxy'].get(
                    'proxy_port', ''),
            'proxy_rdns':
                app_env.my_config['proxy'].get(
                    'proxy_rnds', ''),
            'proxy_enabled':
                app_env.my_config['proxy'].get(
                    'proxy_enabled', '')}
        payload['logging'] = app_env.log_level
        payload['ssl_verify'] = "1" if app_env.verify else "0"
        self.logger.debug('Configuration sent to Splunk.')
        return {'links': {},
                'entry': [{'name': 'configuration', 'content': payload}]}

    def handle_config_post(self, in_dict, app_env):
        """Handle configuration updates."""
        self.logger.info('handle_config_post entered.')
        try:
            return {'links': {},
                    'entry': [{'name': 'configuration_output',
                               'content':
                               rfe_rest.write_configuration(in_dict,
                                                            app_env,
                                                            self.logger)}]}
        except Exception as err:
            self.logger.error('Failed to save config: %s' % err)
            return {'links': {},
                    'entry': [{'name': 'configuration_output',
                               'content': {'message':
                                           'Failed due to: %s' % err,
                                           'error': True}}]}

    def handle_head_risk_lists(self, in_dict, app_env):
        """Handle HEADing Risk Lists."""
        self.logger.info('handle_head_risk_lists entered.')
        return {'links': {},
                'entry': rfe_rest.head_fusion_files(app_env, self.logger)}

    def handle(self, in_string):
        """Route REST calls."""
        # Phase one: fetch api_token
        try:
            in_dict = json.loads(in_string)
            app_env = RfeAppEnv(in_dict, self.logger)
        except Exception as err:
            self.logger.error('Failed to create AppEnv object: %s', err,
                              exc_info=True)
            return {
                'payload': {
                    'links': {},
                    'entry': [
                        {
                            'name': 'debug',
                            'content': 'Failed to create AppEnv object.'}]},
                'status': 500}

        # Phase two: get info about the environment.
        try:
            self.logger.setLevel(app_env.log_level)
        except Exception:
            self.logger.error('Failed to map environment', exc_info=True)
            raise
        else:
            self.logger.debug('Loglevel set to %s', app_env.log_level)

        # Phase three: handle the request.
        try:
            if in_dict['path_info'] == 'alerts_metadata':
                payload = self.handle_alerts_metadata(in_dict, app_env)
                status = 200
            elif in_dict['path_info'] == 'configuration':
                if in_dict['method'] == 'GET':
                    payload = self.handle_config_get(in_dict, app_env)
                    status = 200
                elif in_dict['method'] == 'POST':
                    payload = self.handle_config_post(in_dict, app_env)
                    status = 200
            elif in_dict['path_info'] == 'scheduler':
                payload = self.handle_scheduler(in_dict, app_env)
                status = 200
            elif in_dict['path_info'] == 'sample_data':
                payload = self.handle_sample_data(in_dict, app_env)
                status = 200
            elif in_dict['path_info'] == 'debug':
                # XXX: Should we filter out sensitive data? Ex session keys?
                payload = {'links': {},
                           'entry': [{'name': 'debug',
                                      'content': in_dict}]}
                status = 200
            elif in_dict['path_info'].startswith('download_risklist'):
                status, payload = self.handle_download_risklist(in_dict,
                                                                app_env)
            elif in_dict['path_info'] == 'head_risklists':
                payload = self.handle_head_risk_lists(in_dict, app_env)
                status = 200
            elif in_dict['path_info'].startswith('download_alert'):
                payload = self.handle_download_alerts(in_dict, app_env)
                status = 200
            elif in_dict['path_info'] == 'lookup_alert':
                payload = self.handle_lookup_alert(in_dict, app_env)
                status = 200
            elif in_dict['path_info'].startswith('lookup_'):
                payload = {
                    'entry': [
                        {
                            'name': in_dict['path_info'].split('/')[0],
                            'content': self.handle_lookup(in_dict, app_env)
                        }
                    ]}
                status = 200
            elif in_dict['path_info'].startswith('search_'):
                res = self.handle_search(in_dict, app_env)
                # pylint: disable=no-member
                reslist = [{'name': ent['id'],
                            'content': rfe_enrich.fold_json(ent)}
                           for ent in res]
                payload = {
                    'entry': reslist
                }
                status = 200  # HTTP status code
            elif in_dict['path_info'] == 'validate':
                payload = self.handle_validate(in_dict, app_env)
                status = 200  # HTTP status code
            else:
                payload = mk_payload(r'Page not found: %s' % (
                    in_dict['path_info']))
                status = 404
        except Exception as err:
            self.logger.error(r'failed during handling phase: %s',
                              err, exc_info=True)
            payload = mk_payload('Internal error in handling phase: '
                                 r'%s\n%s' % (err, traceback.format_exc()))
            status = 500
        else:
            self.logger.debug('handler completed successfully')

        return {
            'payload': payload,
            'status': status
        }

    def setup_logging(self):
        """Setup logging."""
        logger = logging.getLogger(__name__)
        if len(logger.handlers):
            return logger

        splunk_home = os.environ['SPLUNK_HOME']

        logging_default_config_file = os.path.join(splunk_home,
                                                   'etc', 'log.cfg')
        logging_local_config_file = os.path.join(splunk_home,
                                                 'etc', 'log-local.cfg')
        logging_stanza_name = 'python'
        logging_file_name = "ta_recordedfuture_cyber_rest.log"
        base_log_path = os.path.join('var', 'log', 'splunk')
        logging_format = "%(asctime)s %(levelname)-s\t%(module)s:" \
                         "%(lineno)d - %(message)s"
        splunk_log_handler = logging.handlers.RotatingFileHandler(
            os.path.join(splunk_home, base_log_path, logging_file_name),
            mode='a', maxBytes=10000000, backupCount=5)
        splunk_log_handler.setFormatter(logging.Formatter(logging_format))
        logger.addHandler(splunk_log_handler)
        splunk.setupSplunkLogger(logger,
                                 logging_default_config_file,
                                 logging_local_config_file,
                                 logging_stanza_name)
        return logger


def mk_payload(message):
    """Insert payload message in the proper structure."""
    return {
        'entry': [
            {
                'name': 'error',
                'payload': message
            }
        ]
    }
