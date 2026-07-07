# Upgradation constants
inputs_conf_file = "inputs"
settings_conf_file = "ta_cloudknox_settings"
inputs_upgradation_stanza = "inputs_upgraded"

# Validation constants
VALID_AUTH_SYSTEMS = ["AWS", "AZURE", "GCP", "VCENTER"]

# API Endpoints
AUTH_ENDPOINT = "/api/v2/service-account/authenticate"
LIST_AUTH_SYSTEMS = "/api/v2/organization/authorization-systems"
PAR_DATA_ENDPOINT = "/api/v3/privilege-analytics/finding/data"
PAR_DATA_SUMMARY_ENDPOINT = "/api/v3/privilege-analytics/finding/summary"
AUDITLOG_DATA_ENDPOINT = "/api/v2/organization/activities"
ALERT_DATA_ENDPOINT = "/api/v2/organization/alerts/{}-based"

# Global variables
AUTH_SYS_CHUNK_SIZE = 100
GLOBAL_RETRY = 1
PAGE_SIZE = 500
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
UTC_FORMAT = r"""%Y-%m-%dT%H:%M:%SZ"""
START_DATETIME_LAST_DAYS = 90
CLOUDKNOX_SOURCE = "cloudknox"
CLOUDKNOX_AUDITLOGS_INPUT_SOURCE = "cloudknox_auditlogs"
CLOUDKNOX_ALERTS_INPUT_SOURCE = "cloudknox_alerts"
SECONDS_OF_HR = 60 * 60
SECONDS_OF_FIVE_MIN = 60 * 5

# CloudKnox token lock timeout in seconds
LOCK_TIMEOUT = 50
LOCK_POLLING_INTERVAL = 10

