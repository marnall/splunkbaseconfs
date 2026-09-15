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
from soar_sdk.params import MakeRequestParams, Param, Params


class CiscoSecureAccessMakeRequestParams(MakeRequestParams):
    endpoint: str = Param(
        required=True,
        description=(
            "Cisco Secure Access API path, relative to the configured base URL. "
            "For example: 'deployments/v2/networkdevices' or "
            "'admin/v2/vpn/userConnections'. Do not include the base URL."
        ),
    )
    verify_ssl: bool = Param(
        required=False,
        default=True,
        description="Whether to verify the SSL certificate. Default true.",
    )


class ListDestinationListsParams(Params):
    list_destinations: bool = Param(
        required=False,
        default=False,
        description="If true, also fetch and embed each list's destination entries. "
        "Default false (returns list metadata only).",
    )


DESTINATION_LIST_ACCESS_VALUES = [
    "allow",
    "block",
    "url_proxy",
    "no_decrypt",
    "warn",
    "none",
    "thirdparty_block",
]


class CreateDestinationListParams(Params):
    """Parameters for Create Destination List. POST policies/v2/destinationlists. Requires policies.destinationLists:write."""

    name: str = Param(
        required=True,
        description="Name of the destination list.",
    )
    access: str = Param(
        required=True,
        description="Access classification for the list (used with access rules). Cannot create lists with access type thirdparty_block via this API.",
        value_list=DESTINATION_LIST_ACCESS_VALUES,
    )
    destinations_json: str = Param(
        required=False,
        description='Optional JSON array of up to 500 destinations, e.g. [{"destination":"cisco.com","type":"domain","comment":"optional"}]. type: domain, url, or ipv4.',
    )


class AddToDestinationListParams(Params):
    destination_list_id: int = Param(
        required=False,
        description="Destination List ID. If not provided, the default destination list ID will be used.",
    )
    destination: str = Param(
        required=True, description="Destination URL, domain, or IP address"
    )
    comment: str = Param(required=False, description="Comment for the destination")


class RemoveDestinationsFromListParams(Params):
    destination_list_id: int = Param(
        required=False,
        description="The ID of the Destination List to remove destinations from. If not provided, the default destination list ID will be used.",
    )
    destination_ids: str = Param(
        required=True,
        description="Comma-separated destination IDs to remove (e.g. 60582,60583).",
    )


class GetDomainParams(Params):
    domain: str = Param(
        required=True, description="Domain name to look up (e.g. cisco.com)."
    )


class GetPassiveDNSParams(Params):
    """Parameters for Get Passive DNS. GET investigate/v2/pdns/name/{domain}."""

    domain: str = Param(
        required=True, description="The domain to get passive DNS records for."
    )
    offset: int = Param(
        required=False,
        default=0,
        description="Index to start reading the collection (0-based). Default 0.",
    )
    limit: int = Param(
        required=False,
        default=1000,
        description="Maximum records to return in one call (1-9999). Default 1000. "
        "Use 9999 to retrieve the full set in a single call; the API caps total "
        "retrievable records at 10000 per domain.",
    )


IDENTITY_TYPE_VALUES = ["device", "securityGroupTag"]


class ListIdentitiesParams(Params):
    type: str = Param(
        required=True,
        description="Identity type to list: 'device' for device registrations, "
        "'securityGroupTag' for security group tags (SGTs).",
        value_list=IDENTITY_TYPE_VALUES,
    )


class UpdateIdentitiesParams(Params):
    type: str = Param(
        required=True,
        description="Identity type: 'device' for identity endpoints, 'securityGroupTag' for SGTs.",
        value_list=IDENTITY_TYPE_VALUES,
    )
    identities_json: str = Param(
        required=True,
        description='JSON array of identity objects (1-250). Devices: {"key","label","status","authName"}. SGTs: {"key","label","status","tagId"}. status: "active"|"inactive".',
    )


class ListCertificatesForDeviceParams(Params):
    user_id: str = Param(required=True, description="The ID of the user (ZTNA).")
    device_id: str = Param(required=True, description="The ID of the user device.")


class ListCertificatesForUserParams(Params):
    user_id: str = Param(
        required=True,
        description="The ID of the user (ZTNA). Get all device certificates for this user.",
    )


class GetRoamingComputerParams(Params):
    device_id: str = Param(
        required=True,
        description="The device ID (deviceId) of the roaming computer, e.g. AB00C7DCEC99D211.",
    )


class DeleteManagedDeviceParams(Params):
    origin_id: int = Param(
        required=True,
        description="Origin ID of the network device to remove (obtain from the List Managed Devices action).",
    )


class GetNetworkDeviceParams(Params):
    """Parameters for Get Network Device. GET deployments/v2/networkdevices/{originId}. Requires deployments.networkdevices:read."""

    origin_id: int = Param(
        required=True,
        description="Origin ID of the network device (obtain from the List Managed Devices action).",
    )


class GetNetworkTunnelGroupParams(Params):
    """Parameters for Get Network Tunnel Group. GET deployments/v2/networktunnelgroups/{id}. Requires deployments.networktunnelgroups:read."""

    id: int = Param(
        required=True,
        description="ID of the network tunnel group (obtain from the List Network Tunnel Groups action).",
    )


