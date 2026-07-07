CONNECT_TIMEOUT = 15
READ_TIMEOUT = 60
TIMEOUT = (CONNECT_TIMEOUT, READ_TIMEOUT)
OBSERVABLE_TYPES_IDENTIFIERS = [
    "ip", "ipv6", "device", "user", "domain", "sha256", "md5", "sha1", "url",
    "pki_serial", "email", "imei", "imsi", "amp_computer_guid", "hostname",
    "mac_address", "file_name", "file_path", "odns_identity",
    "odns_identity_label", "email_messageid", "email_subject", "cisco_mid",
    "mutex", "certificate_common_name", "certificate_issuer",
    "certificate_serial", "orbital_node_id", "process_name", "registry_key",
    "registry_name", "registry_path", "user_agent",
]

ADDON_NAME = "TA-cisco-threat-response"
SOURCE_TYPE = "cisco:tr:data"
