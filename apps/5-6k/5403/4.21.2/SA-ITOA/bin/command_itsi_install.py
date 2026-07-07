# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import json
import sys
import uuid

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

import itsi_path
from urllib.parse import quote_plus

from SA_ITOA_app_common.splunklib.searchcommands import Configuration, Option, GeneratingCommand, dispatch, validators

from ITOA.setup_logging import InstrumentCall, logger

from splunk import rest, RESTException, ResourceNotFound
from itsi.itsi_utils import ItsiMacroReader


@Configuration()
class ItsiInstallCommand(GeneratingCommand):

    is_noah_enabled = Option(
        doc='''
            **Syntax:** **is_noah_enabled=***<Boolean>*
            **Description:** Is the deployment on Noah?''',
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    def make_request(self, session_key, path, method='GET', params=None):
        """
        make GET/POST to a path
        :param path: the path of an endpoint
        :type path: str
        :param method: one of ['GET', 'POST']
        :type method: str
        :param params: params that send out with the request
        :type params: dict
        :return: content from the returned request
        :rtype: json
        """
        args = {'output_mode': 'json'}
        args.update(params if params else {})
        response = None
        content = None
        try:
            if method == 'GET':
                response, content = rest.simpleRequest(
                    path,
                    method=method,
                    getargs=args,
                    sessionKey=session_key,
                    raiseAllErrors=False
                )
            elif method == 'POST':
                response, content = rest.simpleRequest(
                    path,
                    method=method,
                    postargs=args,
                    sessionKey=session_key,
                    raiseAllErrors=False
                )
        except Exception as e:
            raise RESTException(500, '%s' % e)
        if response.status != 200:
            raise RESTException(response.status, 'Received unexpected results from dispatcher: {}'.format(content))
        return json.loads(content)

    def get_conf_stanza(self, session_key, conf_name, stanza_name, app='SA-ITOA'):
        """
        Create conf stanza by calling splunk conf endpoints

        @type session_key: string
        @param session_key: session_key

        @type conf_name: string
        @param conf_name: conf file name

        @type stanza_name: dict
        @param stanza_name: dict of data to post

        @type app: string
        @param app: itsi_module name

        @rtype: dict
        @return: response dictionary

        """
        getargs = {'output_mode': 'json'}
        rest_path = self.get_conf_rest_path(conf_name, app) + '/' + quote_plus(stanza_name)
        response, content = rest.simpleRequest(
            rest_path,
            method='GET',
            getargs=getargs,
            sessionKey=session_key,
            raiseAllErrors=True
        )
        return {'response': response, 'content': json.loads(content)['entry'][0]['content']}

    def get_conf_rest_path(self, conf_name, app='SA-ITOA', host_base_uri=''):
        """
        builds the configuration restpath
        @type conf_name: String
        @param: conf_name: configuration file name

        @type app: string
        @param app: itsi_module name

        @type host_base_uri: string
        @param app: base uri

        @rtype: String
        @return: return response

        """
        if host_base_uri:
            return host_base_uri + '/servicesNS/nobody/' + app + '/configs/conf-' + conf_name
        else:
            return rest.makeSplunkdUri() + 'servicesNS/nobody/' + app + '/configs/conf-' + conf_name

    def create_conf_property(self, session_key, conf_name, conf_stanza, data_to_post, app='SA-ITOA'):
        """
        Create conf stanza by calling splunk conf endpoints

        @type session_key: string
        @param session_key: session_key

        @type conf_name: string
        @param conf_name: conf file name

        @type conf_stanza: dict
        @param conf_stanza: dict of data to post

        @type data_to_post: string
        @param data_to_post: {stanza_name: {param_name: param_value}}

        @type app: string
        @param app: itsi_module name

        @rtype: tuple
        @return: response and content or raise an exception
        """
        postargs = data_to_post[conf_stanza]
        postargs['output_mode'] = 'json'
        try:
            self.get_conf_stanza(session_key, conf_name, conf_stanza, app)['content']  # detect if stanza already exists
            rest_path = self.get_conf_rest_path(conf_name, app) + '/' + quote_plus(conf_stanza)
            logger.info('Making API call to add conf flag with %s, postargs: %s, method: POST' % (
                rest_path, postargs))
            response, content = rest.simpleRequest(
                rest_path,
                method='POST',
                postargs=postargs,
                sessionKey=session_key,
                raiseAllErrors=True
            )

        except ResourceNotFound:
            rest_path = self.get_conf_rest_path(conf_name, app)
            postargs['name'] = conf_stanza
            logger.info('Making API call to add conf flag with %s, postargs: %s, method: POST' % (
                rest_path, postargs))
            response, content = rest.simpleRequest(
                rest_path,
                method='POST',
                postargs=postargs,
                sessionKey=session_key,
                raiseAllErrors=True
            )

        return {'response': response, 'content': content}

    def execute_add_action_config(self, conf_name, stanza_name, app_name, param_name, param_value, session_key):
        """
        executes add action of the configuration
        :param conf_name: configuration file name
        :param stanza_name: stanza name to be updated
        :param app_name: app name
        :param param_name: new parameter name
        :param param_value: new parameter value
        :param session_key: the splunkd session key for the request
        :type session_key: string
        :return: None
        """
        logger.info('Starting component config add, configuration:%s.%s.%s.%s' % (app_name,
                                                                                  conf_name,
                                                                                  stanza_name,
                                                                                  param_name))
        try:
            # call the create property api with new parameter value
            logger.info(
                'Executing component config add, adding property:%s.%s.%s.%s' % (app_name,
                                                                                 conf_name,
                                                                                 stanza_name,
                                                                                 param_name))
            data_to_post = {stanza_name: {param_name: param_value}}
            logger.info(
                "Executing component config add, the data_to_post:%s" % (data_to_post))
            self.create_conf_property(session_key, conf_name, stanza_name, data_to_post, app_name)
            logger.info(
                'Finished component config add, configuration:%s.%s.%s.%s' % (app_name,
                                                                              conf_name,
                                                                              stanza_name,
                                                                              param_name))
        except RESTException as e:
            if e.statusCode == 409:
                logger.info(
                    'Finished component config add, config stanza %s.%s.%s already exists' % (app_name,
                                                                                              conf_name,
                                                                                              stanza_name))

            else:
                logger.error(
                    "Failed component config add, failed to add stanza configuration:%s" % (e))
                raise e

    def reload_inputs(self, app, session_key):
        """
        Reload inputs for an app
        :param app: the app for which to refresh inputs
        :type app: string
        :param session_key: the splunkd session key for the request
        :type session_key: string
        :return: None
        """
        path = "%sservicesNS/nobody/%s/data/inputs" % (rest.makeSplunkdUri(), app)
        logger.info('Reloading inputs, retrieving inputs for app %s by calling %s' % (app, path))
        content = self.make_request(session_key, path)
        for entry in content['entry']:
            input_name = entry['name']
            if "_reload" not in entry['links'] or \
                    input_name == 'tcp' or input_name.startswith('tcp://'):  # Reloading tcp inputs will return 404.
                logger.info("Reloading inputs, input name %s for app %s does not support reload, skipped." % (
                    input_name, app))
                continue
            logger.info('Reloading inputs, reloading input %s in app %s' % (input_name, app))
            self.make_request(session_key,
                              "%s%s" % (rest.makeSplunkdUri(), entry['links']['_reload']),
                              method='POST')

    def generate(self):
        logger.info("Running search command 'itsiinstall'")
        try:
            itsi_notable_archive_macro = ItsiMacroReader(self.service.token, 'itsi_notable_archive_index')
            itsi_notable_audit_macro = ItsiMacroReader(self.service.token, 'itsi_notable_audit_index')
            itsi_grouped_alerts_macro = ItsiMacroReader(self.service.token, 'itsi_grouped_alerts_index')
            itsi_tracked_alerts_macro = ItsiMacroReader(self.service.token, 'itsi_tracked_alerts_index')
            itsi_import_objects_macro = ItsiMacroReader(self.service.token, 'get_itsi_import_objects_index')
            itsi_nats_metrics_macro = ItsiMacroReader(self.service.token, 'itsi_nats_metrics_index')

            MISCELLANEOUS = {
                'splunk_httpinput': {
                    'disabled': {
                        'http': '0'
                    }
                },
                'SA-ITOA': {
                    'disabled': {
                        'itsi_notable_event_hec_init://default_hec_initializer': '1',
                        'itsi_hec_init://bulk_import_hec_initializer': '1',
                        'http://Auto Generated ITSI Event Management Token': '0',
                        'http://itsi_group_comments_token': '0',
                        'http://itsi_bulk_import_token': '0',
                        'http://nats_hec': '0'

                    },
                    'index': {
                        'http://Auto Generated ITSI Notable Event Retention Policy Token': itsi_notable_archive_macro.index,
                        'http://Auto Generated ITSI Notable Index Audit Token': itsi_notable_audit_macro.index,
                        'http://itsi_group_alerts_token': itsi_grouped_alerts_macro.index,
                        'http://itsi_group_alerts_sync_token': itsi_grouped_alerts_macro.index,
                        'http://Auto Generated ITSI Event Management Token': itsi_tracked_alerts_macro.index,
                        'http://itsi_group_comments_token': itsi_grouped_alerts_macro.index,
                        'http://itsi_bulk_import_token': itsi_import_objects_macro.index,
                        'http://nats_hec': itsi_nats_metrics_macro.index
                    },
                    'indexes': {
                        'http://Auto Generated ITSI Notable Event Retention Policy Token': itsi_notable_archive_macro.index,
                        'http://Auto Generated ITSI Notable Index Audit Token': itsi_notable_audit_macro.index,
                        'http://itsi_group_alerts_token': itsi_grouped_alerts_macro.index,
                        'http://itsi_group_alerts_sync_token': itsi_grouped_alerts_macro.index,
                        'http://Auto Generated ITSI Event Management Token': itsi_tracked_alerts_macro.index,
                        'http://itsi_group_comments_token': itsi_grouped_alerts_macro.index,
                        'http://itsi_bulk_import_token': itsi_import_objects_macro.index,
                        'http://nats_hec': itsi_nats_metrics_macro.index
                    },
                    'source': {
                        'http://Auto Generated ITSI Notable Index Audit Token': 'Notable Event Audit',
                        'http://itsi_group_alerts_token': 'itsi_group_alerts',
                        'http://itsi_group_alerts_sync_token': 'itsi_group_alerts',
                        'http://itsi_group_comments_token': 'Notable Event Comment',
                        'http://itsi_bulk_import_token': 'itsi bulk import',
                        'http://nats_hec': 'nats'
                    },
                    'sourcetype': {
                        'http://Auto Generated ITSI Notable Event Retention Policy Token': 'itsi_notable:archive',
                        'http://Auto Generated ITSI Notable Index Audit Token': 'itsi_notable:audit',
                        'http://itsi_group_alerts_token': 'itsi_notable:group',
                        'http://itsi_group_alerts_sync_token': 'itsi_notable:group',
                        'http://Auto Generated ITSI Event Management Token': 'itsi_notable:event',
                        'http://itsi_group_comments_token': 'itsi_notable:comment',
                        'http://itsi_bulk_import_token': 'itsi_import_objects:csv'
                    },
                    'token': {
                        'http://Auto Generated ITSI Notable Event Retention Policy Token': str(uuid.uuid4()),
                        'http://Auto Generated ITSI Notable Index Audit Token': str(uuid.uuid4()),
                        'http://itsi_group_alerts_token': str(uuid.uuid4()),
                        'http://itsi_group_alerts_sync_token': str(uuid.uuid4()),
                        'http://Auto Generated ITSI Event Management Token': str(uuid.uuid4()),
                        'http://itsi_group_comments_token': str(uuid.uuid4()),
                        'http://itsi_bulk_import_token': str(uuid.uuid4()),
                        'http://nats_hec': str(uuid.uuid4())
                    }
                }
            }
            if self.is_noah_enabled:
                logger.info("Noah is enabled, proceeding with 'itsiinstall'")
                for app, modinputs in MISCELLANEOUS.items():  # set miscellaneous configs in local inputs.conf for mod inputs
                    for key, stanzas in modinputs.items():
                        for stanza_name, value in stanzas.items():
                            self.execute_add_action_config('inputs', stanza_name, app, key, value, self.service.token)
                self.reload_inputs('SA-ITOA', self.service.token)
            else:
                logger.info("Noah is not enabled, exiting 'itsiinstall'")
            logger.info("Completed running 'itsiinstall'")
            yield {}
        except Exception as e:
            # Explicitly specify Exception message due to missing Python3 support in error_exit()
            self.error_exit(e, message=str(e))


dispatch(ItsiInstallCommand, sys.argv, sys.stdin, sys.stdout, __name__)
