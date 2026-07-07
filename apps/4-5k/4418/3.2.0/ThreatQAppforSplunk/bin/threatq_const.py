import threatquotient_app_declare
import os

VERIFY_SSL = True           # Default: True. Change this to False if certificate validation is not required.
VERIFY_SSL_KVSTORE = False  # Default: False. This will be used for internal calls.
VERIFY_SSL_FORWARDER = False

CERT_FILE_LOC = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', threatquotient_app_declare.ta_name, 'local', 'cac_certs', 'custom_cert.pem')
KEY_FILE_LOC = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', threatquotient_app_declare.ta_name, 'local', 'cac_certs', 'custom_key.pem')

DATAMODEL_AND_ITS_SEARCH_MAP = {
    "network_traffic": ["| datamodel Network_Traffic All_Traffic search"],
    "malware": ["| datamodel Malware Malware_Attacks search"],
    "incident_management": ["| datamodel Incident_Management Notable_Events search", "| datamodel Incident_Management Suppressed_Notable_Events search", "| datamodel Incident_Management Suppression_Audit_Expired search", "| datamodel Incident_Management Suppression_Audit search"],
    "intrusion_detection": ["| datamodel Intrusion_Detection IDS_Attacks search"],
    "authentication": ["| datamodel Authentication Authentication search"],
    "certificates": ["| datamodel Certificates SSL search"],
    "endpoint": ["| datamodel Endpoint Filesystem search", "| datamodel Endpoint Services search", "| datamodel Endpoint Processes search"],
    "email": ["| datamodel Email All_Email search"],
    "compute_inventory": ["| datamodel Compute_Inventory User search"],
    "network_resolution": ["| datamodel Network_Resolution DNS search"],
    "updates": ["| datamodel Updates Updates search"],
    "web": ["| datamodel Web Web search"]
}

DEFAULT_GROUP_BY_FIELDS_OF_DATAMODEL = {
    "threatq_match_indicators_network_traffic": "All_Traffic.src",
    "threatq_match_indicators_malware" : "Malware_Attacks.file_name, Malware_Attacks.file_hash, Malware_Attacks.signature, Malware_Attacks.sender, Malware_Attacks.src, Malware_Attacks.user",
    "threatq_match_indicators_incident_management_notable_events": "Notable_Events.src",
    "threatq_match_indicators_incident_management_suppressed_notable_events": "Suppressed_Notable_Events.src",
    "threatq_match_indicators_incident_management_suppression_audit_expired": "Notable_Event_Suppressions.Suppression_Audit_Expired.signature",
    "threatq_match_indicators_incident_management_suppression_audit": "Notable_Event_Suppressions.Suppression_Audit.signature, Notable_Event_Suppressions.Suppression_Audit.user",
    "threatq_match_indicators_intrusion_detection": "IDS_Attacks.src, IDS_Attacks.signature, IDS_Attacks.user",
    "threatq_match_indicators_authentication": "Authentication.src_user, Authentication.user",
    "threatq_match_indicators_certificates": "All_Certificates.SSL.ssl_hash, All_Certificates.SSL.ssl_issuer_email, All_Certificates.SSL.ssl_subject_email, All_Certificates.SSL.ssl_subject_common_name, All_Certificates.SSL.ssl_issuer_common_name, All_Certificates.SSL.ssl_subject_organization, All_Certificates.SSL.ssl_issuer_organization, All_Certificates.SSL.ssl_serial, All_Certificates.SSL.ssl_subject_unit, All_Certificates.SSL.ssl_issuer_unit",
    "threatq_match_indicators_endpoint_filesystem": "Filesystem.file_name, Filesystem.file_hash",
    "threatq_match_indicators_endpoint_services": "Services.service",
    "threatq_match_indicators_endpoint_processes": "Processes.process_name",
    "threatq_match_indicators_email": "All_Email.file_name, All_Email.file_hash, All_Email.subject, All_Email.src_user",
    "threatq_match_indicators_compute_inventory": "All_Inventory.User.user",
    "threatq_match_indicators_network_resolution": "DNS.query, DNS.answer",
    "threatq_match_indicators_updates": "Updates.file_name, Updates.file_hash",
    "threatq_match_indicators_web": "Web.user, Web.http_referrer, Web.url, Web.http_user_agent, Web.src, Web.dest"
}