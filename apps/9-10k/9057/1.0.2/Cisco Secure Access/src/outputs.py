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
from soar_sdk.action_results import ActionOutput


class ManagedDevice(ActionOutput):
    originId: int
    deviceId: str
    deviceKey: str
    name: str
    serialNumber: str
    createdAt: str
    organizationId: int


class ListManagedDevicesOutput(ActionOutput):
    devices: list[ManagedDevice]


class GetNetworkDeviceOutput(ActionOutput):
    """Response from Get Network Device API (GET deployments/v2/networkdevices/{originId}). Same shape as ManagedDevice."""

    originId: int
    deviceId: str
    deviceKey: str
    name: str
    serialNumber: str
    createdAt: str
    organizationId: int


class DeleteManagedDeviceOutput(ActionOutput):
    success: bool = True
    message: str | None = None


class VirtualAppliance(ActionOutput):
    originId: int
    name: str
    isUpgradable: bool
    health: str
    type: str
    stateUpdatedAt: str
    siteId: int | None = None
    createdAt: str | None = None
    modifiedAt: str | None = None
    # Flattened from API's `state` object
    state_syncing: str | None = None
    # Flattened from API's `settings` object
    internalIPs: list[str] | None = None
    externalIP: str | None = None
    hostType: str | None = None
    uptime: int | None = None
    version: str | None = None
    domains: list[str] | None = None
    lastSyncTime: str | None = None


class ListVirtualAppliancesOutput(ActionOutput):
    virtualAppliances: list[VirtualAppliance]


class Site(ActionOutput):
    originId: int
    name: str
    siteId: int
    isDefault: bool
    modifiedAt: str
    createdAt: str
    type: str | None = None
    internalNetworkCount: int | None = None
    vaCount: int | None = None


class ListSitesOutput(ActionOutput):
    sites: list[Site]


class Destination(ActionOutput):
    id: str
    type: str
    createdAt: str
    destination: str | None = None
    comment: str | None = None


class DestinationList(ActionOutput):
    id: int
    organizationId: int
    access: str
    isGlobal: bool
    name: str
    thirdpartyCategoryId: int | None = None  # API may return null
    createdAt: int
    modifiedAt: int
    isMspDefault: bool
    markedForDeletion: bool
    bundleTypeId: int | None = None
    destinationCount: int | None = None
    domainCount: int | None = None
    urlCount: int | None = None
    ipv4Count: int | None = None
    ipv6Count: int | None = None
    applicationCount: int | None = None
    destinations: list[Destination] | None = None


class ListDestinationListsOutput(ActionOutput):
    destinationLists: list[DestinationList]


class AddToDestinationListOutput(ActionOutput):
    addedDestinationId: str | None = None
    destinationList: DestinationList


class CreateDestinationListOutput(ActionOutput):
    """Response data from Create Destination List (POST policies/v2/destinationlists)."""

    destinationList: DestinationList


class RemoveDestinationsFromListOutput(ActionOutput):
    destinationList: DestinationList


class RoamingComputer(ActionOutput):
    """Roaming computer from Get/List Roaming Computers. Required per schema: originId, name, deviceId, type, status, swgStatus, lastSyncStatus, lastSyncSwgStatus, lastSync, appliedBundle, hasIpBlocking, version, osVersion, osVersionName."""

    originId: int
    name: str
    deviceId: str
    type: str
    status: str
    swgStatus: str
    lastSyncStatus: str
    lastSyncSwgStatus: str
    lastSync: str
    appliedBundle: int
    hasIpBlocking: bool
    version: str
    osVersion: str
    osVersionName: str
    anyconnectDeviceId: str | None = None


class GetRoamingComputerOutput(ActionOutput):
    """Posture/security status for a roaming computer (Get Roaming Computer API). Same required fields as RoamingComputer."""

    originId: int
    name: str
    deviceId: str
    type: str
    status: str
    swgStatus: str
    lastSyncStatus: str
    lastSyncSwgStatus: str
    lastSync: str
    appliedBundle: int
    hasIpBlocking: bool
    version: str
    osVersion: str
    osVersionName: str
    anyconnectDeviceId: str | None = None


class ListRoamingComputersOutput(ActionOutput):
    roamingComputers: list[RoamingComputer]


