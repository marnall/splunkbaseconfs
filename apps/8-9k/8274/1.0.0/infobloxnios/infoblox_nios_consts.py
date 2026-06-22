# File: infoblox_nios_consts.py
#
# Copyright 2025 Infoblox Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
#
# Json keys specific to the app's config parameters
CONFIG_USERNAME = "username"
CONFIG_PASSWORD = "password"  # pragma: allowlist secret
CONFIG_URL = "url"
CONFIG_VERIFY_SERVER_CERT = "verify_server_cert"

# Json keys specific to the action's input parameters and the output result
JSON_CONTENT_TYPE = "Content-Type"

# Response status codes
REST_RESP_SUCCESS = 200
REST_RESP_CREATE_SUCCESS = 201

# Error messages
TEST_CONN_FAILED = "Connectivity test failed"
ERROR_API_UNSUPPORTED_METHOD = "Unsupported method {method}"
EXCEPTION_OCCURRED = "Exception occurred"
UNKNOWN_ERROR_MSG = "Unknown error occurred."
ERROR_REQUIRED_SUBSTITUTE_NAME = "Substitute name is required when rule type is 'Substitute (domain name)'"
ERROR_COMMENT_LENGTH_EXCEEDED = "Comment length cannot exceed 256 characters"
ERROR_JSON_PARSE = "Failed to parse JSON for additional parameters"
ERROR_INVALID_OBJECT_TYPE = "Invalid object type. Supported types: 'Domain Name', 'IP address', 'Client IP Address'"
ERROR_INVALID_ENUM_PARAM = "Invalid value for parameter '{key}'. Valid values are: {valid_values}"
ERROR_NAME_FORMAT = "Failed to format name parameter with RP zone"
ERROR_CREATE_RPZ_CNAME_RULE = "Error occurred while creating RPZ CNAME rule"
ERROR_CREATE_RPZ_TXT_RULE = "Error occurred while creating RPZ TXT rule"
ERROR_UPDATE_RPZ_CNAME_RULE = "Error occurred while updating RPZ CNAME rule"
ERROR_INVALID_REFERENCE_ID = "Invalid reference ID format"
ERROR_CREATE_RPZ_A_RULE = "Error occurred while creating RPZ A rule"
ERROR_CREATE_RPZ_AAAA_RULE = "Error occurred while creating RPZ AAAA rule"
ERROR_INVALID_IPV4 = "Invalid IPv4 address format"
ERROR_INVALID_IPV6 = "Invalid IPv6 address format"
ERROR_CREATE_RPZ_MX_RULE = "Error occurred while creating RPZ MX rule"
ERROR_PREFERENCE_VALUE = "Preference value must be between 0 and 65535"
ERROR_ORDER_VALUE = "Order value must be between 0 and 65535"
ERROR_CREATE_RPZ_PTR_RULE = "Error occurred while creating RPZ PTR rule"
ERROR_BOTH_IP_ADDRESSES = "Cannot provide both IPv4 and IPv6 addresses at the same time"
ERROR_CREATE_HOST_RECORD = "Error creating Host Record"
ERROR_HOST_RECORD_INVALID_JSON = "Invalid JSON in {field} parameter"
ERROR_HOST_RECORD_MISSING_IP = "At least one IPv4 or IPv6 address must be provided"
ERROR_HOST_RECORD_INVALID_IPV4 = "Invalid IPv4 address format: {ipv4}"
ERROR_HOST_RECORD_INVALID_IPV6 = "Invalid IPv6 address format: {ipv6}"
ERROR_HOST_RECORD_INVALID_MAC = "Invalid MAC address format: {mac}"
ERROR_HOST_RECORD_INVALID_EXTATTRS = "Invalid Extended Attributes format. Use key=value format separated by commas"
ERROR_DELETE_RPZ_RULE = "Error deleting RPZ Rule"
ERROR_DELETE_RPZ = "Error deleting Response Policy Zone"
CREATE_RPZ_ERROR_MESSAGE = "Error creating Response Policy Zone"
CREATE_RPZ_INVALID_JSON_ERROR = "Invalid JSON in {field} parameter"
ERROR_INVALID_INT_PARAM = "Please provide a valid integer value in the '{key}' parameter"
ERROR_ZERO_INT_PARAM = "Please provide a non-zero positive integer value in the '{key}' parameter"
ERROR_NEG_INT_PARAM = "Please provide a positive integer value in the '{key}' parameter"
SEARCH_RPZ_RULE_ERROR_MESSAGE = "Error occurred while searching for RPZ rules"
GET_RPZ_ERROR_MESSAGE = "Error occurred while fetching response policy zones"

