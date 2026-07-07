# ${copyright}
"""
Constants for Cisco Enterprise Networks import flow=
"""

CATALYST_CENTER_SANDBOX_TITLE = "Catalyst Center Sandbox - {account_name}"
CATALYST_CENTER_SITE_TEMPLATE = "Catalyst Center Site"
CATALYST_CENTER_SITE_TEMPLATE_ID = "da-itsi-cp-enterprise-networking-catalyst-center-site"
CATALYST_CENTER_SPL = """
search `itsi_cp_catalyst_center_index` sourcetype="cisco:dnac:site:topology"
  cisco_catalyst_host={cisco_catalyst_host}
| rename id AS siteId, name AS siteName,
  type AS siteType, nameHierarchy AS siteHierarchy
| table cisco_catalyst_host, siteId, siteName, siteType, parentId, siteHierarchy
"""
COMPOSITE_ID_LENGTH = 6

MERAKI_NETWORK_TEMPLATE = "Meraki Network"
MERAKI_NETWORK_TEMPLATE_ID = "da-itsi-cp-enterprise-networking-meraki-network"
MERAKI_NETWORK_SPL = """
search `meraki_index` sourcetype="meraki:organizations"
| dedup id
| rename cloud.region.name AS ServiceTitle,
 cloud.region.host.name AS ServiceDependency, id AS OrganizationID
| table ServiceTitle ServiceDependency OrganizationID NetworkTag ServiceTemplate
| append
    [| search `meraki_index` sourcetype="meraki:organizations"
    | dedup id
    | rename cloud.region.host.name AS ServiceTitle,
     name as ServiceDependency, id AS OrganizationID
    | table ServiceTitle ServiceDependency OrganizationID ServiceTemplate
    ]
| append
    [| search `meraki_index` sourcetype="meraki:organizationsnetworks"
    | dedup id
    | rename tags{{}} AS NetworkTag, organizationId AS OrganizationID
    | mvexpand NetworkTag
    | eval NetworkTag = if(NetworkTag = "", "Untagged", NetworkTag),
     ServiceDependency = NetworkTag
    | join OrganizationID
        [| search `meraki_index` sourcetype="meraki:organizations"
        | dedup id
        | rename name as ServiceTitle, organizationId AS OrganizationID
        | table OrganizationID ServiceTitle
            ]
    | table ServiceTitle ServiceDependency OrganizationID ServiceTemplate
    | dedup ServiceTitle ServiceDependency OrganizationID
        ]
| append
    [| search `meraki_index` sourcetype="meraki:organizationsnetworks"
    | dedup id
    | rename tags{{}} AS NetworkTag, organizationId AS OrganizationID
    | mvexpand NetworkTag
    | eval NetworkTag = if(NetworkTag = "", "Untagged", NetworkTag),
     ServiceTitle = NetworkTag
    | eval ServiceTemplate="Meraki Network"
    | table ServiceTitle OrganizationID NetworkTag ServiceTemplate
    | dedup ServiceTitle OrganizationID NetworkTag ]
| search OrganizationID="{organization_id}"
"""
MERAKI_ORGANIZATION_SPL = """
search `meraki_index` sourcetype="meraki:organizations" id="{organization_id}"
| dedup id
| rename cloud.region.name AS region, cloud.region.host.name AS host
| table id, name, region, host
"""
