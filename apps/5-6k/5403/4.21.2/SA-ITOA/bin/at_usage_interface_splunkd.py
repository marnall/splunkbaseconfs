# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import traceback
from collections import defaultdict

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

import itsi_path
import itsi_py3

from ITOA.setup_logging import getLogger
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import ItoaInterfaceProvider

from itsi.objects.itsi_service import ItsiService
from itsi.objects.itsi_kpi_threshold_template import ItsiKpiThresholdTemplate


logger = getLogger()
logger.debug('Initialized AT Usage REST splunkd handler interface log')


class ATUsageProviderSplunkd(ItoaInterfaceProvider):
    '''
    This wrapper class for the REST provider in internal ATUsageProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    '''
    def __init__(self, system_auth_token):
        '''
        Constructor for provider for the interface

        @type: string
        @param system_auth_token: the splunkd system level authorization token

        '''
        self.session_key = system_auth_token
        self.owner = 'nobody'

    def get_at_usage_data(self):
        try:
            at_services = self.fetch_at_enabled_services()
            pred_templates = [template['_key'] for template in self.fetch_predefined_kpi_threshold_templates()]

            usage_data = {
                'kpis_using_at': 0,
                'kpis_using_policies': defaultdict(int),
                'kpis_using_threshold_templates': defaultdict(int),
                'kpis_using_custom_threshold_templates': defaultdict(int),
                'kpis_using_custom_thresholds': 0,
                'kpis_using_recommendation': 0,
                'kpis_with_recommendations_modified': 0,
                'services_using_at': 0,
                'services_using_custom_thresholds': 0,
                'services_using_recommendation': 0,
                'services_with_recommendations_modified': 0,
                'min_threshold_level': defaultdict(int),
                'max_threshold_level': defaultdict(int)
            }

            for service in at_services:
                service_data = {
                    'kpis_using_at': 0,
                    'kpis_using_recommendation': 0,
                    'kpis_using_custom_thresholds': 0,
                    'kpis_with_recommendations_modified': 0
                }
                for kpi in service['kpis']:

                    # Collect data if and only if AT enabled
                    if not kpi.get('adaptive_thresholds_is_enabled'):
                        continue

                    service_data['kpis_using_at'] += 1
                    kpi_threshold_template_id = kpi.get('kpi_threshold_template_id')

                    if kpi.get('is_recommended_time_policies', False):
                        service_data['kpis_using_recommendation'] += 1
                        if kpi.get('was_recommendation_modified', False):
                            # Modified recommendations
                            service_data['kpis_with_recommendations_modified'] += 1
                    elif kpi_threshold_template_id:
                        if kpi_threshold_template_id in pred_templates:
                            usage_data['kpis_using_threshold_templates'][kpi_threshold_template_id] += 1
                        else:
                            usage_data['kpis_using_custom_threshold_templates'][kpi_threshold_template_id] += 1
                    else:
                        service_data['kpis_using_custom_thresholds'] += 1
                    temp_kpi_usage_data = defaultdict(bool)
                    time_variate_thresholds_spec = kpi.get('time_variate_thresholds_specification', None)
                    if not time_variate_thresholds_spec or not time_variate_thresholds_spec.get('policies', None):
                        # Skip when time_variate_thresholds_specifications are not set on the KPI
                        continue
                    for policy_title, policy in time_variate_thresholds_spec['policies'].items():
                        policy_type = policy['policy_type']
                        temp_kpi_usage_data[policy_type] = True
                        # Collect data for only AT policies
                        if policy_type == 'static':
                            continue
                        for t_level in policy['aggregate_thresholds']['thresholdLevels']:
                            # Minimum threshold levels for each policy
                            usage_data['min_threshold_level'][policy_type] = min(
                                usage_data['min_threshold_level'][policy_type],
                                t_level['dynamicParam'])
                            # Maximun threshold levels for each policy
                            usage_data['max_threshold_level'][policy_type] = max(
                                usage_data['max_threshold_level'][policy_type],
                                t_level['dynamicParam'])

                    for type, being_used in temp_kpi_usage_data.items():
                        if being_used:
                            usage_data['kpis_using_policies'][type] += 1

                # Gather services data
                if service_data['kpis_using_at'] > 0:
                    usage_data['services_using_at'] += 1
                    usage_data['kpis_using_at'] += service_data['kpis_using_at']
                if service_data['kpis_using_custom_thresholds'] > 0:
                    usage_data['services_using_custom_thresholds'] += 1
                    usage_data['kpis_using_custom_thresholds'] += service_data['kpis_using_custom_thresholds']
                if service_data['kpis_using_recommendation'] > 0:
                    usage_data['services_using_recommendation'] += 1
                    usage_data['kpis_using_recommendation'] += service_data['kpis_using_recommendation']
                if service_data['kpis_with_recommendations_modified'] > 0:
                    usage_data['services_with_recommendations_modified'] += 1
                    usage_data['kpis_with_recommendations_modified'] += service_data['kpis_with_recommendations_modified']

            return self.render_json({'data': usage_data})
        except Exception:
            tb = traceback.format_exc()
            return self.render_json({
                'status': 500,
                'payload': 'Error: ' + str(tb)
            })

    def fetch_at_enabled_services(self):
        """
        Fetches all ITSI services which are enabled and using Adaptive Thresholding
        @return list of services
        """

        service_object = ItsiService(self.session_key, self.owner)
        return service_object.get_bulk(
            'nobody',
            fields=['title', '_key',
                    'kpis._key',
                    'kpis.time_variate_thresholds_specification',
                    'kpis.kpi_threshold_template_id',
                    'kpis.is_recommended_time_policies',
                    'kpis.was_recommendation_modified',
                    'kpis.adaptive_thresholds_is_enabled'],
            filter_data={'$and': [
                {'enabled': 1},
                {'kpis.adaptive_thresholds_is_enabled': True},
            ]}
        )

    def fetch_predefined_kpi_threshold_templates(self):
        """
        Fetches all predefind KPI threshold templates
        @return list of predefined templates
        """
        tampate_object = ItsiKpiThresholdTemplate(self.session_key, self.owner)
        return tampate_object.get_bulk(
            'nobody',
            fields=['_key'],
            filter_data={'_immutable': 1}
        )


class ATUsageInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):

    '''
    Class implementation for REST handler for Adaptive Thresholding Usage
    '''
    def __init__(self, command_line, command_arg):
        '''
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        '''
        super(ATUsageInterfaceSplunkd, self).__init__()

    def migration_check(self, session_key):
        '''
        Override migration_check in SplunkdRestInterfaceBase
        MigrationInterfaceSplunkd should be accessible during migration and serve request regardless of migration
        running
        Thus override migration_check of SplunkdRestInterfaceBase
        '''
        pass

    def handle(self, args):
        '''
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        '''
        return self._default_handle(args)

    def _dispatch_to_provider(self, args):
        '''
        Parses the REST path on the interface to help route to respective handlers
        This handler's thin layer parses the paths and routes actual handling for the call
        to ATUsageInterfaceSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        '''
        if not isinstance(args, dict):
            message = 'Invalid REST args received by Adaptive Thresholding Usage interface - {}'.format(args)
            raise ItoaValidationError(message=message, logger=logger)

        system_auth_token = args['system_authtoken']

        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by Adaptive Thresholding Usage interface - {}'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 1) or (path_parts[0] != 'at_usage_data'):
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))

        interface_provider = ATUsageProviderSplunkd(system_auth_token)
        return interface_provider.get_at_usage_data()