# Endpoints
BASE_ENDPOINT = "/wapi/v2.13.1"
TEST_SCHEMA_ENDPOINT = "/?_schema"
RPZ_CNAME_DOMAIN_ENDPOINT = "/record:rpz:cname"
RPZ_CNAME_IP_ENDPOINT = "/record:rpz:cname:ipaddress"
RPZ_CNAME_CLIENT_IP_ENDPOINT = "/record:rpz:cname:clientipaddress"
RPZ_TXT_ENDPOINT = "/record:rpz:txt"
RPZ_PTR_ENDPOINT = "/record:rpz:ptr"
RPZ_MX_ENDPOINT = "/record:rpz:mx"
CREATE_RPZ_SRV_RULE_ENDPOINT = "/record:rpz:srv"
CREATE_RPZ_NAPTR_RULE_ENDPOINT = "/record:rpz:naptr"
DHCP_LEASE_ENDPOINT = "/lease"
LIST_HOST_INFO_ENDPOINT = "/record:host"
LIST_NETWORK_INFO_ENDPOINT = "/network"
RPZ_A_DOMAIN_ENDPOINT = "/record:rpz:a"
RPZ_A_IP_ENDPOINT = "/record:rpz:a:ipaddress"
RPZ_AAAA_DOMAIN_ENDPOINT = "/record:rpz:aaaa"
RPZ_AAAA_IP_ENDPOINT = "/record:rpz:aaaa:ipaddress"
IP_LOOKUP_ENDPOINT_IPV4 = "/ipv4address"
IP_LOOKUP_ENDPOINT_IPV6 = "/ipv6address"
CREATE_HOST_RECORD_ENDPOINT = "/record:host"
DELETE_RPZ_ENDPOINT = "/{reference_id}"
CREATE_RPZ_ENDPOINT = "/zone_rp"
RPZ_ENDPOINT = "/zone_rp"

