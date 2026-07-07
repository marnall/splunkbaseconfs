"""
Modular input to collect Tier Zero assets from BloodHound Enterprise via its REST API
"""
import json
from rest_client import make_cypher_request, log_error

"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Placeholder for input validation"""
    pass


# ------------------ Helper Functions ------------------ #


def build_tier_zero_cypher_query():
    """Builds the Cypher query for Tier Zero assets"""
    return {
        "query": (
            "match (n) "
            "where (n:Tag_Tier_Zero) or "
            "coalesce(n.system_tags,'') contains('admin_tier_0') "
            "return n"
        ),
        "include_properties": True,
    }


def fetch_available_domains(helper, ew):
    """Fetch available domains and return a mapping of domain_id -> metadata"""
    from rest_client import get_available_domains

    domain_mapping = {}
    response = get_available_domains(helper, ew)

    if not response or response == "UNAUTHORIZED":
        helper.log_error("[ERROR] Failed to fetch available domains or unauthorized. Stopping execution.")
        return domain_mapping
    
    if "data" not in response:
        helper.log_warning("No data returned from available domains API")
        return domain_mapping

    # Handle case where data might be None
    domains = response.get("data") or []
    for domain in domains:
        domain_id = domain.get("id")
        if domain_id:
            domain_mapping[domain_id] = {
                "name": domain.get("name"),
                "collected": domain.get("collected"),
                "type": domain.get("type"),
                "impact_value": domain.get("impactValue"),
            }

    helper.log_info(f"Retrieved {len(domain_mapping)} available domains")
    return domain_mapping


def extract_nodes_from_response(response):
    """Extract nodes dictionary from Cypher response"""
    # Handle case where data might be None, and nodes might be None
    data = response.get("data") or {}
    return data.get("nodes") or {}


def filter_nodes(helper, nodes_dict, available_domains):
    """Filter nodes by domain collection status and node kind"""
    filtered_nodes = {}
    excluded_counts = {"uncollected_domain": 0, "meta_kind": 0}

    for node_id, node_data in nodes_dict.items():
        node_kind = node_data.get("kind", "")

        if node_kind == "Meta":
            excluded_counts["meta_kind"] += 1
            helper.log_debug(f"Excluding node {node_id} - kind is Meta")
            continue

        domain_id = get_node_domain_id(node_data)
        if domain_id in available_domains and not available_domains[domain_id].get(
            "collected"
        ):
            excluded_counts["uncollected_domain"] += 1
            helper.log_debug(
                f"Excluding node {node_id} - domain {domain_id} not collected"
            )
            continue

        filtered_nodes[node_id] = node_data

    total_excluded = sum(excluded_counts.values())
    helper.log_info(
        f"Excluded {total_excluded} nodes: {excluded_counts['uncollected_domain']}"
        "uncollected, {excluded_counts['meta_kind']} Meta"
    )
    return filtered_nodes


def get_node_domain_id(node_data):
    """Extract domain ID from node data"""
    properties = node_data.get("properties", {})

    if "owner_objectid" in properties:
        return properties["owner_objectid"]
    if "domainsid" in properties:
        return properties["domainsid"]
    if "objectId" in node_data:
        return node_data["objectId"]

    label = node_data.get("label", "")
    if "@" in label:
        return label.split("@")[-1]

    return None


def process_nodes(helper, ew, nodes_dict, source_domain_config, available_domains):
    """Iterate through nodes and write events to Splunk"""
    sourcetype = "BHE:tier_zero_assets"

    for node_id, node_data in nodes_dict.items():
        transformed_asset = transform_node_to_asset(
            helper, ew, node_data, source_domain_config, node_id, available_domains
        )
        if not transformed_asset:
            helper.log_warning(f"Failed to transform node {node_id}")
            continue

        write_splunk_event(helper, ew, transformed_asset, sourcetype)