class GetDomainStatusOutput(ActionOutput):
    domain: str
    status: int | None = None
    status_description: str | None = None
    security_categories: list[str] | None = None
    content_categories: list[str] | None = None


class DomainRiskIndicator(ActionOutput):
    indicator: str | None = None
    normalized_score: int | None = None
    score: float | None = None


class GetDomainRiskScoreOutput(ActionOutput):
    risk_score: int | None = None
    indicators: list[DomainRiskIndicator] | None = None


class PassiveDNS(ActionOutput):
    minTtl: int | None = None
    maxTtl: int | None = None
    firstSeen: int | None = None
    lastSeen: int | None = None
    name: str | None = None
    type: str | None = None
    rr: str | None = None
    securityCategories: list[str] | None = None
    contentCategories: list[str] | None = None
    firstSeenISO: str | None = None
    lastSeenISO: str | None = None


class GetPassiveDNSOutput(ActionOutput):
    passive_dns_records: list[PassiveDNS] | None = None
    total_records: int | None = None
    returned_records: int | None = None
    offset: int | None = None
    limit: int | None = None
    has_more_records: bool | None = None
    next_offset: int | None = None


class VPNSession(ActionOutput):
    username: str | None = None
    deviceName: str | None = None
    assignedIp: str | None = None  # RFC 1918 IPv4 assigned to the VPN connection
    assignedIpv6: str | None = None  # IPv6 assigned to the VPN session
    publicIp: str | None = None
    sessionId: str | None = None
    loginTime: str | None = None
    profileName: str | None = None


class ListVPNSessionsOutput(ActionOutput):
    vpn_sessions: list[VPNSession]


class Identity(ActionOutput):
    key: str
    label: str
    status: str
    createdAt: int
    modifiedAt: int
    authName: str | None = None
    tagId: int | None = None


class ListIdentitiesOutput(ActionOutput):
    """Identities from List Identities. Client returns data array; API schema has total, limit, offset, data."""

    identities: list[Identity]


class UpdateIdentitiesOutput(ActionOutput):
    success: bool | None = None


class ZtnaCertificate(ActionOutput):
    """ACME-issued certificate for a ZTNA user device (List Certificates for Device)."""

    certificateId: str | None = None
    status: str | None = None  # active | expired | revoked
    createdAt: str | None = None
    expiresAt: str | None = None
    revokedAt: str | None = None


class ListCertificatesForDeviceOutput(ActionOutput):
    deviceId: str | None = None
    certificates: list[ZtnaCertificate] | None = None


class ZtnaDeviceCertificateInfo(ActionOutput):
    """Device ID and its certificates (List Certificates for User)."""

    deviceId: str | None = None
    certificates: list[ZtnaCertificate] | None = None


class ListCertificatesForUserOutput(ActionOutput):
    userId: str | None = None
    devices: list[ZtnaDeviceCertificateInfo] | None = None


class FirewallRule(ActionOutput):
    """Access rule from List Rules API. Required per schema: ruleId."""

    ruleId: int
    organizationId: int | None = None
    ruleName: str | None = None
    ruleDescription: str | None = None
    ruleAction: str | None = None
    rulePriority: int | None = None
    ruleIsDefault: bool | None = None
    ruleIsEnabled: bool | None = None
    modifiedBy: str | None = None
    modifiedAt: str | None = None
    createdAt: str | None = None


class ListFirewallRulesOutput(ActionOutput):
    count: int | None = None
    firewall_rules: list[FirewallRule] | None = None


class RuleConditionItem(ActionOutput):
    """Single rule condition (SDK requires typed output, not raw list)."""

    attributeName: str | None = None
    # API returns strings, booleans, or numbers; SOAR manifest only allows Optional[T].
    attributeValue: str | None = None
    attributeOperator: str | None = None


class RuleSettingItem(ActionOutput):
    """Single rule setting (SDK requires typed output, not raw list)."""

    settingName: str | None = None
    settingValue: str | None = None