# Return fields parameter for API calls
RETURN_FIELDS_PARAM_IP = "_return_fields=canonical,comment,disable,extattrs,name,rp_zone,ttl,use_ttl,view,zone,is_ipv4"
RETURN_FIELDS_PARAM = "_return_fields=canonical,comment,disable,extattrs,name,rp_zone,ttl,use_ttl,view,zone"
RETURN_FIELDS_PARAM_RPZ_TXT = "_return_fields=comment,disable,extattrs,name,rp_zone,text,ttl,use_ttl,view,zone"
RETURN_FIELDS_PARAM_RPZ_PTR = "_return_fields=comment,disable,extattrs,ipv4addr,ipv6addr,name,ptrdname,rp_zone,ttl,use_ttl,view,zone"
RETURN_FIELDS_PARAM_RPZ_MX = "_return_fields=comment,disable,extattrs,mail_exchanger,name,preference,rp_zone,ttl,use_ttl,view,zone"
RETURN_FIELDS_PARAM_RPZ_A = "_return_fields=comment,disable,extattrs,ipv4addr,name,rp_zone,ttl,use_ttl,view,zone"
RETURN_FIELDS_PARAM_PRZ_AAAA = "_return_fields=comment,disable,extattrs,ipv6addr,name,rp_zone,ttl,use_ttl,view,zone"
IPV4_RETURN_FIELDS = "comment,conflict_types,dhcp_client_identifier,discover_now_status,discovered_data,extattrs,fingerprint,ip_address,is_conflict,is_invalid_mac,lease_state,mac_address,ms_ad_user_data,names,network,network_view,objects,reserved_port,status,types,usage,username"
IPV6_RETURN_FIELDS = "comment,conflict_types,discover_now_status,discovered_data,extattrs,fingerprint,ip_address,is_conflict,lease_state,ms_ad_user_data,names,network,network_view,objects,reserved_port,status,types,usage,duid"
CREATE_RPZ_NAPTR_RULE_RETURN_FIELDS = (
    "comment,disable,extattrs,flags,last_queried,name,order,preference,regexp,replacement,rp_zone,services,ttl,use_ttl,view,zone"
)
DHCP_LEASE_RETURN_FIELDS = "address,billing_class,binding_state,client_hostname,cltt,discovered_data,ends,fingerprint,hardware,ipv6_duid,ipv6_iaid,ipv6_preferred_lifetime,ipv6_prefix_bits,is_invalid_mac,ms_ad_user_data,network,network_view,never_ends,never_starts,next_binding_state,on_commit,on_expiry,on_release,option,protocol,remote_id,served_by,server_host_name,starts,tsfp,tstp,uid,username,variable"
LIST_HOST_INFO_RETURN_FIELDS = "aliases,allow_telnet,cli_credentials,cloud_info,comment,configure_for_dns,creation_time,ddns_protected,device_description,device_location,device_type,device_vendor,disable,disable_discovery,dns_aliases,dns_name,extattrs,ipv4addrs,ipv6addrs,last_queried,ms_ad_user_data,name,network_view,rrset_order,snmp3_credential,snmp_credential,ttl,use_cli_credentials,use_dns_ea_inheritance,use_snmp3_credential,use_snmp_credential,use_ttl,view,zone"
LIST_NETWORK_INFO_RETURN_FIELDS = "authority,bootfile,bootserver,cloud_info,comment,conflict_count,ddns_domainname,ddns_generate_hostname,ddns_server_always_updates,ddns_ttl,ddns_update_fixed_addresses,ddns_use_option81,deny_bootp,dhcp_utilization,dhcp_utilization_status,disable,discover_now_status,discovered_bgp_as,discovered_bridge_domain,discovered_tenant,discovered_vlan_id,discovered_vlan_name,discovered_vrf_description,discovered_vrf_name,discovered_vrf_rd,discovery_basic_poll_settings,discovery_blackout_setting,discovery_engine_type,dynamic_hosts,email_list,enable_ddns,enable_dhcp_thresholds,enable_discovery,enable_email_warnings,enable_ifmap_publishing,enable_pxe_lease_time,enable_snmp_warnings,endpoint_sources,extattrs,high_water_mark,high_water_mark_reset,ignore_dhcp_option_list_request,ignore_id,ignore_mac_addresses,ipam_email_addresses,ipam_threshold_settings,ipam_trap_settings,ipv4addr,last_rir_registration_update_sent,last_rir_registration_update_status,lease_scavenge_time,logic_filter_rules,low_water_mark,low_water_mark_reset,members,mgm_private,mgm_private_overridable,ms_ad_user_data,netmask,network,network_container,network_view,nextserver,options,port_control_blackout_setting,pxe_lease_time,recycle_leases,rir,rir_organization,rir_registration_status,same_port_control_discovery_blackout,static_hosts,subscribe_settings,total_hosts,unmanaged,unmanaged_count,update_dns_on_lease_renewal,utilization"
CREATE_RPZ_SRV_RULE_RETURN_FIELDS = "comment,disable,extattrs,name,port,priority,rp_zone,target,ttl,use_ttl,view,weight,zone"
HOST_RECORD_RETURN_FIELDS = "aliases,allow_telnet,cli_credentials,cloud_info,comment,configure_for_dns,creation_time,ddns_protected,device_description,device_location,device_type,device_vendor,disable,disable_discovery,dns_aliases,dns_name,extattrs,ipv4addrs,ipv6addrs,comment,last_queried,ms_ad_user_data,name,network_view,rrset_order,snmp3_credential,snmp_credential,ttl,use_cli_credentials,use_dns_ea_inheritance,use_snmp3_credential,use_snmp_credential,use_ttl,view,zone"
RPZ_RETURN_FIELDS = (
    "address,comment,disable,display_domain,dns_soa_email,extattrs,external_primaries,"
    "external_secondaries,fireeye_rule_mapping,fqdn,grid_primary,grid_secondaries,locked,"
    "locked_by,log_rpz,mask_prefix,member_soa_mnames,member_soa_serials,network_view,ns_group,"
    "parent,prefix,primary_type,record_name_policy,rpz_drop_ip_rule_enabled,"
    "rpz_drop_ip_rule_min_prefix_length_ipv4,rpz_drop_ip_rule_min_prefix_length_ipv6,"
    "rpz_last_updated_time,rpz_policy,rpz_priority,rpz_priority_end,rpz_severity,"
    "rpz_type,soa_default_ttl,soa_email,soa_expire,soa_negative_ttl,soa_refresh,soa_retry,"
    "soa_serial_number,substitute_name,use_external_primary,use_grid_zone_timer,use_log_rpz,"
    "use_record_name_policy,use_rpz_drop_ip_rule,use_soa_email,view"
)