def transform_node_to_asset(
    helper, ew, node_data, source_domain_config, node_id, available_domains
):
    """Transform a node dictionary into a Splunk-friendly asset dictionary"""
    properties = node_data.get("properties", {})
    object_id = properties.get("owner_objectid") or node_data.get("objectId") or node_id

    name = (
        properties.get("displayname") or properties.get("name") or "Not available"
    ).strip()

    raw_domain_name = extract_domain_name_with_mapping(
        node_data, properties, node_data.get("label", ""), available_domains
    )
    domain_name = apply_domain_grouping(raw_domain_name)

    asset = {
        "objectid": object_id,
        "name": name,
        "source_domain": source_domain_config,
        "domain_name": domain_name,
        "raw_domain_name": raw_domain_name,
        "kind": node_data.get("kind", "Unknown"),
        "label": node_data.get("label", ""),
        "isTierZero": node_data.get("isTierZero", False),
        "isOwnedObject": node_data.get("isOwnedObject", False),
        "lastSeen": node_data.get("lastSeen", ""),
    }

    # Merge properties into asset dictionary
    asset.update(properties)
    return asset


def extract_domain_name_with_mapping(node_data, properties, label, available_domains):
    """Extract domain name using properties, available_domains mapping, or label"""
    for key in ["owner_objectid", "domainsid"]:
        if key in properties:
            domain_info = available_domains.get(properties[key])
            if domain_info:
                return domain_info.get("name", "Unknown")

    object_id = node_data.get("objectId")
    if object_id and object_id in available_domains:
        return available_domains[object_id].get("name", "Unknown")

    if "@" in label:
        return label.split("@")[-1]

    return "Unknown"


def apply_domain_grouping(domain_name):
    """Normalize domain names for grouping"""
    if not domain_name:
        return "Unknown"

    domain_upper = domain_name.upper()

    specter_domains = ["SPECTERDEV.ONMICROSOFT.COM", "SPECTEROPS DEVELOPMENT"]
    if any(s in domain_upper for s in specter_domains):
        return "SPECTEROPS DEVELOPMENT"

    if "PHANTOM" in domain_upper and domain_upper != "PHANTOM.CORP":
        return "PHANTOM CORP"

    return domain_upper


def write_splunk_event(helper, ew, transformed_asset, sourcetype):
    """Write a single asset event to Splunk"""
    event_data_json = json.dumps(transformed_asset)
    event = helper.new_event(
        event_data_json,
        time=None,
        host=None,
        index=helper.get_output_index(),
        source=None,
        sourcetype=sourcetype,
        done=True,
        unbroken=True,
    )
    ew.write_event(event)
    helper.log_debug(f"[DEBUG] Event written for {transformed_asset.get('objectid')}")


def collect_events(helper, ew):
    """
    Main event collection function for Tier Zero assets
    """
    try:
        helper.log_info("[INFO] Starting collect_events function for Tier Zero assets")

        source_domain_config = helper.get_arg("bloodhound_account").get("domain_name")

        available_domains = fetch_available_domains(helper, ew)
        cypher_query = build_tier_zero_cypher_query()

        cypher_response = make_cypher_request(helper, ew, cypher_query)
        if not cypher_response or cypher_response == "UNAUTHORIZED":
            if cypher_response == "UNAUTHORIZED":
                helper.log_error("[ERROR] Unauthorized access. Stopping execution.")
            else:
                helper.log_warning("No data returned from Cypher query after retries")
            return
        
        if "data" not in cypher_response:
            helper.log_warning("No data returned from Cypher query")
            return

        nodes = extract_nodes_from_response(cypher_response)
        filtered_nodes = filter_nodes(helper, nodes, available_domains)

        helper.log_info(f"Processing {len(filtered_nodes)} Tier Zero assets")
        process_nodes(
            helper, ew, filtered_nodes, source_domain_config, available_domains
        )

        helper.log_info(f"Finished processing {len(filtered_nodes)} Tier Zero assets")

    except Exception as exception:
        log_error(helper, ew, "tier_zero_collect_events", exception)

