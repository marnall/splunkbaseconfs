# Copyright (c) 2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .actions.destination_lists import (
    add_to_destination_list,
    create_destination_list,
    list_destination_lists,
    remove_destinations_from_list,
)
from .actions.devices import (
    delete_managed_device,
    get_network_device,
    get_network_tunnel_group,
    get_roaming_computer,
    list_managed_devices,
    list_network_tunnel_groups,
    list_resource_connectors,
    list_roaming_computers,
    list_sites,
    list_virtual_appliances,
)
from .actions.domains import get_domain_risk_score, get_domain_status, get_passive_dns
from .actions.identities import (
    list_certificates_for_device,
    list_certificates_for_user,
    list_identities,
    update_identities,
)
from .actions.make_request import make_request
from .actions.rules import create_rule, list_firewall_rules
from .actions.swg import (
    delete_swg_override_device_settings,
    list_swg_override_device_settings,
    set_swg_override_device_settings,
)
from .actions.vpn import list_vpn_sessions
from .core import app, test_connectivity


app.test_connectivity()(test_connectivity)
test_connectivity_action = app.get_actions()["test_connectivity"]
test_connectivity_action.meta.description = (
    "Test OAuth authentication to Cisco Secure Access."
)
test_connectivity_action.meta.verbose = (
    "Verifies that the configured asset can authenticate to Cisco Secure Access "
    "with OAuth credentials."
)

app.register_action(
    list_destination_lists,
    read_only=True,
    description="List Cisco Secure Access destination lists.",
    verbose=(
        "Lists destination list metadata. Set list_destinations to true to also "
        "fetch destination entries for each list. Use destination list IDs from "
        "this action when adding or removing destinations."
    ),
)
app.register_action(
    create_destination_list,
    description="Create a Cisco Secure Access destination list.",
    verbose=(
        "Creates a non-global destination list for Access policies. The request "
        "sets isGlobal=false and bundleTypeId=2. Optional destinations_json must "
        "be a JSON array of no more than 500 domain, URL, or IPv4 destinations. "
        "Cisco Secure Access does not support creating thirdparty_block "
        "destination lists through this API."
    ),
    read_only=False,
)
app.register_action(
    add_to_destination_list,
    description="Add one domain, URL, or IP destination to a destination list.",
    verbose=(
        "Adds one destination entry per run. Provide a destination list ID from "
        "List Destination Lists, or configure a default destination list ID on "
        "the asset. The destination can be a domain, URL, or IP address."
    ),
    read_only=False,
)
app.register_action(
    remove_destinations_from_list,
    description="Remove one or more destination entries from a destination list.",
    verbose=(
        "Removes destination entries by destination entry ID, not by destination "
        "value. Get entry IDs from List Destination Lists with list_destinations "
        "enabled or from Add To Destination List output. Provide a destination "
        "list ID or configure a default destination list ID on the asset."
    ),
    read_only=False,
)

app.register_action(
    list_managed_devices,
    read_only=True,
    description="List managed network devices registered in Cisco Secure Access.",
    verbose=(
        "Lists Cisco Secure Access managed network devices. Use the originId "
        "returned by this action as the lookup or delete identifier for a device."
    ),
)
app.register_action(
    delete_managed_device,
    description="Delete one managed network device by origin ID.",
    verbose=(
        "Deletes a managed network device using its originId. Get the originId "
        "from List Managed Devices."
    ),
    read_only=False,
)
app.register_action(
    get_network_device,
    read_only=True,
    description="Get details for one managed network device by origin ID.",
    verbose=(
        "Retrieves one managed network device using its originId. Get the "
        "originId from List Managed Devices."
    ),
)
app.register_action(
    list_virtual_appliances,
    read_only=True,
    description="List virtual appliances in the organization",
)
app.register_action(
    list_sites,
    read_only=True,
    description="List sites in the organization",
)
app.register_action(
    get_roaming_computer,
    read_only=True,
    description="Get posture and security details for a roaming computer",
)
app.register_action(
    list_roaming_computers,
    read_only=True,
    description="List roaming computers in the organization",
)
app.register_action(
    list_network_tunnel_groups,
    read_only=True,
    description="List network tunnel groups in the organization",
)
app.register_action(
    get_network_tunnel_group,
    read_only=True,
    description="Get a network tunnel group by ID",
)
app.register_action(
    list_resource_connectors,
    read_only=True,
    description="List resource connectors in the organization",
)