# Rule type to canonical mappings
RULE_TYPE_PASSTHRU = "Passthru"
RULE_TYPE_BLOCK_NO_DOMAIN = "Block (No such domain)"
RULE_TYPE_BLOCK_NO_DATA = "Block (No data)"
RULE_TYPE_SUBSTITUTE = "Substitute (domain name)"

# Canonical values for rule types
CANONICAL_PASSTHRU = "rpz-passthru"
CANONICAL_BLOCK_NO_DOMAIN = ""
CANONICAL_BLOCK_NO_DATA = "*"

# Object types
OBJECT_TYPE_DOMAIN = "Domain Name"
OBJECT_TYPE_IP = "IP address"
OBJECT_TYPE_CLIENT_IP = "Client IP Address"

# Success messages
SUCCESS_CREATE_RPZ_CNAME_RULE = "Successfully created RPZ CNAME rule"
SUCCESS_CREATE_RPZ_A_RULE = "Successfully created RPZ A rule"
SUCCESS_CREATE_RPZ_AAAA_RULE = "Successfully created RPZ AAAA rule"
SUCCESS_UPDATE_RPZ_CNAME_RULE = "Successfully updated RPZ CNAME rule"
SUCCESS_CREATE_RPZ_PTR_RULE = "Successfully created RPZ PTR rule"
SUCCESS_CREATE_RPZ_TXT_RULE = "Successfully created RPZ TXT rule"
TEST_CONNECTIVITY_MESSAGE = "Checking connection to Infoblox NIOS"
TEST_CONN_SUCCESS = "Connectivity test succeeded"
SUCCESS_CREATE_RPZ_MX_RULE = "Successfully created RPZ MX rule"
COMMON_SUCCESS_MESSAGE = "Successfully {action_verb} {count} {object_type}"
DHCP_LEASE_SUCCESS_MESSAGE = "Successfully retrieved {0} DHCP lease record(s)"
IP_LOOKUP_SUCCESS_MESSAGE = "Successfully retrieved {0} IP record(s)"
LIST_HOST_INFO_SUCCESS_MESSAGE = "Successfully retrieved {count} host record(s)"
LIST_NETWORK_INFO_SUCCESS_MESSAGE = "Successfully retrieved {count} network record(s)"
CREATE_HOST_RECORD_SUCCESS_MESSAGE = "Successfully created Host Record. Reference ID: {reference_id}"
DELETE_RPZ_RULE_SUCCESS_MESSAGE = "Successfully deleted RPZ Rule. Reference ID: {reference_id}"
DELETE_RPZ_SUCCESS_MESSAGE = "Successfully deleted Response Policy Zone. Reference ID: {reference_id}"
CREATE_RPZ_SUCCESS_MESSAGE = "Successfully created Response Policy Zone. Reference ID: {reference_id}"
SEARCH_RPZ_RULE_SUCCESS_MESSAGE = "Successfully retrieved {count} RPZ rule(s)"
GET_RPZ_SUCCESS_MESSAGE = "Successfully retrieved {count} response policy zone(s)"

