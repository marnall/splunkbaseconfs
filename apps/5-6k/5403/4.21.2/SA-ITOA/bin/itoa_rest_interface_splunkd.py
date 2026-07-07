# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import operator
import http

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))
from user_access_utils import CheckUserAccess

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'bin']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
import itsi_py3

from urllib.parse import unquote

from ITOA.setup_logging import getLogger

logger = getLogger()

from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.itoa_common import is_feature_enabled, toggle_mod_input, mod_input_reload

from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import (
    ItoaInterfaceProvider,
    get_supported_itoa_object_types,
    get_interactable_object_types,
    get_privatizeable_object_types
)
from itsi.access_control.splunkd_controller_rbac_utils import EnforceRBACSplunkd
from itsi.itsi_utils import CAPABILITY_MATRIX
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.searches.itsi_filter import ITSI_FILTER_MODE_ADVANCED, ITSI_FILTER_MODE_SIMPLE

logger.debug("Initialized ITOA REST splunkd handler interface log")


def NormalizeRESTRequestForSharedObjects(function):
    """
    Decorator for shared object types
    Applicable only to object types deep_dive and glass_table

    This decorator is custom built for ItoaRestInterfaceProviderSplunkd and makes assumptions about
    methods/attributes from the class

    @param args: arguments passed to the decorator
    @param kwargs: key value args passed to the decorator
        do stuff iff:
        - there is an 'owner' and 'object' in kwargs.
        - 'object' is either 'glass_table' or 'deep_dive'
        normalize 'owner' to 'nobody'
    """

    def wrapper(self, *args, **kwargs):
        def is_true(var):
            """
            utility method to check if value of var implies true

            @type: boolean
            @param var: the variable under question

            @type: variable
            @param type: string, bool, number types

            @rtype: boolean
            @return False by default, True if it matches criteria
            """
            is_true = False
            if isinstance(var, itsi_py3.string_type):
                if var.strip().lower() == 'true' or var.strip().lower().startswith('yes'):
                    is_true = True
            elif isinstance(var, bool):
                is_true = var
            elif isinstance(var, (int, float, complex)):
                if int(var) > 0:
                    is_true = True
            return is_true

        owner = args[0]
        object_type = args[1]
        filter_data = kwargs.get('filter')

        if filter_data:
            filter_data = json.loads(filter_data)

        new_owner = owner
        if owner is not None and object_type in get_privatizeable_object_types():
            new_owner = 'nobody'
            if self._rest_method == 'GET' and filter_data is not None:
                is_shared = is_true(filter_data.get('shared'))
                if is_shared:
                    if owner == 'nobody':
                        filter_data['_owner'] = 'nobody'
                    else:
                        filter_data['$or'] = [{'_owner': 'nobody'}, {'_owner': owner}]
                else:
                    filter_data['_owner'] = owner
                filter_data.pop('shared', None)  # useless here on - not sent when creating
                kwargs['filter'] = json.dumps(filter_data)
        new_list = [unquote(a) for a in args[1:]]
        new_args = (new_owner,) + tuple(new_list)
        return function(self, *new_args, **kwargs)

    return wrapper