app.register_action(
    get_domain_status,
    read_only=True,
    description="Get the status and categorization of a domain",
)
app.register_action(
    get_domain_risk_score,
    read_only=True,
    description="Get the risk score for a domain",
)
app.register_action(
    get_passive_dns,
    read_only=True,
    description="Get passive DNS records for a domain",
)

app.register_action(
    list_identities,
    read_only=True,
    description="List device or security group tag identities",
    verbose=(
        "Lists identities by type. Use type=device for device registrations or "
        "type=securityGroupTag for security group tag identities."
    ),
)
app.register_action(
    update_identities,
    description="Create or update device or security group tag identities",
    verbose=(
        "Creates or updates 1-250 identity objects from identities_json. Use "
        "type=device for device registrations and type=securityGroupTag for "
        "security group tag identities. Device objects use key, label, status, "
        "and authName. Security group tag objects use key, label, status, and "
        "tagId. Set status to inactive to deactivate an identity."
    ),
    read_only=False,
)
app.register_action(
    list_certificates_for_device,
    read_only=True,
    description="List latest ZTNA certificates for a specific user device.",
    verbose=(
        "Lists the latest ACME-issued ZTNA certificates for one user device by "
        "user ID and device ID."
    ),
)
app.register_action(
    list_certificates_for_user,
    read_only=True,
    description="List latest ZTNA device certificates for a user.",
    verbose=(
        "Lists the latest ACME-issued ZTNA device certificates for all devices "
        "associated with the specified user ID."
    ),
)

app.make_request()(make_request)
make_request_action = app.get_actions()["make_request"]
make_request_action.meta.description = (
    "Send an authenticated request to a Cisco Secure Access API endpoint."
)
make_request_action.meta.verbose = (
    "Sends an authenticated request using the asset's Cisco Secure Access OAuth "
    "credentials. Provide an API path relative to the configured base URL, such "
    "as deployments/v2/networkdevices. Do not include the base URL."
)

app.register_action(
    create_rule,
    description="Create an access policy rule.",
    verbose=(
        "Creates an access policy rule. rule_conditions_json and "
        "rule_settings_json are required JSON arrays. rule_name must be unique "
        "and 2-50 characters."
    ),
    read_only=False,
)
app.register_action(
    list_firewall_rules,
    read_only=True,
    description="List access policy rules.",
    verbose=(
        "Lists access policy rules. Use rule_name or filters to narrow results "
        "when needed."
    ),
)

app.register_action(
    list_swg_override_device_settings,
    read_only=True,
    description="List Cisco Secure Web Gateway override settings for managed devices.",
    verbose=(
        "Lists Cisco Secure Web Gateway override settings for 1-100 device "
        "origin IDs. Use origin IDs from managed or roaming device inventory."
    ),
)
app.register_action(
    set_swg_override_device_settings,
    description="Set Cisco Secure Web Gateway override settings for managed devices.",
    verbose=(
        "Sets Cisco Secure Web Gateway override settings for 1-100 device "
        "origin IDs. Use value 1 to enable Secure Web Gateway and value 0 to "
        "disable it for the specified devices."
    ),
    read_only=False,
)
app.register_action(
    delete_swg_override_device_settings,
    description="Delete Cisco Secure Web Gateway override settings for managed devices.",
    verbose=(
        "Deletes Cisco Secure Web Gateway override settings for 1-100 device "
        "origin IDs. After removal, the organization Secure Web Gateway setting "
        "applies."
    ),
    read_only=False,
)

app.register_action(
    list_vpn_sessions,
    read_only=True,
    description="List active VPN sessions",
)


if __name__ == "__main__":
    app.cli()