# Start Message
IP_LOOKUP_START_MESSAGE = "Starting IP Lookup action"
DHCP_LEASE_START_MESSAGE = "Starting DHCP Lease Lookup action"
DELETE_RPZ_RULE_START_MESSAGE = "Starting Delete RPZ Rule action"
CREATE_HOST_RECORD_START_MESSAGE = "Starting Create Host Record action"
DELETE_RPZ_START_MESSAGE = "Starting Delete Response Policy Zone action"
CREATE_RPZ_START_MESSAGE = "Starting Create Response Policy Zone action"
GET_RPZ_START_MESSAGE = "Starting to retrieve Response Policy Zones"
SEARCH_RPZ_RULE_START_MESSAGE = "Starting to search for RPZ Rules"

# IP Lookup related constants
DEFAULT_LIMIT = 100

# Status options
IP_LOOKUP_STATUS_VALUES = ["ALL", "ACTIVE", "UNUSED", "USED"]

# Pagination constants
DEFAULT_MAX_RESULTS = 1000  # Default maximum results if no limit specified
DEFAULT_PAGE_SIZE = 1000  # Default page size for pagination

# Execution start message template
EXECUTION_START_MSG = "Starting execution of action: {}"

# Common validation constants (reusable across actions)
MAX_PORT_VALUE = 65535  # Standard networking port range maximum
# RPZ additional parameters supported fields
RPZ_SUPPORTED_ADDITIONAL_FIELDS = frozenset(["disable", "extattrs", "ttl", "use_ttl", "view"])

# Protocol options for DHCP Lease Lookup
PROTOCOL_BOTH = "BOTH"
PROTOCOL_IPV4 = "IPV4"
PROTOCOL_IPV6 = "IPV6"

# List Host Info related constants
LIST_HOST_INFO_DEFAULT_LIMIT = 100
# List Network Info related constants
LIST_NETWORK_INFO_DEFAULT_LIMIT = 100

# Progress message
CREATE_HOST_RECORD_PROGRESS_MESSAGE = "Creating Host Record with name: {name}"
DELETE_RPZ_RULE_PROGRESS_MESSAGE = "Deleting RPZ Rule with reference: {ref}"
DELETE_RPZ_PROGRESS_MESSAGE = "Deleting Response Policy Zone with reference ID: {reference_id}"
CREATE_RPZ_PROGRESS_MESSAGE = "Creating Response Policy Zone with FQDN: {fqdn}"
GET_RPZ_PROGRESS_MESSAGE = "Retrieving Response Policy Zone with FQDN: {fqdn}"
SEARCH_RPZ_RULE_PROGRESS_MESSAGE = "Searching for RPZ Rule with name: {name}"

# RPZ policy values
RPZ_POLICY_VALUES = ["DISABLED", "GIVEN", "NODATA", "NXDOMAIN", "PASSTHRU", "SUBSTITUTE"]
RPZ_SEVERITY_VALUES = ["CRITICAL", "MAJOR", "WARNING", "INFORMATIONAL"]
RPZ_TYPE_VALUES = ["FEED", "FIREEYE", "LOCAL"]
# RPZ Rule constants
RPZ_RULE_RETURN_FIELDS = "canonical,comment,disable,extattrs,name,rp_zone,ttl,use_ttl,view,zone"