class ListSWGOverrideDeviceSettingsParams(Params):
    """Parameters for List SWG Override Device Settings. POST deployments/v2/deviceSettings/SWGEnabled/list. Requires deployments.devices.swg:read."""

    origin_ids: str = Param(
        required=True,
        description="Comma-separated origin IDs of devices (1-100) to list SWG override settings for.",
    )


class DeleteSWGOverrideDeviceSettingsParams(Params):
    """Parameters for Delete SWG Override Device Settings. POST deployments/v2/deviceSettings/SWGEnabled/remove. Requires deployments.devices.swg:write."""

    origin_ids: str = Param(
        required=True,
        description="Comma-separated origin IDs of devices (1-100) to remove SWG override setting from. Organization SWG setting will apply after removal.",
    )


class SetSWGOverrideDeviceSettingsParams(Params):
    """Parameters for Set SWG Override Device Settings. POST deployments/v2/deviceSettings/SWGEnabled/set. Requires deployments.devices.swg:write."""

    value: str = Param(
        required=True,
        description="Enable (1) or disable (0) Secure Web Gateway for the devices.",
        value_list=["0", "1"],
    )
    origin_ids: str = Param(
        required=True,
        description="Comma-separated origin IDs of devices (1-100). Devices must be registered as roaming computers.",
    )


class ListResourceConnectorsParams(Params):
    """Parameters for List Resource Connectors. GET deployments/v2/connectorAgents. Requires deployments.resourceconnectors:read."""

    offset: int = Param(
        required=False,
        default=0,
        description="Index to start reading the collection (0-based). Default 0.",
    )
    limit: int = Param(
        required=False,
        default=10,
        description="Maximum number of items to return. Default 10.",
    )
    filters: str = Param(
        required=False,
        description="Optional JSON object to filter by groupId, instanceId, status, confirmed, hasSynced, hasLatestVersion. See API docs.",
    )
    sort_by: str = Param(
        required=False,
        default="originIpAddress",
        description="Sort field: instanceId, originIpAddress, createdAt, modifiedAt.",
        value_list=["instanceId", "originIpAddress", "createdAt", "modifiedAt"],
    )
    sort_order: str = Param(
        required=False,
        default="asc",
        description="Sort order: asc or desc.",
        value_list=["asc", "desc"],
    )


class ListNetworkTunnelGroupsParams(Params):
    """Parameters for List Network Tunnel Groups. GET deployments/v2/networktunnelgroups. Requires deployments.networktunnelgroups:read."""

    offset: int = Param(
        required=False,
        default=0,
        description="Index to start reading the collection (0-based). Default 0.",
    )
    limit: int = Param(
        required=False,
        default=10,
        description="Number of records per page (1-200). Default 10.",
    )
    filters: str = Param(
        required=False,
        description="Optional JSON object to filter by name, exactName, region, networkTunnelGroupIds, exactAuthIdPrefix, status, or duplicateCIDRs. See API docs.",
    )
    sort_by: str = Param(
        required=False,
        default="name",
        description="Sort field: name, status, createdAt, modifiedAt.",
        value_list=["name", "status", "createdAt", "modifiedAt"],
    )
    sort_order: str = Param(
        required=False,
        default="asc",
        description="Sort order: asc or desc.",
        value_list=["asc", "desc"],
    )
    include_statuses: bool = Param(
        required=False,
        default=False,
        description="Include tunnelsStatus for each hub (max 10 tunnel states per hub).",
    )


class ListFirewallRulesParams(Params):
    offset: int = Param(
        required=False,
        default=0,
        description="Index to start reading the collection (0-based). Default 0.",
    )
    limit: int = Param(
        required=False,
        default=10,
        description="Number of rules per page. Max 1000. Default 10.",
    )
    rule_name: str = Param(
        required=False,
        description="Filter by rule name or substring (e.g. 'Allow all rule').",
    )
    filters: str = Param(
        required=False,
        description="Optional JSON object to filter rules by properties (ruleName, ruleDescription, ruleIsEnabled, ruleAction, ruleConditions, sources, destinations, etc.). Cannot combine ruleConditions with sources/destinations.",
    )


RULE_ACTION_VALUES = ["allow", "block"]


class CreateRuleParams(Params):
    """Parameters for Create Rule. POST policies/v2/rules. Requires policies.rules:write."""

    rule_name: str = Param(
        required=True,
        description="Rule name (2-50 alphanumeric, hyphen, underscore, space). Unique across access rules.",
    )
    rule_action: str = Param(
        required=True,
        description="Action for the rule.",
        value_list=RULE_ACTION_VALUES,
    )
    rule_conditions_json: str = Param(
        required=True,
        description='JSON array of conditions, e.g. [{"attributeName":"umbrella.destination.all","attributeValue":true,"attributeOperator":"="},{"attributeName":"umbrella.source.all","attributeValue":true,"attributeOperator":"="}]',
    )
    rule_settings_json: str = Param(
        required=True,
        description='JSON array of settings, e.g. [{"settingName":"umbrella.default.traffic","settingValue":"PUBLIC_INTERNET"}]',
    )
    rule_description: str = Param(
        required=False,
        description="Optional description (max 256 characters).",
    )
    rule_priority: int = Param(
        required=False,
        description="Optional priority (positive integer, unique across rules).",
    )
    rule_is_enabled: bool = Param(
        required=False,
        default=True,
        description="Whether the rule is enabled. Default true.",
    )