# Declare Source Type
CATEGORIES = {"AWS": [
    {
        "name": "REPORT_SUMMARY",
        "sourcetype": "cloudknox:aws:summary",
        "summaryType": "SUMMARY_DATA"
    },
    {
        "name": "IDENTITIES_INACTIVE",
        "sourcetype": "cloudknox:aws:identities_inactive",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"],
        "summaryDataType": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"]
    },
    {
        "name": "GROUPS_INACTIVE",
        "sourcetype": "cloudknox:aws:groups_inactive",
        "subCategory": ["GROUPS"],
        "summaryDataType": ["GROUPS"]
    },
    {
        "name": "IDENTITIES_SUPER",
        "sourcetype": "cloudknox:aws:identities_super",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"],
        "summaryDataType": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"]
    },
    {
        "name": "IDENTITIES_ACTIVE_OVER_PROVISIONED",
        "sourcetype": "cloudknox:aws:identities_active_over_provisioned",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"],
        "summaryDataType": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"]
    },
    {
        "name": "PCI_DISTRIBUTION",
        "sourcetype": "cloudknox:aws:pci_distribution",
        "subCategory": ["DISTRIBUTION"]
    },
    {
        "name": "PRIVILEGE_ESCALATION",
        "sourcetype": "cloudknox:aws:privilege_escalation",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES"],
        "summaryDataType": ["USERS", "AWS_ROLES", "AWS_RESOURCES"]
    },
    {
        "name": "S3_BUCKET_ENCRYPTION",
        "sourcetype": "cloudknox:aws:s3_bucket_encryption",
        "subCategory": ["UNENCRYPTED", "SSE_S3"],
        "summaryDataType": ["UNENCRYPTED", "SSE_S3"]
    },
    {
        "name": "S3_BUCKET_ACCESS",
        "sourcetype": "cloudknox:aws:s3_buckets_accessible_externally",
        "subCategory": ["S3_BUCKETS"],
        "summaryDataType": ["S3_BUCKETS"]
    },
    {
        "name": "EC2_S3_BUCKET_ACCESSIBILITY",
        "sourcetype": "cloudknox:aws:ec2_s3_buckets_accessibility",
        "subCategory": ["INSTANCES"],
        "summaryDataType": ["INSTANCES"]
    },
    {
        "name": "OPEN_SECURITY_GROUPS",
        "sourcetype": "cloudknox:aws:open_security_groups",
        "subCategory": ["SECURITY_GROUPS"],
        "summaryDataType": ["SECURITY_GROUPS"]
    },
    {
        "name": "SOD_SECURITY_TOOLS",
        "sourcetype": "cloudknox:aws:identities_that_can_administer_security_tools",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"],
        "summaryDataType": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"]
    },
    {
        "name": "SOD_SECRET_INFORMATION",
        "sourcetype": "cloudknox:aws:identities_that_can_access_secret_information",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"],
        "summaryDataType": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS"]
    },
    {
        "name": "CROSS_ACCOUNT_ACCESS",
        "sourcetype": "cloudknox:aws:cross_account_access",
        "subCategory": ["EXTERNAL_ACCOUNTS", "ROLES"],
        "summaryDataType": ["ROLES"]
    },
    {
        "name": "MFA_ENFORCEMENT",
        "sourcetype": "cloudknox:aws:hygiene_mfa_enforcement",
        "subCategory": ["USERS"],
        "summaryDataType": ["USERS"]
    },
    {
        "name": "IAM_ACCESS_KEY_AGE",
        "sourcetype": "cloudknox:aws:hygiene_iam_access_key_Age",
        "subCategory": ["KEYS"],
        "summaryDataType": ["KEYS"]
    },
    {
        "name": "IAM_ACCESS_KEY_USAGE",
        "sourcetype": "cloudknox:aws:hygiene:unused_iam_access_keys",
        "subCategory": ["KEYS"],
        "summaryDataType": ["KEYS"]
    },
    {
        "name": "EXCLUDED_ENTITIES",
        "sourcetype": "cloudknox:aws:excluded_entities",
        "subCategory": ["USERS", "AWS_ROLES", "AWS_RESOURCES", "SERVERLESS", "GROUPS",
                        "AWS_SECURITY_GROUPS", "S3_BUCKETS"]
    }],
    "AZURE": [
    {
        "name": "IDENTITIES_INACTIVE",
        "sourcetype": "cloudknox:azure:identities_inactive",
        "subCategory": ["USERS", "AZURE_APPS", "SERVERLESS"],
        "summaryDataType": ["USERS", "AZURE_APPS", "SERVERLESS"]
    },
    {
        "name": "GROUPS_INACTIVE",
        "sourcetype": "cloudknox:azure:groups_inactive",
        "subCategory": ["GROUPS"],
        "summaryDataType": ["GROUPS"]
    },
    {
        "name": "IDENTITIES_SUPER",
        "sourcetype": "cloudknox:azure:identities_super",
        "subCategory": ["USERS", "AZURE_APPS", "SERVERLESS"],
        "summaryDataType": ["USERS", "AZURE_APPS", "SERVERLESS"]
    },
    {
        "name": "IDENTITIES_ACTIVE_OVER_PROVISIONED",
        "sourcetype": "cloudknox:azure:identities_active_over_provisioned",
        "subCategory": ["USERS", "AZURE_APPS", "SERVERLESS"],
        "summaryDataType": ["USERS", "AZURE_APPS", "SERVERLESS"]
    },
    {
        "name": "AZURE_BLOB_STORAGE_ENCRYPTION",
        "sourcetype": "cloudknox:azure:blob_storage_account_encryption",
        "subCategory": ["MICROSOFT_MANAGED_KEYS"],
        "summaryDataType": ["MICROSOFT_MANAGED_KEYS"]
    },
    {
        "name": "AZURE_BLOB_STORAGE_ACCESS",
        "sourcetype": "cloudknox:azure:blob_storage_containers_accessible_externally",
        "subCategory": ["CONTAINERS"],
        "summaryDataType": ["CONTAINERS"]
    },
    {
        "name": "OPEN_SECURITY_GROUPS",
        "sourcetype": "cloudknox:azure:open_network_security_groups",
        "subCategory": ["AZURE_SECURITY_GROUPS"],
        "summaryDataType": ["AZURE_SECURITY_GROUPS"]
    },
    {
        "name": "PCI_DISTRIBUTION",
        "sourcetype": "cloudknox:azure:pci_distribution",
        "subCategory": ["DISTRIBUTION"]
    },
    {
        "name": "EXCLUDED_ENTITIES",
        "sourcetype": "cloudknox:azure:excluded_entities",
        "subCategory": ["USERS", "AZURE_APPS", "SERVERLESS", "GROUPS",
                        "AZURE_STORAGE_ACCOUNTS", "AZURE_BLOB_CONTAINERS", "AZURE_SECURITY_GROUPS"]
    }],
    "GCP": [
    {
        "name": "IDENTITIES_INACTIVE",
        "sourcetype": "cloudknox:gcp:identities_inactive",
        "subCategory": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS"],
        "summaryDataType": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS"]
    },
    {
        "name": "GROUPS_INACTIVE",
        "sourcetype": "cloudknox:gcp:groups_inactive",
        "subCategory": ["GROUPS"],
        "summaryDataType": ["GROUPS"]
    },
    {
        "name": "IDENTITIES_SUPER",
        "sourcetype": "cloudknox:gcp:identities_super",
        "subCategory": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS"],
        "summaryDataType": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS"]
    },
    {
        "name": "IDENTITIES_ACTIVE_OVER_PROVISIONED",
        "sourcetype": "cloudknox:gcp:identities_active_over_provisioned",
        "subCategory": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS"],
        "summaryDataType": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS"]
    },
    {
        "name": "PCI_DISTRIBUTION",
        "sourcetype": "cloudknox:gcp:pci_distribution",
        "subCategory": ["DISTRIBUTION"]
    },
    {
        "name": "PRIVILEGE_ESCALATION",
        "sourcetype": "cloudknox:gcp:privilege_escalation",
        "subCategory": ["USERS", "GCP_SVC_ACCTS"],
        "summaryDataType": ["USERS", "GCP_SVC_ACCTS"]
    },
    {
        "name": "GCP_BUCKET_ENCRYPTION",
        "sourcetype": "cloudknox:gcp:storage_bucket_encryption",
        "subCategory": ["GCP_STORAGE_BUCKETS"],
        "summaryDataType": ["GCP_STORAGE_BUCKETS"]
    },
    {
        "name": "GCP_BUCKET_ACCESS",
        "sourcetype": "cloudknox:gcp:storage_buckets_accessible_externally",
        "subCategory": ["GCP_STORAGE_BUCKETS"],
        "summaryDataType": ["GCP_STORAGE_BUCKETS"]
    },
    {
        "name": "EXCLUDED_ENTITIES",
        "sourcetype": "cloudknox:gcp:excluded_entities",
        "subCategory": ["USERS", "GCP_SVC_ACCTS", "SERVERLESS", "GROUPS", "GCP_STORAGE_BUCKETS"]
    }],
    "VCENTER": [
    {
        "name": "IDENTITIES_INACTIVE",
        "sourcetype": "cloudknox:vcenter:identities_inactive",
        "subCategory": ["USERS"],
        "summaryDataType": ["USERS"]
    },
    {
        "name": "GROUPS_INACTIVE",
        "sourcetype": "cloudknox:vcenter:groups_inactive",
        "subCategory": ["GROUPS"],
        "summaryDataType": ["GROUPS"]
    },
    {
        "name": "IDENTITIES_SUPER",
        "sourcetype": "cloudknox:vcenter:identities_super",
        "subCategory": ["USERS"],
        "summaryDataType": ["USERS"]
    },
    {
        "name": "IDENTITIES_ACTIVE_OVER_PROVISIONED",
        "sourcetype": "cloudknox:vcenter:identities_active_over_provisioned",
        "subCategory": ["USERS"],
        "summaryDataType": ["USERS"]
    },
    {
        "name": "PCI_DISTRIBUTION",
        "sourcetype": "cloudknox:vcenter:pci_distribution",
        "subCategory": ["DISTRIBUTION"]
    },
    {
        "name": "EXCLUDED_ENTITIES",
        "sourcetype": "cloudknox:vcenter:excluded_entities",
        "subCategory": ["USERS", "GROUPS"]
    }]
}

# HTTP request payload for auditlogs
AUDIT_PAYLOAD = {}

# HTTP request payload for alerts
ALERT_PAYLOAD = {}
