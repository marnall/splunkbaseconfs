# ${copyright}
"""
Generic REST interface for Service Import workflow
"""
import json
import sys
import uuid

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.util import normalizeBoolean
import splunk.rest as rest

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))

from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.setup_logging import InstrumentCall, getLogger
from itsi.itsi_utils import ITOAInterfaceUtils
from SA_ITOA_app_common.splunklib.results import ResultsReader

logger = getLogger()

# Default lookback period for fetching services when not specified in conf
DEFAULT_FETCH_SERVICES_LOOKBACK = "-7d"


class RequestHandler:
    """
    Container for generic service import request-specific logic
    """

    def __init__(self, user, session_key, transaction_id):
        self.user = user
        self.session_key = session_key
        self.transaction_id = transaction_id

    @InstrumentCall(logger)
    def _fetch_module_entries(self):
        """
        Fetch every stanza from itsi_service_import_flow_data.conf.
        Returns the raw `entry` array from Splunkd.
        """
        conf_url = (
            rest.makeSplunkdUri()
            + "servicesNS/nobody/DA-ITSI-ContentLibrary/configs/"
            "conf-itsi_service_import_flow_data"
        )
        args = {"output_mode": "json"}
        response, content = rest.simpleRequest(
            conf_url,
            method="GET",
            getargs=args,
            sessionKey=self.session_key,
            raiseAllErrors=False,
        )

        status = int(response.get("status", 0))
        if status == 404:
            raise ITOAError(
                404,
                "Service import configuration not found",
            )
        if status != 200:
            raise ITOAError(
                500, f"Failed to fetch configuration: {status}"
            )

        payload = json.loads(content.decode("utf-8"))
        return payload.get("entry", [])

    @InstrumentCall(logger)
    def get_modules(self):
        """
        Get all available service import modules from itsi_service_import_flow_data.conf
        """
        logger.info("Fetching all service import modules from conf")

        try:
            results = self._fetch_module_entries()
            modules = []
            for item in results:
                stanza_name = item.get('name')
                if stanza_name:
                    logger.info(f"Processing stanza: {stanza_name}")
                    content_data = item.get('content', {})

                    # Get the content pack name for placeholder replacement
                    cp_name = content_data.get('name', stanza_name)

                    icon_src = (f"/static/{content_data['icon']}"
                                if content_data.get('icon')
                                else "/static/icons/onboarding.png")
                    dependencies_raw = content_data.get(
                        'dependencies_for_service_import', ''
                    )
                    try:
                        dependencies = json.loads(dependencies_raw or "{}")
                    except json.JSONDecodeError:
                        logger.error(
                            "Invalid dependencies JSON for module '%s'",
                            stanza_name,
                        )
                        dependencies = {}

                    module_data = {
                        'id': stanza_name,
                        'name': cp_name,
                        'title': cp_name,
                        'appname': content_data.get('appname', ''),
                        'itsiappname': content_data.get('itsiappname', ''),
                        'iconSrc': icon_src,
                        'description': content_data.get('description', ''),
                        'dependenciesForServiceImport': dependencies,
                    }

                    modules.append(module_data)
                    logger.info(f"Successfully processed module: {stanza_name}")

            logger.info(f"Found {len(modules)} service import modules")
            return json.dumps({
                'modules': modules
            })

        except Exception as e:
            logger.error(f"Error fetching modules: {e}")
            raise ITOAError(500, f"Failed to get modules: {str(e)}")

    @InstrumentCall(logger)
    def get_module_filters(self, module_id):
        logger.info(
            "Fetching service import filters for '%s'", module_id
        )
        entries = self._fetch_module_entries()

        content_data = None
        for entry in entries:
            if entry.get("name") == module_id:
                content_data = entry.get("content", {})
                break

        if content_data is None:
            raise ITOAError(404, f"Module '{module_id}' not found")

        # Get fetch_services_lookback from conf
        fetch_services_lookback = content_data.get(
            "fetch_services_lookback", DEFAULT_FETCH_SERVICES_LOOKBACK
        ).strip()

        try:
            filters_dict = json.loads(content_data.get("filters") or "{}")
        except json.JSONDecodeError as exc:
            logger.error(
                "Invalid JSON for filters in module '%s': %s", module_id, exc
            )
            raise ITOAError(
                500,
                "Module configuration contains invalid JSON in 'filters'",
            )

        filters_response = []
        service = None

        for filter_name, filter_conf in filters_dict.items():
            filter_conf = filter_conf or {}
            spl = filter_conf.get("SPL", "").strip()
            values = []

            if spl:
                if service is None:
                    service = ITOAInterfaceUtils.service_connection(
                        self.session_key, "SA-ITOA"
                    )

                try:
                    results = service.jobs.oneshot(
                        spl,
                        earliest_time=fetch_services_lookback,
                        latest_time="now",
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to execute SPL for filter '%s': %s",
                        filter_name,
                        exc,
                    )
                    raise ITOAError(
                        500,
                        f"Failed to execute SPL for filter '{filter_name}'",
                    )

                # Get field names for value and label
                # If SPL returns 2 columns, treat as (value, label)
                # If SPL returns 1 column, use it as both value and label
                value_field = filter_conf.get("value_field")
                label_field = filter_conf.get("label_field")

                seen = set()
                for row in ResultsReader(results):
                    if not isinstance(row, dict):
                        continue

                    row_fields = [k for k, v in row.items()
                                  if v not in (None, "", [])]

                    if not row_fields:
                        continue

                    # Determine value and label
                    if value_field and label_field:
                        # Explicitly configured fields
                        value = row.get(value_field)
                        label = row.get(label_field)
                    elif len(row_fields) >= 2:
                        # Two columns: first is value, second is label
                        value = row.get(row_fields[0])
                        label = row.get(row_fields[1])
                    elif len(row_fields) == 1:
                        # Single column: use as both value and label
                        value = row.get(row_fields[0])
                        label = value
                    else:
                        continue

                    if value in (None, "", []):
                        continue

                    value_str = str(value)
                    if value_str in seen:
                        continue
                    seen.add(value_str)

                    label_str = (str(label) if label not in (None, "", [])
                                 else value_str)
                    values.append({
                        "value": value_str,
                        "label": label_str
                    })

            filters_response.append(
                {
                    "name": filter_conf.get("name", filter_name),
                    "label": filter_conf.get("label", filter_name),
                    "placeholder": filter_conf.get("placeholder", ""),
                    "options": values,
                }
            )

        response_payload = {
            "moduleId": module_id,
            "filters": filters_response,
        }
        return json.dumps(response_payload)

    @InstrumentCall(logger)
    def fetch_services(self, module_id, filter_values):
        """
        Fetch services for a given module using the fetch_services_spl from conf.
        Substitutes filter placeholders and executes SPL to discover services.

        :param module_id: The module identifier (e.g., 'catalyst_center', 'meraki')
        :type module_id: str

        :param filter_values: Dictionary of filter names and their selected values
        :type filter_values: dict

        :return: JSON string containing services
        :rtype: str
        """
        logger.info(
            "Fetching services for module '%s' with filters: %s",
            module_id,
            filter_values
        )

        # Fetch module configuration
        entries = self._fetch_module_entries()
        content_data = None
        for entry in entries:
            if entry.get("name") == module_id:
                content_data = entry.get("content", {})
                break

        if content_data is None:
            raise ITOAError(404, f"Module '{module_id}' not found")

        # Get fetch_services_spl from conf
        fetch_services_spl = content_data.get("fetch_services_spl", "").strip()
        if not fetch_services_spl:
            raise ITOAError(
                400,
                f"Module '{module_id}' does not have a 'fetch_services_spl' configured"
            )

        # Get fetch_services_lookback from conf
        fetch_services_lookback = content_data.get(
            "fetch_services_lookback", DEFAULT_FETCH_SERVICES_LOOKBACK
        ).strip()

        # Substitute placeholders with filter values
        # Placeholders are in the format {filter_name}
        substituted_spl = fetch_services_spl
        for filter_name, filter_value in filter_values.items():
            placeholder = "{" + filter_name + "}"
            if placeholder in substituted_spl:
                substituted_spl = substituted_spl.replace(placeholder, filter_value)
                logger.info(
                    "Substituted placeholder '%s' with value '%s'",
                    placeholder,
                    filter_value
                )

        logger.info("Executing SPL for service discovery: %s", substituted_spl)

        # Execute SPL query
        service = ITOAInterfaceUtils.service_connection(
            self.session_key, "SA-ITOA"
        )
        try:
            results = service.jobs.oneshot(
                substituted_spl,
                earliest_time=fetch_services_lookback,
                latest_time="now"
            )
        except Exception as exc:
            logger.error(
                "Failed to execute fetch_services_spl for module '%s': %s",
                module_id,
                exc
            )
            raise ITOAError(
                500,
                f"Failed to execute service discovery query: {str(exc)}"
            )

        # Parse results and build service list
        service_map = {}

        for row in ResultsReader(results):
            if not isinstance(row, dict):
                continue

            logger.debug("SPL row result: %s", row)

            # Extract standard fields
            service_title = row.get("service_title")
            service_dependency = row.get("service_dependency", "")
            service_template = row.get("service_template", "")

            if not service_title:
                logger.warning("Skipping row without service_title: %s", row)
                continue

            # Build tags from all other fields (excluding standard fields)
            tags = {}
            for key, value in row.items():
                if key not in ["service_title", "service_dependency", "service_template"]:
                    if value not in (None, []):
                        tags[key] = value

            # Determine type field (service_template or N/A)
            service_type = service_template if service_template else "N/A"

            # Check if service already exists in map
            if service_title in service_map:
                if service_dependency and service_dependency not in service_map[service_title]["dependencies"]:
                    service_map[service_title]["dependencies"].append(service_dependency)
            else:
                # Create new service entry
                service_map[service_title] = {
                    "id": service_title,
                    "title": service_title,
                    "dependencies": [service_dependency] if service_dependency else [],
                    "type": service_type,
                    "tags": tags
                }

        services = list(service_map.values())

        logger.info(
            "Successfully fetched %d services for module '%s'",
            len(services),
            module_id
        )

        response = {
            "_key": str(uuid.uuid4()),
            "title": f"{module_id}_services",
            "services": services,
            "module_id": module_id,
            "filters": filter_values,
            "fetch_services_spl": substituted_spl,
            "fetch_services_lookback": fetch_services_lookback
        }

        return json.dumps(response)