class CreateRuleOutput(ActionOutput):
    """Response from Create Rule API (POST policies/v2/rules)."""

    organizationId: int | None = None
    ruleId: int | None = None
    ruleName: str | None = None
    ruleDescription: str | None = None
    ruleAction: str | None = None
    rulePriority: int | None = None
    ruleIsDefault: bool | None = None
    ruleIsEnabled: bool | None = None
    ruleConditions: list[RuleConditionItem] | None = None
    ruleSettings: list[RuleSettingItem] | None = None
    modifiedBy: str | None = None
    modifiedAt: str | None = None
    createdAt: str | None = None


class NetworkTunnelGroupHubStatus(ActionOutput):
    """Hub status from API. Required per schema: time, status."""

    time: str
    status: str


class NetworkTunnelGroupHub(ActionOutput):
    """Single hub entry in a network tunnel group (SDK requires typed output, not raw list)."""

    id: int | None = None
    name: str | None = None
    status: NetworkTunnelGroupHubStatus | None = None  # API returns object, not string


class NetworkTunnelGroupRouting(ActionOutput):
    """Routing config for a network tunnel group (SDK requires typed output, not raw dict)."""

    type: str | None = None


class NetworkTunnelGroup(ActionOutput):
    """Network Tunnel Group from List Network Tunnel Groups API (deployments/v2/networktunnelgroups)."""

    id: int | None = None
    name: str | None = None
    organizationId: int | None = None
    deviceType: str | None = None
    region: str | None = None
    status: str | None = None
    hubs: list[NetworkTunnelGroupHub] | None = None
    routing: NetworkTunnelGroupRouting | None = None
    createdAt: str | None = None
    modifiedAt: str | None = None


class ListNetworkTunnelGroupsOutput(ActionOutput):
    data: list[NetworkTunnelGroup] | None = None
    offset: int | None = None
    limit: int | None = None
    total: int | None = None


class GetNetworkTunnelGroupOutput(ActionOutput):
    """Response from Get Network Tunnel Group API (GET deployments/v2/networktunnelgroups/{id}). Same shape as NetworkTunnelGroup."""

    id: int | None = None
    name: str | None = None
    organizationId: int | None = None
    deviceType: str | None = None
    region: str | None = None
    status: str | None = None
    hubs: list[NetworkTunnelGroupHub] | None = None
    routing: NetworkTunnelGroupRouting | None = None
    createdAt: str | None = None
    modifiedAt: str | None = None


class ResourceConnector(ActionOutput):
    """Resource Connector from List Connectors API (deployments/v2/connectorAgents)."""

    id: int | None = None
    groupId: int | None = None
    instanceId: str | None = None
    confirmed: bool | None = None
    enabled: bool | None = None
    version: str | None = None
    sha1: str | None = None
    hostname: str | None = None
    originIpAddress: str | None = None
    baseVersion: str | None = None
    isLatestBaseVersion: bool | None = None
    upgradeStatus: str | None = None
    status: str | None = None
    statusUpdatedAt: str | None = None
    controlStatusUpdatedAt: str | None = None
    revoked_at: str | None = None
    createdAt: str | None = None
    modifiedAt: str | None = None


class ListResourceConnectorsOutput(ActionOutput):
    data: list[ResourceConnector] | None = None
    offset: int | None = None
    limit: int | None = None
    total: int | None = None


class SWGOverrideSettingItem(ActionOutput):
    """SWG override setting for one device from List SWG Override Device Settings API."""

    originId: int
    name: str
    value: str
    modifiedAt: str


class ListSWGOverrideDeviceSettingsOutput(ActionOutput):
    """Response from List SWG Override Device Settings (POST deployments/v2/deviceSettings/SWGEnabled/list)."""

    settings: list[SWGOverrideSettingItem]


class SWGDeviceSettingItem(ActionOutput):
    """Per-device status from Set SWG Override Device Settings API."""

    originId: int
    code: int
    message: str


class SetSWGOverrideDeviceSettingsOutput(ActionOutput):
    """Response from Set SWG Override Device Settings (POST deployments/v2/deviceSettings/SWGEnabled/set)."""

    totalCount: int
    successCount: int
    failCount: int
    items: list[SWGDeviceSettingItem]
    value: str


class DeleteSWGOverrideDeviceSettingsOutput(ActionOutput):
    """Response from Delete SWG Override Device Settings (POST deployments/v2/deviceSettings/SWGEnabled/remove)."""

    status: str | None = None
