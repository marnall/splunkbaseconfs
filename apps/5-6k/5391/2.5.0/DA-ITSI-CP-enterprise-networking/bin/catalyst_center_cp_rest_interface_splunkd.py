# ${copyright}
"""
REST interface for Cisco Enterprise Networks service import flow
"""
import json
import sys
import time
import uuid

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.util import normalizeBoolean

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "bin"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))

import itsi_py3

from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.setup_logging import InstrumentCall, getLogger
from SA_ITOA_app_common.solnlib.splunkenv import get_conf_stanza
from SA_ITOA_app_common.splunklib.results import ResultsReader
from command_itsi_import_objects import to_import_specification
from itsi.csv_import.itoa_bulk_import_sandbox_service import ServiceSandboxBulkImporter
from itsi.itsi_utils import ITOAInterfaceUtils
from itsi.objects.itsi_sandbox import ItsiSandbox
from itsi.objects.itsi_sandbox_service import ItsiSandboxService
from itsi.objects.itsi_service_template import ItsiBaseServiceTemplate
from catalyst_center_cp_constants import (
    CATALYST_CENTER_SANDBOX_TITLE,
    CATALYST_CENTER_SITE_TEMPLATE,
    CATALYST_CENTER_SITE_TEMPLATE_ID,
    CATALYST_CENTER_SPL,
    MERAKI_NETWORK_TEMPLATE,
    MERAKI_NETWORK_TEMPLATE_ID,
    MERAKI_NETWORK_SPL,
    MERAKI_ORGANIZATION_SPL,
)
from catalyst_center_cp_objects import ItsiCpCatalystCenterTree, ItsiCpCatalystCenterRecord
from catalyst_center_cp_utils import build_catalyst_import
from meraki_cp_objects import ItsiCpMerakiTree, ItsiCpMerakiRecord

logger = getLogger()