class ItoaRestInterfaceProviderSplunkd(ItoaInterfaceProvider):
    """
    This wrapper class for the REST provider in ItoaInterfaceProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    """

    def __init__(self, session_key, current_user, rest_method):
        """
        The decorator invoked wrapper for the decorated function (REST handler)
        This wrapper does the access check on the REST request and throws an exception if access is denied

        @type: string
        @param session_key: the splunkd session key for the request

        @type: string
        @param current_user: current user invoking the request

        @type: string
        @param: type of REST method of this request, GET/PUT/POST/DELETE
        """
        self._setup(session_key, current_user, rest_method)

    def get_supported_object_types(self):
        """
        Method to get supported ITOA object for this interface

        @type: object
        @param self: the self reference

        @rtype: json
        @return: json of the supported objects list
        """
        return self.get_supported_object_types_json()

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def load_csv(self, owner, **kwargs):
        """
        Method to perform bulk import of CSV data

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the updated objects list
        """
        return self._bulk_csv_import(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def bulk_update(self, owner, object_type, **kwargs):
        """
        Method to perform bulk updates on objects

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the update
        """
        return self._bulk_update(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def bulk_entities_update(self, owner, object_type, **kwargs):
        """
        Method to bulk update entity fields

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the update
        """
        return self._bulk_entities_update(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def retire_entities(self, owner, object_type, **kwargs):
        """
        Method to bulk update entities and set them to retired

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the update
        """
        return self._manage_entities(owner, object_type, retire_entities=True, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def restore_entities(self, owner, object_type, **kwargs):
        """
        Method to bulk update retired entities and change them to unretired

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the update
        """
        return self._manage_entities(owner, object_type, retire_entities=False, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def count_retirable_entities(self, owner, object_type, **kwargs):
        """
        Method to bulk update entities and set them to retired

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: dictionary of retirable entities
        """
        return self.count_of_retirable_entities(owner,
                                                object_type,
                                                retire_entities=False,
                                                **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def retire_retirable_entities(self, owner, object_type, **kwargs):
        """
        Method to bulk update entities and set them to retired

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the update
        """
        return self.retire_all_retirable_entities(owner,
                                                  object_type,
                                                  retire_entities=True,
                                                  **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='entity', logger=logger)
    def bulk_delete_retired_entities(self, owner, object_type, **kwargs):
        """
        Method to bulk delete retired entities

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the deletion operation
        """
        if not is_feature_enabled('itsi-bulk-delete-retired-entities', session_key=self._session_key):
            raise ITOAError(status=http.HTTPStatus.METHOD_NOT_ALLOWED,
                            message='Bulk delete of retired entities feature is not enabled.')
        return self.delete_retired_entities(owner,
                                            object_type,
                                            **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='custom_threshold_windows', logger=logger)
    def associate_ctw_kpis(self, owner, object_id, **kwargs):
        """
        Method to update ctw object and set proper association

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the update
        """
        return self._associate_ctw_kpis(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='custom_threshold_windows', logger=logger)
    def disconnect_kpis_from_ctw(self, owner, ctw_id, **kwargs):
        """
        Method to disconnect Custom Threshold Window object from corresponding KPIs/Services

        @type: object
        @param self: the self reference

        @type: string
        @param owner: user making the request

        @type: string
        @param ctw_id: Id of CTW object to be disconnected from KPI/Services

        @type: dictionary
        @param kwargs: dictionary of service_id to list of kpi_ids entries

        @rtype: string
        @return: ID of CTW object successfully disconnected from KPIs
        """
        # Call the interface_provider function
        return self._disconnect_kpis_from_ctw(owner, ctw_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='custom_threshold_windows', logger=logger)
    def get_ctws_by_kpi(self, owner, kpi_id, **kwargs):
        """
        Method to fetch a list of CTWs that are associated with the passed-in KPI ID

        @type: string
        @param owner: owner making the request

        @type: string
        @param kpi_id: ID of the KPI

        @rtype: json
        @return: result of the fetch (containing a list of CTWs)
        """
        return self._get_ctws_by_kpi(owner, kpi_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='custom_threshold_windows', logger=logger)
    def get_linked_kpis(self, owner, **kwargs):
        """
        Method to fetch a list of service/kpis that are associated with the passed in threshold_window_id

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the fetch
        """
        return self._get_linked_kpis(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='custom_threshold_windows', logger=logger)
    def stop_active_ctw(self, owner, ctw_id, **kwargs):
        """
        Stop an active custom threshold window

        @type: string
        @param owner: owner making the request

        @type: string
        @param ctw_id: key of the CTW object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: stopped CTW object
        """
        return self._stop_active_ctw(owner, ctw_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='custom_threshold_windows', logger=logger)
    def bulk_stop_active_ctws(self, owner, **kwargs):
        """
        Stop multiple active custom threshold windows

        @type: string
        @param owner: owner making the request

        @rtype: json
        @return: list of stopped CTW objects
        """
        return self._bulk_stop_active_ctws(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='service', logger=logger)
    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='kpi_threshold_template', logger=logger)
    def shift_time_offset(self, owner, **kwargs):
        """
        Function to shift the offset in object's time policy

        @type: string
        @param owner: owner making the request

        @rtype: json
        @return: message
        """
        return self._shift_time_offset(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='kpi', logger=logger)
    def get_drift_kpis(self, owner, **kwargs):
        """
        Function to shift the offset in object's time policy

        @type: string
        @param owner: owner making the request

        @rtype: json
        @return: message
        """
        return self._get_drift_kpis(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='at_incremental_values', logger=logger)
    def get_at_incremental_values(self, owner, kpi_id, **kwargs):
        """
        GET request that fetches the incremental learning values for a KPI id

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param kpi_id: KPI id of the KPI to fetch incremental values for

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the fetch
        """
        return self._get_at_incremental_values(owner, kpi_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='upgrade_readiness_prechecks', logger=logger)
    def get_precheck_details(self, owner, precheck_id, **kwargs):
        """
        GET request that fetches the precheck details and returns as a dict of items based on precheck_id provided

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param precheck_id: unique id of the precheck that is failing

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the fetch
        """
        return self._get_precheck_details(owner, precheck_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='upgrade_readiness_prechecks', logger=logger)
    def start_new_upgrade_readiness_precheck(self):
        """
        POST request that starts a new precheck and

        @type: object
        @param self: the self reference

        @rtype: json
        @return: transaction id, status and message of the new precheck
        """
        return self._start_new_upgrade_readiness_precheck()

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='upgrade_readiness_prechecks', logger=logger)
    def remediate_failed_precheck(self, precheck_id):
        """
        POST request that remediates a failed precheck

        @type: object
        @param self: the self reference

        @type: string
        @param precheck_id: unique id of the failed precheck

        @rtype: json
        @return: transaction id, status and message of the new remediation
        """
        return self._remediate_failed_precheck(precheck_id)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX,
                     object_type='upgrade_readiness_prechecks', logger=logger)
    def get_remediation_details(self, owner, precheck_id, **kwargs):
        """
        GET request that fetches the precheck details and returns as a dict of items based on precheck_id provided

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param precheck_id: unique id of the precheck that is failing

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: result of the fetch
        """
        return self._get_remediation_details(owner, precheck_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def generate_entity_filter(self, owner, **kwargs):
        """
        Endpoint which can be used to generate  an entity filter that is
        consumable by KPI search strings. A nice thing about this endpoint is
        that it can be invoked within a Splunk search command using "| rest".
        The purpose of this endpoint is to generate entity filters on the fly
        at search time. This is achieved by invoking this endpoint from within a subsearch.
        For more, see ITOA-5990.

        @type owner: basestring
        @param owner: string indicating owner of this call.

        @type kwargs: dict
        @param kwargs: parameters; query params that are sent as part of request
            Mandatory keys:
                @type service_id: basestring
                @param service_id: identifier of the service that this KPI belongs to
            Other keys:
                @type entity_id_fields: basestring
                @param entity_id_fields: comma separated entity identifier fields as defined in KPI

        @rtype: basestring
        @return entity filter
        """
        logger.debug('Input args=%s', json.dumps(kwargs))
        return self._generate_entity_filter(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def get_kpi_searches(self, owner, **kwargs):
        """
        Method to generate KPI searches

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated search
        """
        return self._get_kpi_searches(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def get_unique_service_tags(self, owner, **kwargs):
        """
        Method to get unique set of service tags

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated search
        """
        return self._get_unique_service_tags(owner, **kwargs)

    def get_kpi_searches_gt(self, owner, **kwargs):
        """
        Method to generate KPI searches for data models in glass table ad hoc widgets

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated search
        """
        return self._get_kpi_searches(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def get_search_clause(self, owner, **kwargs):
        """
        Method to generate search clauses for KPI search construction

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated search clauses
        """
        return self._get_search_clause(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def preview_merge(self, owner, **kwargs):
        """
        Method to generate preview results of bulk CSV import

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the previewed objects
        """
        return self._preview_merge(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def get_alias_list(self, owner, **kwargs):
        """
        Method to get alias list

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the aliases
        """
        return self._get_alias_list(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def get_backfill_search(self, owner, **kwargs):
        """
        Method to generate backfill searches

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated searches
        """
        return self._get_backfill_search(owner, **kwargs)

    def get_dependent_kpis(self, owner, service_id, earliest_time='-60m', latest_time='now', **kwargs):
        """
        Method to retrieve all kpi dependencies

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param service_id: the service to find dependent kpis on

        @type: string
        @param earliest_time: the earliest time to search severity on

        @type: string
        @param latest_time: the latest time to search severity on

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the kpi dependencies
        """
        return self._get_dependent_kpis(owner, service_id, earliest_time, latest_time)

    def get_service_trees(self, owner, **kwargs):
        """
        Method to retrieve service tree

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the service tree
        """
        return self._get_service_trees(owner, **kwargs)

    def fetch_service_trees(self, owner, **kwargs):
        """
        Equivalent to get_service_trees but using a POST
        payload in place of GET querystring parameters

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the service tree
        """
        return self._fetch_service_trees(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    def get_sandbox_service_trees(self, owner, **kwargs):
        """
        Method to retrieve sandbox service tree

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the sandbox service tree
        """
        return self._get_sandbox_service_trees(owner, **kwargs)

    def get_linked_sandbox_services_for_template(self, owner, **kwargs):
        """
        Method to retrieve sandbox services with template information

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the service tree
        """
        return self._get_sandbox_services_for_template_with_status_info(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='kpi_entity_threshold', logger=logger)
    def kpi_entity_threshold_recommendations(self, owner, **kwargs):
        """
        Method to generate the policies from recommender response

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated policies
        """
        return self._kpi_entity_threshold_recommendations(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def kpi_threshold_recommendations(self, owner, **kwargs):
        """
        Method to generate the policies from recommender response

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the generated policies
        """
        return self._kpi_threshold_recommendations(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    def get_entity_filter(self, owner, **kwargs):
        """
        Method to get entity filters

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the entity filters
        """
        filter_mode = kwargs.get('filter_mode', ITSI_FILTER_MODE_ADVANCED)
        summary_only = kwargs.get('is_get_summary', False)
        if filter_mode == ITSI_FILTER_MODE_ADVANCED:
            method = self._get_entity_filter_summary if summary_only else self._get_entity_filter
            return method(owner, **kwargs)
        elif filter_mode == ITSI_FILTER_MODE_SIMPLE:
            return self._get_entity_from_simple_filter(owner, summary_only, **kwargs)
        else:
            raise ITOAError(status=400, message='Specified filter mode is invalid - {}.'.format(filter_mode))

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='rbac', logger=logger)
    def object_permissions(self, owner, object_type, **kwargs):
        """
        Method to get/set object permissions

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results
        """
        return self._perms(object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='rbac', logger=logger)
    def object_permissions_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Method to get/set object permissions on specific object

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of permissions processing
        """
        return self._perms_by_id(object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def bulk_crud(self, owner, object_type, **kwargs):
        """
        Routes CRUD operations on objects

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the REST method results
        """
        if self._rest_method == 'GET':
            return self._get_bulk(owner, object_type, **kwargs)
        elif self._rest_method in ['PUT', 'POST']:
            if isinstance(kwargs['data'], dict) and kwargs['data'].get('action') == 'fetch':
                return self._get_bulk(owner, object_type, **kwargs['data'])
            else:
                return self._create_or_update(owner, object_type, **kwargs)
        elif self._rest_method == 'DELETE':
            self._delete_bulk(owner, object_type, **kwargs)
        else:
            raise ITOAError(status="500", message="Unsupported HTTP method %s." % self._rest_method)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def crud_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Routes CRUD operations per object

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: string
        @param object_id: id of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of the REST method
        """
        if self._rest_method == 'GET':
            return self._get_by_id(owner, object_type, object_id, **kwargs)
        elif self._rest_method in ['PUT', 'POST']:
            return self._update_by_id(owner, object_type, object_id, **kwargs)
        elif self._rest_method == 'DELETE':
            return self._delete_by_id(owner, object_type, object_id, **kwargs)
        else:
            raise ITOAError(status="500", message="Unsupported HTTP method %s." % self._rest_method)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def user_preference_bulk_crud(self, owner, object_type, **kwargs):
        """
        Routes CRUD operations on objects

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the REST method results
        """
        if self._rest_method == 'GET':
            return self._get_bulk(owner, object_type, **kwargs)
        elif self._rest_method in ['PUT', 'POST']:
            if isinstance(kwargs['data'], dict) and kwargs['data'].get('action') == 'fetch':
                return self._get_bulk(owner, object_type, **kwargs['data'])
            else:
                # first delete existing user preferences
                self._user_preference_delete_bulk(owner, **kwargs)
                return self._create_or_update(owner, object_type, **kwargs)
        elif self._rest_method == 'DELETE':
            self._user_preference_delete_bulk(owner, **kwargs)
        else:
            raise ITOAError(status="500", message="Unsupported HTTP method %s." % self._rest_method)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def refresh_objects(self, owner, object_type, **kwargs):
        """
        Refreshes objects in bulk

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of refresh
        """
        return self._refresh_object(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def refresh_object_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Refreshes specific objects

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: string
        @param object_id: id of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of the refresh
        """
        return self._object_refresh_by_id(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='refresh_queue_job', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def refresh_queue_crud_by_id(self, owner, object_type, object_id, **kwargs):
        """
        CRUD for refresh queue job by ID

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: string
        @param object_id: id of ITOA object

        @rtype: json
        @return: json of the results of the refresh
        """
        if self._rest_method == 'DELETE':
            return self._delete_refresh_queue_job_by_id(owner, object_type, object_id, **kwargs)
        else:
            return self.crud_by_id(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='kpi', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def kpi_single_crud(self, owner, kpi_id, **kwargs):
        """
        CRUD for a single KPI by ID

        @type: string
        @param owner: owner making the request

        @type: string
        @param kpi_id: ID of KPI object

        @rtype: JSON
        @return: JSON object representing the KPI object inside a service
        """
        return self._kpi_single_crud(owner, kpi_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='kpi', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def kpi_bulk_crud(self, owner, object_type, **kwargs):
        """
        CRUD for bulk KPIs

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object (required for wrapper)

        @rtype: JSON
        @return: JSON object representing the KPI object inside a service
        """
        return self._kpi_bulk_crud(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='service', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def link_template_to_service(self, owner, object_type, object_id, **kwargs):
        """
        Get service template id from service /
        Link a single service to a service template

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: string
        @param object_id: id of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of the refresh
        """
        return self._link_template_to_service(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd(is_bulk_op=True)
    def get_objects_count(self, owner, object_type, **kwargs):
        """
        Gets count of objects with filters applied

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the count of objects
        """
        if object_type == 'entity':
            return self._get_entity_summary(owner, **kwargs)

        return self._get_object_count(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def templatize_object_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Templatizes given object

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: string
        @param object_id: id of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the templatized objects
        """
        return self._templatize_object_by_id(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def get_neighbors(self, owner, object_type, **kwargs):
        """
        Get related entity relationships for a given entity within given levels

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of the REST method
        """
        return self._get_neighbors(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def get_entity_data_drilldown_filter(self, owner, entity_id, **kwargs):
        """
        Get entity data drilldown filter for an entity that could be used to filter on raw data associated
        with the entity

        @type owner: str
        @param owner: user making the request

        @type entity_id: str
        @param entity_id: _key of the entity

        @type kwargs: dict
        @param kwargs: key word argument extracted from request

        @rtype: json
        @return: data filter in json format
        """
        return self._get_entity_data_drilldown_filter(owner, entity_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity_discovery_searches', logger=logger)
    def get_discovery_searches_per_entity(self, owner, entity_id, **kwargs):
        """
        Get discovery search details related to entity status for specific entity

        @type owner: str
        @param owner: user making the request

        @type entity_id: str
        @param entity_id: _key of the entity

        @type kwargs: dict
        @param kwargs: key word argument extracted from request

        @rtype: json
        @return: discovery search details in json format
        """
        return self._get_discovery_searches_per_entity(owner, entity_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity_discovery_searches', logger=logger)
    def fetch_discovery_search_details(self, owner, search_id, **kwargs):
        """
        Get discovery search details for specific search_id

        @type owner: str
        @param owner: user making the request

        @type search_id: str
        @param search_id: _key of the discovery search

        @type kwargs: dict
        @param kwargs: key word argument extracted from request

        @rtype: json
        @return: discovery search details in json format
        """
        return self._fetch_discovery_search_details(owner, search_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def get_entity_dashboard_drilldown_url_params(self, owner, entity_id, **kwargs):
        """
        Get entity dashboard drilldown url and params for an entity that could be used to create dashboards for
        the entity

        @type owner: str
        @param owner: user making the request

        @type entity_id: str
        @param entity_id: _key of the entity

        @type kwargs: dict
        @param kwargs: key word argument extracted from request

        @rtype: json
        @return: list of dashboard drilldown with base url and params
        """
        return self._get_entity_dashboard_drilldown_url_params(owner, entity_id, **kwargs)

    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def get_entity_dashboard_drilldown_bulk_url_params(self, owner, object_type, **kwargs):
        """
        Get entity dashboard drilldown url and params for an entity that could be used to create dashboards for
        the entity

        @type owner: str
        @param owner: user making the request

        @type object_type: str
        @param object_type: type of ITOA object, must be 'entity'

        @type kwargs: dict
        @param kwargs: key word argument extracted from request

        @rtype: json
        @return: list of dashboard drilldown with base url and params
        """
        return self._get_entity_dashboard_drilldown_bulk_url_params(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def get_dimensions_summary(self, owner, object_type, **kwargs):
        """
        Get identifier and informational dimensions for all the entities

        @type owner: str
        @param owner: user making the request


        @type kwargs: dict
        @param kwargs: key word argument extracted from request

        @rtype: json
        @return: list of all the dimensions
        """
        return self._get_dimensions_summary(owner, object_type, **kwargs)

    def get_rest_request_info(self, args, kwargs):
        """
        Invoked by access check (CheckUserAccess decorator) in SA-UserAccess
        to get splunkd request specific information

        @type: object
        @param self: the self reference

        @type: tuple
        @param args: args of the decorated REST handler function being processed

        @type: dict
        @param kwargs: kwargs of the decorated REST handler function being processed

        @rtype: tuple
        @return: tuple containing (user, session_key, object_type, operation, owner) for this request
        """
        owner = args[0] if len(args) > 0 else None
        object_type = args[1] if len(args) > 1 else None

        session_key = self._session_key
        user = self._current_user
        method = self._rest_method

        if method == 'GET':
            operation = 'read'
        elif method in ['POST', 'PUT']:
            operation = 'write'
        elif method == 'DELETE':
            operation = 'delete'
        else:
            message = 'Unsupported operation - {0}.'.format(method)
            raise Exception(message)

        return user, session_key, object_type, operation, owner

    def get_privatizeable_object_types(self):
        """
        Invoked by access check (CheckUserAccess decorator) in SA-UserAccess
        to get information about privatizeable object types

        @type: object
        @param self: the self reference

        @rtype: list of strings
        @return: names of object types
        """
        return get_privatizeable_object_types()

    def modify_mod_input(self, data_input, input_name, action, **kwargs):
        """
        Enables/Disables a given modular input.

        @type: str
        @param data_input: modular input name

        @type: str
        @param input_name: data input stanza name

        @type: str
        @param action: action to be performed (enable/disable)

        @type: dict
        @param kwargs: kwargs of the decorated REST handler function being processed

        @rtype: str
        @return: data
        """

        try:
            response = toggle_mod_input(self._session_key, 'SA-ITOA', data_input, input_name, action)
        except Exception as ex:
            logger.error('Failed to enable the modular input="%s"', data_input)
            raise ITOAError(status=500, message=str(ex))

        return json.dumps(response)

    def reload_mod_input(self, data_input, **kwargs):
        """
        reloads a given modular input.

        @type: str
        @param data_input: modular input name

        @type: dict
        @param kwargs: kwargs of the decorated REST handler function being processed

        @rtype: str
        @return: data
        """

        try:
            logger.info('Reloading the modular input="%s"', data_input)
            response = mod_input_reload(self._session_key, 'SA-ITOA', data_input)
        except Exception as ex:
            logger.error('Failed to reload the modular input="%s"', data_input)
            raise ITOAError(status=500, message=str(ex))

        return json.dumps(response)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def save_sandbox(self, owner, object_id, **kwargs):
        """
        PUT request that saves the sandbox along with creation, update, and deletion of sandbox services

        @type: string
        @param owner: Splunk user saving the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: transaction id of the new precheck
        """
        return self._save_sandbox(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def validate_sandbox(self, owner, object_id, **kwargs):
        """
        Validate that the sandbox services can be created without issue. This is a best-effort method.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._validate_sandbox(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def publish_sandbox(self, owner, object_id, **kwargs):
        """
        Publish sandbox services to actual services.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._publish_sandbox(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def synchronize_sandbox(self, owner, object_id, **kwargs):
        """
        Synchronize sandbox services for any template updates.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._synchronize_sandbox(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def sandbox_services_health(self, owner, object_id, **kwargs):
        """
        Synchronize sandbox services for any template updates.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._sandbox_services_health(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def sandbox_services_urgency(self, owner, object_id, **kwargs):
        """
        Synchronize sandbox services for any template updates.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._sandbox_services_urgency(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def publish_revert_sandbox(self, owner, object_id, **kwargs):
        """
        Reverts the published services back into sandbox.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._publish_revert_sandbox(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='sandbox', logger=logger)
    @NormalizeRESTRequestForSharedObjects
    @EnforceRBACSplunkd()
    def publish_reset_sandbox(self, owner, object_id, **kwargs):
        """
        Resets the sandbox from all published services.

        @type: string
        @param owner: Splunk user validating the sandbox

        @type: string
        @param object_id: Key of the object

        @rtype: json
        @return: Key response of the corresponding log
        """
        return self._publish_reset_sandbox(owner, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='entity', logger=logger)
    def clean_import_object_cache(self, owner, object_id):
        """
        Clear import object cache by search name
        """
        return self._clean_import_object_cache(owner, object_id)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='summarization_action', logger=logger)
    def summarization_action(self, owner, **kwargs):
        """
        Method to perform summarization tools actions

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the sandbox service tree
        """
        return self._summarization_action(owner, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='summarization_health', logger=logger)
    def summarization_health(self, owner, **kwargs):
        """
        Method to perform summarization tools actions

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the sandbox service tree
        """
        return self._summarization_health(owner, **kwargs)


class ItoaRestInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for ITOA interface endpoints.
    """

    # Names of APIs of the form:
    # /itoa_interface/load_csv/
    _simple_helper_api_names = [
        'load_csv',
        'generate_entity_filter',
        'get_kpi_searches',
        'get_kpi_searches_gt',
        'get_search_clause',
        'preview_merge',
        'get_alias_list',
        'get_backfill_search',
        'get_entity_filter',
        'get_dependent_kpis',
        'get_service_trees',
        'fetch_service_trees',
        'get_sandbox_service_trees',
        'get_linked_sandbox_services_for_template',
        'shift_time_offset',
        'get_drift_kpis',
        'kpi_entity_threshold_recommendations',
        'kpi_threshold_recommendations',
        'get_unique_service_tags',
        'summarization_action',
        'summarization_health'
    ]

    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(ItoaRestInterfaceSplunkd, self).__init__()

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        return self._default_handle(args)

    def _dispatch_to_provider(self, args):
        """
        Parses the REST path on the interface to help route to respective handlers
        This handler's think layer parses the paths and routes actual handling for the call
        to ItoaRestInterfaceProviderSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        """
        if not isinstance(args, dict):
            message = 'Invalid REST args received by ITOA interface - {}'.format(args)
            raise ItoaValidationError(message=message, logger=logger)

        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']

        rest_method_args = {}

        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)

        SplunkdRestInterfaceBase.extract_force_delete_header(args, rest_method_args)

        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))

        interface_provider = ItoaRestInterfaceProviderSplunkd(session_key, current_user, rest_method)

        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by ITOA interface - {}'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        # Double check this is ITOA interface path
        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'itoa_interface'):
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
        path_parts.pop(0)

        # Version check the API. It should be in the second part of URL if specified. Samples:
        # /itoa_interface/vLatest/... where vLatest implies latest ITSI version
        # /itoa_interface/<Latest ITSI version>/...
        # Currently only latest version of ITSI is supported for all APIs
        if len(path_parts) < 1:
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))

        if path_parts[0] in ['vLatest', 'v' + ITOAInterfaceUtils.get_app_version(session_key, app='itsi')]:
            path_parts.pop(0)

        if len(path_parts) < 1:
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))

        first_path_part = path_parts[0]

        # NOTE: Remove this check once entity AT functionality will complete.
        if first_path_part in ['kpi_entity_threshold', 'kpi_entity_threshold_recommendations'] and not (is_feature_enabled(
                'itsi-entity-level-adaptive-thresholding', session_key=session_key) and is_feature_enabled(
                'itsi-high-scale-at', session_key=session_key)):
            raise ITOAError(status=http.HTTPStatus.METHOD_NOT_ALLOWED,
                            message='High scale AT or Entity level AT feature is not enabled')
        # NOTE: Remove this check once high scale AT or entity AT functionality will complete.
        if first_path_part in ['kpi_at_info', 'at_incremental_values'] and not is_feature_enabled(
                'itsi-high-scale-at', session_key=session_key):
            raise ITOAError(status=http.HTTPStatus.METHOD_NOT_ALLOWED,
                            message='High scale AT feature is not enabled')
        # First check for helper methods which would occur as the first term in the path
        if first_path_part == 'get_supported_object_types' and len(path_parts) == 1:
            return interface_provider.get_supported_object_types()

        owner = self.extract_request_owner(args, rest_method_args)

        if first_path_part == 'entity_discovery_searches':
            if len(path_parts) == 2:
                entity_id = path_parts[1]
                return interface_provider.get_discovery_searches_per_entity(owner, entity_id, **rest_method_args)
            elif len(path_parts) == 3 and path_parts[1] == 'entity_id':
                entity_id = path_parts[2]
                return interface_provider.get_discovery_searches_per_entity(owner, entity_id, **rest_method_args)
            elif len(path_parts) == 3 and path_parts[1] == 'search_id':
                search_id = path_parts[2]
                return interface_provider.fetch_discovery_search_details(owner, search_id, **rest_method_args)
            elif len(path_parts) == 3 and path_parts[1] == 'import_objects_cache':
                import_objects_cache_id = path_parts[2]
                return interface_provider.clean_import_object_cache(owner, import_objects_cache_id)
            else:
                raise ITOAError(
                    status=http.HTTPStatus.BAD_REQUEST,
                    message='Specified REST url/path is not supported - {}.'.format(rest_path)
                )

        if first_path_part in self._simple_helper_api_names:
            if len(path_parts) == 2 and first_path_part == 'get_entity_filter' and path_parts[1] == 'count':
                rest_method_args['is_get_summary'] = True
            elif len(path_parts) != 1:
                raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
            if callable(getattr(interface_provider, first_path_part, None)):
                return operator.methodcaller(first_path_part, owner, **rest_method_args)(interface_provider)

        # Handle if this is a permissions path
        if first_path_part in get_interactable_object_types():
            if len(path_parts) == 2 and path_parts[1] == 'perms':
                return interface_provider.object_permissions(owner, first_path_part, **rest_method_args)
            elif len(path_parts) == 3 and path_parts[2] == 'perms':
                return interface_provider.object_permissions_by_id(
                    owner,
                    first_path_part,
                    path_parts[1],
                    **rest_method_args
                )

        # If no takers so far, it must be an object CRUD path
        if first_path_part in get_supported_itoa_object_types():
            object_type = first_path_part
            if len(path_parts) == 1:
                if object_type == 'kpi':
                    return interface_provider.kpi_bulk_crud(owner, object_type, **rest_method_args)
                elif object_type == 'user_preference':
                    return interface_provider.user_preference_bulk_crud(owner, object_type, **rest_method_args)
                else:
                    return interface_provider.bulk_crud(owner, object_type, **rest_method_args)
            elif len(path_parts) == 2:
                if path_parts[1] == 'refresh':
                    return interface_provider.refresh_objects(owner, object_type, **rest_method_args)
                elif path_parts[1] == 'count':
                    return interface_provider.get_objects_count(owner, object_type, **rest_method_args)
                elif path_parts[1] == 'bulk_update':
                    if object_type == 'kpi':
                        return interface_provider.kpi_bulk_crud(owner, object_type, bulk_update=True,
                                                                **rest_method_args)
                    else:
                        return interface_provider.bulk_update(owner, object_type, **rest_method_args)
                elif path_parts[1] == 'bulk_entities_update':
                    return interface_provider.bulk_entities_update(owner, object_type, **rest_method_args)
                elif path_parts[1] == 'get_neighbors':
                    return interface_provider.get_neighbors(owner, object_type, **rest_method_args)
                elif object_type == 'entity' and path_parts[1] == 'dimensions_summary':
                    return interface_provider.get_dimensions_summary(owner, object_type, **rest_method_args)
                elif object_type == 'entity' and path_parts[1] == 'retire':
                    return interface_provider.retire_entities(owner, object_type, **rest_method_args)
                elif object_type == 'entity' and path_parts[1] == 'restore':
                    return interface_provider.restore_entities(owner, object_type, **rest_method_args)
                elif object_type == 'entity' and path_parts[1] == 'count_retirable':
                    return interface_provider.count_retirable_entities(owner,
                                                                       object_type,
                                                                       **rest_method_args)
                elif object_type == 'entity' and path_parts[1] == 'retire_retirable':
                    return interface_provider.retire_retirable_entities(owner,
                                                                        object_type,
                                                                        **rest_method_args)
                elif object_type == 'entity' and path_parts[1] == 'bulk_delete_retired_entities':
                    return interface_provider.bulk_delete_retired_entities(owner,
                                                                           object_type,
                                                                           **rest_method_args)
                elif object_type == 'custom_threshold_windows' and path_parts[1] == 'linked_kpis':
                    return interface_provider.get_linked_kpis(owner, **rest_method_args)
                elif object_type == 'custom_threshold_windows' and path_parts[1] == 'bulk_stop':
                    return interface_provider.bulk_stop_active_ctws(owner, **rest_method_args)
                elif object_type == 'at_incremental_values':
                    return interface_provider.get_at_incremental_values(owner, path_parts[1], **rest_method_args)
                elif object_type == 'upgrade_readiness_prechecks' and path_parts[1] == 'failed_precheck':
                    return interface_provider.get_precheck_details(owner, "", **rest_method_args)
                elif object_type == 'upgrade_readiness_prechecks' and \
                        path_parts[1] == 'start_new_upgrade_readiness_precheck':
                    return interface_provider.start_new_upgrade_readiness_precheck()
                elif object_type == 'upgrade_readiness_prechecks' and path_parts[1] == 'auto_remediation':
                    return interface_provider.get_remediation_details(owner, "", **rest_method_args)
                elif object_type == 'refresh_queue_job':
                    object_id = path_parts[1]
                    return interface_provider.refresh_queue_crud_by_id(owner, object_type, object_id,
                                                                       **rest_method_args)
                elif object_type == 'kpi':
                    return interface_provider.kpi_single_crud(owner, path_parts[1], **rest_method_args)
                else:
                    # Path is for object CRUD by id
                    object_id = path_parts[1]
                    return interface_provider.crud_by_id(owner, object_type, object_id, **rest_method_args)
            elif len(path_parts) == 3:
                if path_parts[2] == 'refresh':
                    return interface_provider.refresh_object_by_id(owner, object_type, path_parts[1],
                                                                   **rest_method_args)
                elif path_parts[2] == 'templatize':
                    return interface_provider.templatize_object_by_id(owner, object_type, path_parts[1],
                                                                      **rest_method_args)
                elif path_parts[2] == 'base_service_template':
                    return interface_provider.link_template_to_service(owner, object_type, path_parts[1],
                                                                       **rest_method_args)
                elif object_type == 'entity' and path_parts[2] == 'data_drilldown':
                    entity_id = path_parts[1]
                    return interface_provider.get_entity_data_drilldown_filter(owner, entity_id, **rest_method_args)
                elif object_type == 'entity' and path_parts[2] == 'dashboard_drilldown':
                    entity_id = path_parts[1]
                    if entity_id == 'bulk':
                        return interface_provider.get_entity_dashboard_drilldown_bulk_url_params(
                            owner, 'entity', **rest_method_args
                        )
                    else:
                        return interface_provider.get_entity_dashboard_drilldown_url_params(owner, entity_id,
                                                                                            **rest_method_args)
                elif object_type == 'custom_threshold_windows' and path_parts[1] == 'ctws_by_kpi':
                    return interface_provider.get_ctws_by_kpi(owner, path_parts[2], **rest_method_args)
                elif object_type == 'custom_threshold_windows' and path_parts[2] == 'associate_service_kpi':
                    return interface_provider.associate_ctw_kpis(owner, path_parts[1], **rest_method_args)
                elif object_type == 'custom_threshold_windows' and path_parts[2] == 'disconnect_kpis':
                    return interface_provider.disconnect_kpis_from_ctw(owner, path_parts[1], **rest_method_args)
                elif object_type == 'custom_threshold_windows' and path_parts[2] == 'stop':
                    return interface_provider.stop_active_ctw(owner, path_parts[1], **rest_method_args)
                elif object_type == 'upgrade_readiness_prechecks' and path_parts[1] == 'failed_precheck':
                    return interface_provider.get_precheck_details(owner,
                                                                   path_parts[2],
                                                                   **rest_method_args)
                elif object_type == 'sandbox':
                    if path_parts[2] == 'save':
                        return interface_provider.save_sandbox(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'validate':
                        return interface_provider.validate_sandbox(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'publish':
                        return interface_provider.publish_sandbox(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'synchronize':
                        return interface_provider.synchronize_sandbox(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'health':
                        return interface_provider.sandbox_services_health(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'urgencies':
                        return interface_provider.sandbox_services_urgency(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'publish-revert':
                        return interface_provider.publish_revert_sandbox(owner, path_parts[1], **rest_method_args)
                    elif path_parts[2] == 'publish-reset':
                        return interface_provider.publish_reset_sandbox(owner, path_parts[1], **rest_method_args)
                elif object_type == 'upgrade_readiness_prechecks' and \
                        path_parts[1] == 'remediate_failed_precheck':
                    return interface_provider.remediate_failed_precheck(path_parts[2])
                elif object_type == 'upgrade_readiness_prechecks' and path_parts[1] == 'auto_remediation':
                    return interface_provider.get_remediation_details(owner,
                                                                      path_parts[2],
                                                                      **rest_method_args)

        if first_path_part == 'modular_inputs':
            if len(path_parts) == 4:
                mod_input = path_parts[1]
                input_name = path_parts[2]
                action = path_parts[3]
                return interface_provider.modify_mod_input(mod_input, input_name, action, **rest_method_args)
            elif len(path_parts) == 3:
                mod_input = path_parts[1]
                action = path_parts[2]
                if action == 'reload':
                    return interface_provider.reload_mod_input(mod_input, **rest_method_args)
                else:
                    raise ITOAError(
                        status=http.HTTPStatus.BAD_REQUEST,
                        message='Specified REST url/path is not supported - {}.'.format(rest_path)
                    )
            else:
                raise ITOAError(
                    status=http.HTTPStatus.BAD_REQUEST,
                    message='Specified REST url/path is not supported - {}.'.format(rest_path)
                )
        # No takers so far implies REST path is crazy, error out
        raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
