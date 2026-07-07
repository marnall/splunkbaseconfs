# ${copyright}
import json
import sys
import time
import uuid

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.util import normalizeBoolean

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))

import itsi_path
import itsi_py3

from SA_ITOA_app_common.solnlib.splunkenv import get_conf_stanza
from SA_ITOA_app_common.splunklib.results import ResultsReader

from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.setup_logging import InstrumentCall, getLogger
from command_itsi_import_objects import to_import_specification
from itsi.csv_import.itoa_bulk_import_sandbox_service import ServiceSandboxBulkImporter
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.objects.itsi_sandbox import ItsiSandbox
from itsi.objects.itsi_sandbox_service import ItsiSandboxService

from appdynamics_cp_objects import ItsiCpAppDynamicsTree, ItsiCpAppDynamicsRecord
from appdynamics_cp_constants import (
    APPD_SANDBOX_TITLE, APPD_CONTROLLER_NODE, APPD_APPLICATION_NODE, APPD_USER_EXPERIENCE_NODE, APPD_DUMMY_TYPE,
    APPD_APPLICATION_TEMPLATE, APPD_USER_EXPERIENCE_TEMPLATE,
)

logger = getLogger()


class RequestHandler:
    """
    Container for non-trivial `DA-ITSI-CP-appdynamics` request-specific logic
    """
    def __init__(self, user, session_key, transaction_id):
        self.user = user
        self.session_key = session_key
        self.transaction_id = transaction_id

    @InstrumentCall(logger)
    def fetch_tree(self, account_name):
        """
        Fetch a tree representing a draft hierarchy of APM Applications and End User Experiences services

        :param account_name: Account name to fetch controller credentials from
        :type account_name: str

        :return: Tree structure
        :rtype: str of ItsiCpAppDynamicsTree-like dict
        """
        # Fetch credentials
        try:
            stanza = get_conf_stanza("splunk_ta_appdynamics_account", account_name)
            controller = stanza.get("appd_controller_url")
        except KeyError:
            raise ITOAError(404, f"No account credential ({account_name}) in Splunk_TA_appdynamics was found.")

        service = ITOAInterfaceUtils.service_connection(self.session_key, "SA-ITOA")
        key = str(uuid.uuid4())
        app_service = APPD_APPLICATION_NODE.format(controller=controller)
        user_service = APPD_USER_EXPERIENCE_NODE.format(controller=controller)
        content = {
            "_key": key,
            "title": key,
            "potential_services": [
                {
                    "title": APPD_CONTROLLER_NODE.format(controller=controller),
                    "dependencies": [app_service, user_service],
                    "type": APPD_DUMMY_TYPE,
                },
                {
                    "title": app_service,
                    "dependencies": [],
                    "type": APPD_DUMMY_TYPE,
                },
                {
                    "title": user_service,
                    "dependencies": [],
                    "type": APPD_DUMMY_TYPE,
                },
            ],
            "existing_services": [],
            "controller": controller,
            "mod_source": "DA-ITSI-CP-appdynamics",
        }

        # Update with existing data
        sandbox_interface = ItsiSandbox(self.session_key, self.user)
        sandboxes = sandbox_interface.get_bulk("nobody", filter_data={
            "title": APPD_SANDBOX_TITLE.format(controller=controller),
        })
        if sandboxes:
            sandbox_id = sandboxes[0]["_key"]
            sandbox_service_interface = ItsiSandboxService(self.session_key, self.user)
            services = sandbox_service_interface.get_bulk("nobody", filter_data={"sandbox_id": sandbox_id})
            content["existing_services"] = [{
                "title": service["title"],
            } for service in services]

        # Collect data (Applications)
        app_search = f"""
        search `itsi_cp_appdynamics_index` source="application_status" sourcetype="appdynamics_status"
                controller_url="{controller}"
            | dedup application_id
            | table application_id, application_name
        """
        app_results = service.jobs.oneshot(app_search, **{
            "earliest_time": "-24h",
            "latest_time": "now",
        })
        app_reader = ResultsReader(app_results)
        for result in app_reader:
            content["potential_services"].append({
                "title": result["application_name"],
                "dependencies": [],
                "tags": {
                    "id": result["application_id"],
                },
                "type": APPD_APPLICATION_TEMPLATE,
            })
            content["potential_services"][1]["dependencies"].append(result["application_name"])
        else:
            logger.warning("No AppDynamics Application results found")

        # Collect data (End User Experiences)
        user_exp_search = f"""
        search `itsi_cp_appdynamics_index` source="dem_web" sourcetype="appdynamics_status"
                controller_url="{controller}"
            | dedup id
            | table id, name
        """
        user_results = service.jobs.oneshot(user_exp_search, **{
            "earliest_time": "-24h",
            "latest_time": "now",
        })
        user_reader = ResultsReader(user_results)
        for result in user_reader:
            content["potential_services"].append({
                "title": result["name"],
                "dependencies": [],
                "tags": {
                    "id": result["id"],
                },
                "type": APPD_USER_EXPERIENCE_TEMPLATE,
            })
            content["potential_services"][2]["dependencies"].append(result["name"])
        else:
            logger.warning("No AppDynamics End User Experience results found")

        # Create object and return
        tree_interface = ItsiCpAppDynamicsTree(self.session_key, self.user)
        tree_interface.create(self.user, content)
        return json.dumps(content)

    @InstrumentCall(logger)
    def publish_tree(self, key, publish_as_enabled, service_titles_to_publish=[]):
        """
        Publish a tree representing a draft hierarchy of APM Applications and End User Experiences services

        * Tree is deleted upon publish.
        * The organizational services for controller and service type are always created.

        :param key: Key of a ItsiCpAppDynamicsTree object
        :type key: str

        :param publish_as_enabled: Publish services as enabled?
        :type publish_as_enabled: Boolean

        :param service_titles_to_publish: List of services (as titles) to publish (empty implies all)
        :type service_titles_to_publish: list of str

        :return: Summary of publish
        :rtype: str of dict
        """
        # Fetch object
        tree_interface = ItsiCpAppDynamicsTree(self.session_key, self.user)
        appd_tree = tree_interface.get(self.user, key)
        if appd_tree is None:
            raise ITOAError(404, f"Tree {key} not found")
        controller = appd_tree["controller"]

        # Fetch or create sandbox
        sandbox_interface = ItsiSandbox(self.session_key, self.user)
        title = APPD_SANDBOX_TITLE.format(controller=controller)
        sandboxes = sandbox_interface.get_bulk("nobody", filter_data={
            "title": title,
        })
        if not sandboxes:
            response = sandbox_interface.create("nobody", {
                "title": title,
                "description":
                    f"Splunk AppDynamics sandbox for {controller}, created by the Content Pack for AppDynamics",
            })
            sandbox_key = response["_key"]
        else:
            sandbox_key = sandboxes[0]["_key"]

        # See SA-ITOA/lib/itsi/csv_import/itoa_bulk_import_specification.py for spec
        spec = {
            "service_sandbox": sandbox_key,
            "sandbox_service": {
                "backfillEnabled": "0",
                "criticality": "",
                "descriptionColumns": [],
                "serviceEnabled": "1" if publish_as_enabled else "0",
                "serviceSecurityGroup": "default_itsi_security_group",
                "serviceTemplate": "type",
                "titleField": "title",
                "service_sandbox": sandbox_key,
            },
            "service_dependents": ["dependencies"],
            "service_rel": [],
            "template": {
                APPD_APPLICATION_TEMPLATE: {
                    "entity_rules": [
                        {
                            "rule_condition": "AND",
                            "rule_items": [
                                {
                                    "field": "appd_application_id",
                                    "field_type": "alias",
                                    "rule_type": "matchesblank",
                                    "value": "id",
                                },
                                {
                                    "field": "appd_controller_url",
                                    "field_type": "info",
                                    "rule_type": "matchesblank",
                                    "value": "controller",
                                },
                            ],
                        },
                    ],
                },
                APPD_USER_EXPERIENCE_TEMPLATE: {
                    "entity_rules": [
                        {
                            "rule_condition": "AND",
                            "rule_items": [
                                {
                                    "field": "appd_application_id",
                                    "field_type": "alias",
                                    "rule_type": "matchesblank",
                                    "value": "id",
                                },
                            ],
                        },
                        {"rule_condition": "AND",
                         "rule_items": [
                             {
                                 "field": "appd_application_id",
                                 "field_type": "info",
                                 "rule_type": "matchesblank",
                                 "value": "id",
                             },
                         ],
                         },
                    ],
                },
            },
            # Unclear why it's in both forms
            "selectedServices": [],
            "selected_services": None,
            "updateType": "upsert",
            "update_type": "upsert",
        }

        app_service = APPD_APPLICATION_NODE.format(controller=controller)
        user_service = APPD_USER_EXPERIENCE_NODE.format(controller=controller)
        service_titles_set = {controller}
        if service_titles_to_publish:
            service_titles_set = service_titles_set.union(set(service_titles_to_publish))
        else:
            service_titles_set = service_titles_set.union({service["title"] for service in
                                                           appd_tree["potential_services"]})
        services_to_publish = []
        application_dependencies = []
        user_experience_dependencies = []
        for service in appd_tree["potential_services"]:
            service_title = service["title"]
            if service_title in service_titles_set:
                services_to_publish.append(service)
                if service.get("type") == APPD_APPLICATION_TEMPLATE:
                    application_dependencies.append(service_title)
                    service_titles_set.add(app_service)
                elif service.get("type") == APPD_USER_EXPERIENCE_TEMPLATE:
                    user_experience_dependencies.append(service_title)
                    service_titles_set.add(user_service)

        # Add organizational services
        services_to_publish.append({
            "title": APPD_CONTROLLER_NODE.format(controller=controller),
            "dependencies": [app_service, user_service],
        })
        if application_dependencies:
            services_to_publish.append({
                "title": app_service,
                "dependencies": application_dependencies,
            })
        if user_experience_dependencies:
            services_to_publish.append({
                "title": user_service,
                "dependencies": user_experience_dependencies,
            })

        # Reshape object into bulk-importable format and import
        bulk_importer = ServiceSandboxBulkImporter(to_import_specification(spec), self.session_key, self.user, "nobody")
        csvlike = [["title", "dependencies", "id", "type", "controller"]]
        for service in services_to_publish:
            row = [
                service["title"],
                "",
                service.get("tags", {}).get("id", ""),
                service.get("type", ""),
                controller,
            ]
            for dependency_title in service["dependencies"]:
                if dependency_title in service_titles_set:
                    dependency_row = list(row)
                    dependency_row[1] = dependency_title
                    csvlike.append(dependency_row)
            else:
                csvlike.append(row)

        bulk_import_response = bulk_importer.bulk_import(csvlike, transaction_id=self.transaction_id)

        # Cleanup
        errors = []
        if not bulk_import_response.get("services"):
            error_str = "Bulk import of services failed"
            logger.error(error_str)
            errors.append(error_str)
            record_key = None
        else:
            tree_interface.delete(self.user, key)
            record_interface = ItsiCpAppDynamicsRecord(self.session_key, self.user)
            existing_records = record_interface.get_bulk("nobody", filter_data={
                "controller": controller,
            })
            record_data = {
                "sandbox_id": sandbox_key,
                "controller": controller,
                "title": f"Splunk AppDynamics Record - {controller}",
                "publish_time": int(time.time()),
            }
            if not existing_records:
                response = record_interface.create("nobody", record_data)
                record_key = response["_key"]
            else:
                record_key = existing_records[0]["_key"]
                record_interface.update("nobody", record_key, record_data)
        return json.dumps({
            "sandbox_id": sandbox_key,
            "record_id": record_key,
            "errors": errors,
            "services_created": bulk_import_response.get("services"),
        })

    @InstrumentCall(logger)
    def post_object(self, object_class, rest_args, key=None):
        data = rest_args.get("data")
        if not data:
            raise ITOAError(status=400, message="No data provided")
        data_key = key or data.get("_key")
        object_interface = object_class(self.session_key, self.user)
        if data_key:
            # Disambiguate create vs update
            is_create = True
            if object_interface.get("nobody", data_key):
                is_create = False
            if is_create:
                rv = object_interface.create("nobody", data)
            else:
                is_partial_data = normalizeBoolean(rest_args.get("is_partial_data"))
                rv = object_interface.update("nobody", data_key, data, is_partial_data=is_partial_data)
        else:
            # No key means it must be an update
            rv = object_interface.create("nobody", data)
        return json.dumps(rv)

    @InstrumentCall(logger)
    def get_object(self, object_class, key):
        object_interface = object_class(self.session_key, self.user)
        obj = object_interface.get("nobody", key)
        if obj:
            return json.dumps(obj)
        raise ITOAError(status=404, message=f"{object_class.object_type} {key} not found")

    @InstrumentCall(logger)
    def get_object_bulk(self, object_class, rest_args):
        sort_key = rest_args.get("sort_key")
        sort_dir = rest_args.get("sort_dir")
        filter = rest_args.get("filter")
        if filter:
            filter = json.loads(filter)
        offset = rest_args.get("offset")
        if offset:
            offset = int(offset)
        limit = rest_args.get("limit")
        if limit:
            limit = int(limit)
        fields = rest_args.get("fields")
        if fields:
            fields = fields.split(",")
        object_interface = object_class(self.session_key, self.user)
        return json.dumps(object_interface.get_bulk("nobody", sort_key=sort_key, sort_dir=sort_dir, filter_data=filter,
                                                    fields=fields, skip=offset, limit=limit))

    @InstrumentCall(logger)
    def delete_object(self, object_class, key):
        object_interface = object_class(self.session_key, self.user)
        return json.dumps(object_interface.delete("nobody", key))

    @InstrumentCall(logger)
    def delete_object_bulk(self, object_class, rest_args):
        filter = rest_args.get("filter")
        if filter:
            filter = json.loads(filter)
        object_interface = object_class(self.session_key, self.user)
        return json.dumps(object_interface.delete_bulk("nobody", filter_data=filter))


class ItsiCpAppDynamicsRestInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for `DA-ITSI-CP-appdynamics` endpoints.
    """

    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(ItsiCpAppDynamicsRestInterfaceSplunkd, self).__init__()

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

        @rtype: str
        @return: results of the REST method
        """
        if not isinstance(args, dict):
            message = "Invalid REST args received by ITOA interface - {}".format(args)
            raise ItoaValidationError(message=message, logger=logger)

        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, "query", rest_method_args)
        SplunkdRestInterfaceBase.extract_force_delete_header(args, rest_method_args)
        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))

        rest_path = args["rest_path"]
        if not isinstance(rest_path, itsi_py3.string_type):
            message = "Invalid REST path received by ITOA interface - {}".format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        session_key = args["session"]["authtoken"]
        user = self.extract_request_owner(args, rest_method_args)
        rest_method = args['method']
        request_handler = RequestHandler(user, session_key, str(uuid.uuid4()))
        path_parts = rest_path.strip().strip("/").split("/")
        if path_parts[0] == "discovery":
            if path_parts[1] == "tree":
                object_class = ItsiCpAppDynamicsTree
            elif path_parts[1] == "record":
                object_class = ItsiCpAppDynamicsRecord
            # Not basic CRUD
            elif path_parts[1] in ["fetch_tree", "publish_tree"]:
                object_class = None
            else:
                raise ITOAError(status=404, message="Object type {} not found".format(path_parts[1]))

            if rest_method == "POST":
                # Basic CRUD
                if object_class:
                    if len(path_parts) == 2:
                        return request_handler.post_object(object_class, rest_method_args)
                    elif len(path_parts) == 3:
                        return request_handler.post_object(object_class, rest_method_args, key=path_parts[2])

                # Other functions
                if len(path_parts) == 2 and path_parts[1] == "fetch_tree":
                    account = rest_method_args.get("account")
                    if not account:
                        raise ITOAError(400, "Missing `account` query parameter")
                    return request_handler.fetch_tree(account)
                if len(path_parts) == 3 and path_parts[1] == "publish_tree":
                    publish_as_enabled = rest_method_args.get("publish_as_enabled", False)
                    selected_services = []
                    selected_services_str = rest_method_args.get("selected_services")
                    SplunkdRestInterfaceBase.extract_rest_args(args, "selected_services", rest_method_args)
                    if selected_services_str:
                        selected_services = json.loads(selected_services_str)
                    return request_handler.publish_tree(path_parts[2], publish_as_enabled,
                                                        service_titles_to_publish=selected_services)
            elif rest_method == "GET":
                # Basic CRUD
                if object_class:
                    if len(path_parts) == 2:
                        return request_handler.get_object_bulk(object_class, rest_method_args)
                    elif len(path_parts) == 3:
                        return request_handler.get_object(object_class, path_parts[2])
            elif rest_method == "DELETE":
                # Basic CRUD
                if object_class:
                    if len(path_parts) == 2:
                        return request_handler.delete_object_bulk(object_class, rest_method_args)
                    elif len(path_parts) == 3:
                        return request_handler.delete_object(object_class, path_parts[2])
        raise ITOAError(status=404, message="Specified REST URL/path is invalid - {}.".format(rest_path))