class ServiceImportRestInterface(PersistentServerConnectionApplication):
    """
    Generic REST interface for service import workflow
    """

    def __init__(self, command_line, command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, args):
        """
        Blanket handler for REST calls, routing GET/POST/PUT/DELETE requests on the interface.
        """
        try:
            args = json.loads(args)
            result = self._dispatch_to_provider(args)
            return {
                'payload': result,
                'status': 200
            }
        except ITOAError as e:
            logger.error(f"ITOAError in service import REST interface: {e}")
            return {
                'payload': {'message': str(e)},
                'status': getattr(e, 'status', 500)
            }
        except Exception as e:
            logger.exception(f"Unexpected error in service import REST interface: {e}")
            return {
                'payload': {'exception': str(e)},
                'status': 500
            }

    def _dispatch_to_provider(self, args):
        """
        Route requests to appropriate handler methods
        """
        if not isinstance(args, dict):
            message = ("Invalid REST args received by generic service "
                       "import interface - {}").format(args)
            raise ItoaValidationError(message=message, logger=logger)

        rest_path = args.get("rest_path", "")
        if not isinstance(rest_path, str):
            message = ("Invalid REST path received by generic service "
                       "import interface - {}").format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        session_key = args["session"]["authtoken"]
        user = args.get("session", {}).get("user", "nobody")
        rest_method = args['method']
        request_handler = RequestHandler(user, session_key, str(uuid.uuid4()))

        logger.info(
            f"Generic service import REST call: "
            f"method={rest_method}, path={rest_path}")

        path_parts = rest_path.strip().strip("/").split("/")

        if len(path_parts) >= 2 and path_parts[0] == "content_library":

            if rest_method == "GET":
                # GET /content_library/service-import/modules
                if (
                    len(path_parts) == 3
                    and path_parts[1] == "service-import"
                    and path_parts[2] == "modules"
                ):
                    return request_handler.get_modules()
                # GET /content_library/service-import/filters/{module_id}
                if (
                    len(path_parts) == 4
                    and path_parts[1] == "service-import"
                    and path_parts[2] == "filters"
                ):
                    module_id = path_parts[3]
                    return request_handler.get_module_filters(module_id)

            elif rest_method == "POST":
                # POST /content_library/service-import/services
                if (
                    len(path_parts) == 3
                    and path_parts[1] == "service-import"
                    and path_parts[2] == "services"
                ):
                    # Extract request body
                    payload = args.get("payload", "")
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                        except json.JSONDecodeError:
                            raise ITOAError(400, "Invalid JSON in request body")

                    module_id = payload.get("module_id")
                    filter_values = payload.get("filters", {})

                    if not module_id:
                        raise ITOAError(400, "Missing 'module_id' in request body")

                    return request_handler.fetch_services(module_id, filter_values)

        raise ITOAError(
            status=404,
            message="Specified REST URL/path is invalid - {}.".format(rest_path))