class RequestHandler:
    """
    Container for non-trivial `DA-ITSI-CP-CatalystCenter` request-specific logic
    """

    def __init__(self, user, session_key, transaction_id):
        self.user = user
        self.session_key = session_key
        self.transaction_id = transaction_id

    def get_template_name_by_id(self, template_id: str) -> str:
        """Get the actual template name by loading template by its stable ID"""
        try:
            template_interface = ItsiBaseServiceTemplate(self.session_key, self.user)
            template = template_interface.get("nobody", template_id)
            if template:
                template_title = template.get('title', 'Unknown')
                logger.info(f"Resolved template ID '{template_id}' to name '{template_title}'")
                return template_title
            else:
                logger.error(f"Template with ID '{template_id}' not found")
                return None
        except Exception as e:
            logger.error(f"Failed to fetch template by ID '{template_id}': {e}")
            return None

    @InstrumentCall(logger)
    def fetch_tree(self, catalyst_account_name):
        """
        Fetch a tree representing a Catalyst Center controller

        :param catalyst_account_name: Name of Catalyst Account to import services
        :type catalyst_account_name: str

        :return: Tree structure
        :rtype: str of ItsiCpCatalystCenterTree-like dict
        """
        logger.info("Fetching tree for catalyst center account_name=%s", catalyst_account_name)

        # load catalyst account stanza to extract controller url (cisco_catalyst_host)
        try:
            stanza = get_conf_stanza("ta_cisco_catalyst_account", catalyst_account_name)
            cisco_dnac_host = stanza.get("cisco_dna_center_host")
        except KeyError as exc:
            raise ITOAError(
                404,
                f"No account credential ({catalyst_account_name}) in TA_cisco_catalyst was found."
            ) from exc

        key = str(uuid.uuid4())
        content = {
            "_key": key,
            "title": key,
            "potential_services": [],
            "existing_services": [],
            "account_name": catalyst_account_name,
            "controller": cisco_dnac_host,
            "mod_source": "DA-ITSI-CP-enterprise-networking",
        }

        sandbox_interface = ItsiSandbox(self.session_key, self.user)
        sandboxes = sandbox_interface.get_bulk(
            "nobody",
            filter_data={
                "title": CATALYST_CENTER_SANDBOX_TITLE.format(account_name=catalyst_account_name)
            }
        )

        if sandboxes:
            # Add existing services to tree content
            sandbox_id = sandboxes[0]["_key"]
            sandbox_service_interface = ItsiSandboxService(self.session_key, self.user)
            services = sandbox_service_interface.get_bulk(
                "nobody",
                filter_data={"sandbox_id": sandbox_id}
            )
            content["existing_services"] = [{"title": service["title"]} for service in services]

        # Run SPL to fetch Catalyst Center sites
        service = ITOAInterfaceUtils.service_connection(self.session_key, "SA-ITOA")
        search_spl = CATALYST_CENTER_SPL.format(cisco_catalyst_host=cisco_dnac_host)
        results = service.jobs.oneshot(search_spl, earliest_time="-30d", latest_time="now")
        reader = ResultsReader(results)

        sites_dict = {}
        for row in reader:
            logger.debug(f"[fetch_tree] SPL row: {row}")
            site_id = row.get("siteId")
            if not site_id:
                continue
            site_name = row.get("siteName", "")
            if site_name == "Global":
                site_name = f"Catalyst Center Host ({cisco_dnac_host})"
            sites_dict[site_id] = {
                "siteName": site_name,
                "siteHierarchy": row.get("siteHierarchy", ""),
                "siteType": row.get("siteType", "").lower(),
                "parentSiteId": row.get("parentId", ""),
                "dependencies": [],  # Build dependencies below
            }

        # Populate dependencies: parent → child
        for site_id, data in sites_dict.items():
            parent_id = data.get("parentSiteId")
            if parent_id and parent_id in sites_dict:
                sites_dict[parent_id].setdefault("dependencies", []).append(site_id)
                logger.debug(f"[fetch_tree] Added dependency: parent={parent_id} → child={site_id}")

        for key in sites_dict:
            site_type = sites_dict[key]["siteType"]
            content["potential_services"].append({
                "id": key,
                "title": sites_dict[key]["siteName"],
                "dependencies": sites_dict[key]["dependencies"],
                "tags": {
                    "siteId": key,
                    "siteName": sites_dict[key]["siteName"],
                    "siteHierarchy": sites_dict[key]["siteHierarchy"],
                    "siteType": sites_dict[key]["siteType"],
                    "parentSiteId": sites_dict[key]["parentSiteId"],
                },
                "type": site_type if site_type == "building" else "N/A"
            })

        if not sites_dict:
            logger.warning("No site hierarchy results found")

        # Store tree and return
        tree_interface = ItsiCpCatalystCenterTree(self.session_key, self.user)
        tree_interface.create(self.user, content)
        return json.dumps(content)

    @InstrumentCall(logger)
    def publish_tree(self, key, publish_as_enabled, site_ids_to_publish=None, levels_up=1):
        """
        Publish a tree representing a draft hierarchy of Catalyst Center services.

        * Tree is deleted upon publish.

        Supports:
            1. site_ids_to_publish + levels_up: Publish selected services and traverse up N levels.
            2. site_ids_to_publish only: Link selected services directly to Global (levels_up == 1).
            3. levels_up only: Publish all isBuilding=True services and traverse up N levels.

        :param key: Key of a ItsiCpCatalystCenterTree object
        :type key: str

        :param publish_as_enabled: Publish services as enabled?
        :type publish_as_enabled: Boolean

        :param site_ids_to_publish: List of services to publish.
        :type site_ids_to_publish: list of str

        :param levels_up:
                        How many levels up to traverse from each selected service.
                        If 1, services are top-level and linked directly to the Global node.
                        If >1, traverses up to N levels and links the highest parent to Global.
        :type levels_up: int

        :return: Summary of publish
        :rtype: str of dict
        """
        if levels_up is None:
            levels_up = 1

        if site_ids_to_publish is None:
            site_ids_to_publish = []

        # Step 1: Fetch the Catalyst Center tree object by key
        tree_interface = ItsiCpCatalystCenterTree(self.session_key, self.user)
        catalyst_center_tree = tree_interface.get(self.user, key)
        if catalyst_center_tree is None:
            raise ITOAError(404, f"Tree {key} not found")
        catalyst_account_name = catalyst_center_tree["account_name"]
        cisco_dnac_host = catalyst_center_tree["controller"]

        # Step 2: Fetch or create a new sandbox
        sandbox_interface = ItsiSandbox(self.session_key, self.user)
        title = CATALYST_CENTER_SANDBOX_TITLE.format(account_name=catalyst_account_name)
        logger.debug("app_tree={} sandbox_title={}".format(catalyst_center_tree, title))
        sandboxes = sandbox_interface.get_bulk("nobody", filter_data={"title": title})
        if not sandboxes:
            desc = (f"Sandbox for {catalyst_account_name} created by "
                    f"Cisco Enterprise Networking Content Pack")
            response = sandbox_interface.create("nobody", {"title": title, "description": desc})
            sandbox_key = response["_key"]
            logger.debug("Created sandbox. sandbox_key={}".format(sandbox_key))
        else:
            sandbox_key = sandboxes[0]["_key"]
            logger.debug("Sandbox already exists. sandbox_key={}".format(sandbox_key))

        # Step 3: Use acquire actual template name by its ID
        template_name = self.get_template_name_by_id(CATALYST_CENTER_SITE_TEMPLATE_ID)
        if not template_name:
            template_name = CATALYST_CENTER_SITE_TEMPLATE
            logger.error(
                f"Template not found for ID {CATALYST_CENTER_SITE_TEMPLATE_ID}, "
                f"using fallback: {template_name}"
            )
        else:
            logger.info(f"Resolved template name: {template_name}")

        # Step 4: Build the import specification
        spec = {
            "service_sandbox": sandbox_key,
            "sandbox_service": {
                "backfillEnabled": "0",
                "criticality": "",
                "descriptionColumns": [],
                "serviceEnabled": "1" if publish_as_enabled else "0",
                "serviceSecurityGroup": "default_itsi_security_group",
                "base_service_template_id": CATALYST_CENTER_SITE_TEMPLATE_ID,
                "serviceTemplate": "template",
                "titleField": "title",
                "service_sandbox": sandbox_key,
            },
            "service_dependents": ["dependencies"],
            "service_rel": [],
            "template": {
                template_name: {
                    "entity_rules": [
                        {
                            "rule_condition": "AND",
                            "rule_items": [
                                {
                                    "field": "cisco_catalyst_host",
                                    "field_type": "info",
                                    "rule_type": "matchesblank",
                                    "value": "cisco_catalyst_host",
                                },
                                {
                                    "field": "site_hierarchy",
                                    "field_type": "info",
                                    "rule_type": "matchesblank",
                                    "value": "siteHierarchy",
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

        # Step 5. build import payload from tree
        sites = catalyst_center_tree.get("potential_services", [])
        csv_import = build_catalyst_import(sites, cisco_dnac_host, template_name,
                                           levels_up, site_ids_to_publish)
        logger.info("About to import catalyst services count=%d", len(csv_import) - 1)
        logger.debug("csv_import=%s", csv_import)

        # Step 6. run the import
        mapped_spec = to_import_specification(spec)
        logger.debug("spec=%s bulk_import_spec=%s", spec, mapped_spec)
        bulk_importer = ServiceSandboxBulkImporter(
            mapped_spec, self.session_key, self.user, "nobody")
        bulk_import_response = bulk_importer.bulk_import(
            csv_import, transaction_id=self.transaction_id)
        logger.info("Catalyst service import response=%s", bulk_import_response)

        # Step 6. Cleanup
        errors = []
        if not bulk_import_response.get("services"):
            error_str = "Bulk import of services failed"
            logger.error(error_str)
            errors.append(error_str)
            record_key = None
        else:
            tree_interface.delete(self.user, key)
            record_interface = ItsiCpCatalystCenterRecord(
                self.session_key, self.user)
            existing_records = record_interface.get_bulk(
                "nobody", filter_data={"controller": cisco_dnac_host, })
            record_data = {
                "sandbox_id": sandbox_key,
                "controller": cisco_dnac_host,
                "title": f"Cisco Catalyst Center Record - {catalyst_account_name}",
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
            "services_created": bulk_import_response.get("services")
        })

    @InstrumentCall(logger)
    def post_object(self, object_class, rest_args, key=None):
        """
        Create or update object in collection
        :param object_class:
        :param rest_args:
        :param key:
        :return:
        """
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
                value = object_interface.create("nobody", data)
            else:
                is_partial_data = normalizeBoolean(
                    rest_args.get("is_partial_data"))
                value = object_interface.update("nobody", data_key, data, is_partial_data=is_partial_data)
        else:
            # No key means it must be an update
            value = object_interface.create("nobody", data)
        return json.dumps(value)

    @InstrumentCall(logger)
    def get_object(self, object_class, key):
        """
        Get object from collection
        :param object_class:
        :param key:
        :return:
        """
        object_interface = object_class(self.session_key, self.user)
        obj = object_interface.get("nobody", key)
        if obj:
            return json.dumps(obj)
        raise ITOAError(
            status=404, message=f"{object_class.object_type} {key} not found")

    @InstrumentCall(logger)
    def get_object_bulk(self, object_class, rest_args):
        """
        Get objects bulk
        :param object_class:
        :param rest_args:
        :return:
        """
        sort_key = rest_args.get("sort_key")
        sort_dir = rest_args.get("sort_dir")
        filter_data = rest_args.get("filter")
        if filter_data:
            filter_data = json.loads(filter_data)
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
        return json.dumps(
            object_interface.get_bulk(
                "nobody",
                sort_key=sort_key,
                sort_dir=sort_dir,
                filter_data=filter_data,
                fields=fields,
                skip=offset,
                limit=limit))

    @InstrumentCall(logger)
    def delete_object(self, object_class, key):
        """
        Delete object
        :param object_class:
        :param key:
        :return:
        """
        object_interface = object_class(self.session_key, self.user)
        return json.dumps(object_interface.delete("nobody", key))

    @InstrumentCall(logger)
    def delete_object_bulk(self, object_class, rest_args):
        """
        Delete objects bulk
        :param object_class:
        :param rest_args:
        :return:
        """
        filter_data = rest_args.get("filter")
        if filter_data:
            filter_data = json.loads(filter_data)
        object_interface = object_class(self.session_key, self.user)
        return json.dumps(
            object_interface.delete_bulk(
                "nobody", filter_data=filter_data))

    @InstrumentCall(logger)
    def fetch_tree_meraki(self, account_name):
        """
        Fetch and build a draft Meraki service tree based on SPL query results.

        * Retrieves Meraki org info from conf using provided account name.
        * Runs SPL to extract Meraki service relationships.
        * Constructs a dependency map and adds it to a new tree.
        * Saves the draft tree in KV Store.

        :param account_name: Meraki credential stanza name (from conf)
        :type account_name: str

        :return: The full Meraki service tree (JSON-encoded)
        :rtype: str
        """
        # Get Meraki controller info from conf
        try:
            stanza = get_conf_stanza(
                "splunk_ta_cisco_meraki_organization", account_name)
            organization_id = stanza.get("organization_id")
        except KeyError as exc:
            raise ITOAError(404, f"No Meraki credential found for account={account_name}") from exc

        # Start building tree structure
        key = str(uuid.uuid4())
        content = {
            "_key": key,
            "title": key,
            "potential_services": [],
            "existing_services": [],
            "controller": organization_id,
            "mod_source": "DA-ITSI-CP-enterprise-networking",
        }

        # Pull existing services if already onboarded
        sandbox_interface = ItsiSandbox(self.session_key, self.user)
        sandboxes = sandbox_interface.get_bulk("nobody", filter_data={
            "title": f"Meraki Sandbox - {organization_id}",
        })
        if sandboxes:
            sandbox_id = sandboxes[0]["_key"]
            sandbox_service_interface = ItsiSandboxService(
                self.session_key, self.user)
            services = sandbox_service_interface.get_bulk(
                "nobody", filter_data={"sandbox_id": sandbox_id})
            content["existing_services"] = [{"title": s["title"]} for s in services]

        # Run SPL to discover Meraki services
        service = ITOAInterfaceUtils.service_connection(self.session_key, "SA-ITOA")
        search_spl = MERAKI_NETWORK_SPL.format(organization_id=organization_id)
        results = service.jobs.oneshot(
            search_spl,
            earliest_time="-30d",
            latest_time="now")
        reader = ResultsReader(results)

        # Parse results and populate potential services into the tree
        service_map = {}
        for row in reader:
            logger.info(f"Parsed SPL row: {row}")
            title = row.get("ServiceTitle")
            dependency = row.get("ServiceDependency")
            service_template = row.get("ServiceTemplate", "N/A")
            network_tag = row.get("NetworkTag", "")

            if title in service_map:
                if dependency and dependency not in service_map[title]["dependencies"]:
                    service_map[title]["dependencies"].append(dependency)
            else:
                service_map[title] = {
                    "id": title,
                    "title": title,
                    "dependencies": [dependency] if dependency else [],
                    "type": service_template,
                    "tags": {
                        "orgId": organization_id,
                        "siteName": title,
                        "networkTag": network_tag,
                    }
                }

        # Add merged services to potential_services
        content["potential_services"].extend(service_map.values())

        # Save and return tree
        tree_interface = ItsiCpMerakiTree(self.session_key, self.user)
        tree_interface.create(self.user, content)
        return json.dumps(content)

    @InstrumentCall(logger)
    def publish_tree_meraki(self, key, publish_as_enabled, service_titles_to_publish=None):
        """
        Publish a Meraki service tree built from previously fetched SPL results.

        This function:
        - Retrieves the draft Meraki service tree stored in KVStore using the provided `key`.
        - Resolves selected services and their dependencies to ensure complete hierarchy.
        - Creates sandbox services and establishes dependencies between them.
        - Publishes the services either as enabled or disabled, depending on the flag.

        :param key: Unique key identifying the draft Meraki tree in KVStore.
        :type key: str

        :param publish_as_enabled: Flag indicating whether to publish services in enabled state.
        :type publish_as_enabled: bool

        :param service_titles_to_publish: List of service titles to publish.
         If empty, all are published.
        :type service_titles_to_publish: list[str]

        :return: Summary dictionary containing metadata about the published services.
        :rtype: dict[str, Any]
        """
        tree_interface = ItsiCpMerakiTree(self.session_key, self.user)
        meraki_tree = tree_interface.get(self.user, key)
        if not meraki_tree:
            raise ITOAError(404, f"Meraki tree {key} not found")

        organization_id = meraki_tree["controller"]
        sandbox_interface = ItsiSandbox(self.session_key, self.user)
        title = f"Meraki Sandbox - {organization_id}"

        sandboxes = sandbox_interface.get_bulk(
            "nobody", filter_data={"title": title})
        if not sandboxes:
            response = sandbox_interface.create("nobody", {
                "title": title,
                "description": f"Sandbox for Meraki Organization {organization_id} "
                               "created by Cisco Enterprise Networking Content Pack",
            })
            sandbox_key = response["_key"]
        else:
            sandbox_key = sandboxes[0]["_key"]

        meraki_network_template_name = self.get_template_name_by_id(MERAKI_NETWORK_TEMPLATE_ID)
        if not meraki_network_template_name:
            meraki_network_template_name = MERAKI_NETWORK_TEMPLATE
            logger.error(
                f"Template not found for ID {MERAKI_NETWORK_TEMPLATE_ID}, "
                f"using fallback: {meraki_network_template_name}"
            )
        else:
            logger.info(f"Resolved template name: {meraki_network_template_name}")

        # Define import spec
        spec = {
            "service_sandbox": sandbox_key,
            "sandbox_service": {
                "backfillEnabled": "0",
                "criticality": "",
                "descriptionColumns": [],
                "serviceEnabled": "1" if publish_as_enabled else "0",
                "serviceSecurityGroup": "default_itsi_security_group",
                "base_service_template_id": MERAKI_NETWORK_TEMPLATE_ID,
                "serviceTemplate": "template",
                "tagsFields": [
                    "orgId",
                    "networkTag"
                ],
                "titleField": "title",
                "service_sandbox": sandbox_key,
            },
            "service_dependents": ["dependencies"],
            "service_rel": [],
            "template": {
                meraki_network_template_name: {
                    "entity_rules": [
                        {
                            "rule_condition": "AND",
                            "rule_items": [
                                {
                                    "field": "Organization_ID",
                                    "field_type": "info",
                                    "rule_type": "matchesblank",
                                    "value": "orgId",
                                },
                                {
                                    "field": "Tags",
                                    "field_type": "info",
                                    "rule_type": "matchesblank",
                                    "value": "networkTag",
                                },
                            ]
                        }
                    ]
                }
            },
            "selectedServices": [],
            "selected_services": [],
            "updateType": "upsert",
            "update_type": "upsert",
        }

        # Fetch organization info
        service = ITOAInterfaceUtils.service_connection(self.session_key, "SA-ITOA")
        search_spl = MERAKI_ORGANIZATION_SPL.format(organization_id=organization_id)
        results = service.jobs.oneshot(search_spl, earliest_time="-30d", latest_time="now")
        reader = ResultsReader(results)
        org_record = next(reader)
        logger.info("Selected meraki organization for import organization=%s", org_record)

        organization_name = org_record.get("name")
        region_name = org_record.get("region")
        host_name = org_record.get("host")

        # Build map and determine which services to publish
        potential_services = meraki_tree["potential_services"]
        service_map = {s["title"]: s for s in potential_services}
        selected_services = set()
        if service_titles_to_publish is None or len(service_titles_to_publish) == 0:
            all_services = [s["title"] for s in potential_services if s["type"] != "N/A"]
            selected_services.update(all_services)
        else:
            selected_services.update(service_titles_to_publish)

        logger.info("Selected meraki services for import services=%s", selected_services)
        services_to_publish = [service_map[title] for title in selected_services]

        # Build CSV for import
        csvlike = [["title", "dependencies", "orgId", "networkTag", "template"]]
        for service in services_to_publish:
            # add row for network tag service
            csvlike.append([
                service["title"],
                "",
                service["tags"].get("orgId", ""),
                service["tags"].get("networkTag", ""),
                meraki_network_template_name,
            ])

            # add row for organization service dependency on network tag service
            csvlike.append([
                organization_name,
                service["title"],
                organization_id,
                "",
                meraki_network_template_name,
            ])

        # add row for meraki host and region
        csvlike.append([host_name, organization_name, "", "", ""])
        csvlike.append([region_name, host_name, "", "", ""])

        logger.info("About to import meraki services count=%d", len(csvlike) - 1)
        logger.debug("import_rows=%s", csvlike)

        # Import
        bulk_importer = ServiceSandboxBulkImporter(
            to_import_specification(spec), self.session_key, self.user, "nobody")
        bulk_import_response = bulk_importer.bulk_import(
            csvlike, transaction_id=self.transaction_id)
        logger.info(f"bulk_import_response={bulk_import_response}")

        # Cleanup
        errors = []
        if not bulk_import_response.get("services"):
            logger.error("Meraki bulk import failed")
            errors.append("Bulk import failed")
            record_key = None
        else:
            tree_interface.delete(self.user, key)
            record_interface = ItsiCpMerakiRecord(self.session_key, self.user)
            existing_records = record_interface.get_bulk(
                "nobody", filter_data={"controller": organization_id})
            record_data = {
                "sandbox_id": sandbox_key,
                "controller": organization_id,
                "title": f"Meraki Record - {organization_id}",
                "publish_time": int(time.time()),
            }
            if not existing_records:
                record_key = record_interface.create(
                    "nobody", record_data)["_key"]
            else:
                record_key = existing_records[0]["_key"]
                record_interface.update("nobody", record_key, record_data)

        return json.dumps({
            "sandbox_id": sandbox_key,
            "record_id": record_key,
            "errors": errors,
            "services_created": bulk_import_response.get("services"),
        })


class ItsiCpCatalystCenterRestInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for
    `DA-ITSI-CP-enterprise-networking` endpoints.
    """

    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super().__init__()

    def handle(self, args):
        """
        Blanket handler for REST calls, routing GET/POST/PUT/DELETE requests on the interface.
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
        if path_parts[0] == "cl_discovery":
            if path_parts[1] == "tree":
                object_class = ItsiCpCatalystCenterTree
            elif path_parts[1] == "itsi_cp_catalyst_center_records":
                object_class = ItsiCpCatalystCenterRecord
            elif path_parts[1] == "itsi_cp_meraki_records":
                object_class = ItsiCpMerakiRecord
            # Not basic CRUD
            elif path_parts[1] in ["fetch_tree", "fetch_tree_meraki",
                                   "publish_tree", "publish_tree_meraki"]:
                object_class = None
            else:
                raise ITOAError(
                    status=404,
                    message="Object type {} not found".format(
                        path_parts[1]))

            if rest_method == "POST":
                # Basic CRUD
                if object_class:
                    if len(path_parts) == 2:
                        return request_handler.post_object(
                            object_class, rest_method_args)
                    if len(path_parts) == 3:
                        return request_handler.post_object(
                            object_class, rest_method_args, key=path_parts[2])

                # Other functions
                if len(path_parts) == 2 and path_parts[1] == "fetch_tree":
                    account = rest_method_args.get("account")
                    if not account:
                        raise ITOAError(400, "Missing `account` query parameter")
                    return request_handler.fetch_tree(account)

                if len(path_parts) == 2 and path_parts[1] == "fetch_tree_meraki":
                    account = rest_method_args.get("account")
                    if not account:
                        raise ITOAError(400, "Missing `account` query parameter")
                    return request_handler.fetch_tree_meraki(account)

                if len(path_parts) == 3 and path_parts[1] == "publish_tree":
                    payload = rest_method_args.get("data", {})
                    selected_services = payload.get("selected_services", [])
                    levels_up = payload.get("levels_up", 1)
                    publish_as_enabled = payload.get("publish_as_enabled", False)

                    return request_handler.publish_tree(
                        path_parts[2],
                        publish_as_enabled,
                        site_ids_to_publish=selected_services,
                        levels_up=levels_up)

                if len(path_parts) == 3 and path_parts[1] == "publish_tree_meraki":
                    payload = rest_method_args.get("data", {})
                    selected_services = payload.get("selected_services", [])
                    publish_as_enabled = payload.get("publish_as_enabled", False)

                    return request_handler.publish_tree_meraki(
                        path_parts[2],
                        publish_as_enabled,
                        service_titles_to_publish=selected_services
                    )

            elif rest_method == "GET":
                # Basic CRUD
                if object_class:
                    if len(path_parts) == 2:
                        return request_handler.get_object_bulk(
                            object_class, rest_method_args)
                    if len(path_parts) == 3:
                        return request_handler.get_object(
                            object_class, path_parts[2])
            elif rest_method == "DELETE":
                # Basic CRUD
                if object_class:
                    if len(path_parts) == 2:
                        return request_handler.delete_object_bulk(
                            object_class, rest_method_args)
                    if len(path_parts) == 3:
                        return request_handler.delete_object(
                            object_class, path_parts[2])
        raise ITOAError(
            status=404,
            message="Specified REST URL/path is invalid - {}.".format(rest_path))
