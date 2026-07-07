RAW_EVENTS_SAVEDSEARCH = {
    "threatq_match_indicators": {
        "ss_1": '`threatq_match_base_query` sourcetype!="threatq:indicators"',
        "ss_2": '| threatqmatchiocs `threatq_match_process_count`',
    }
}

RAW_EVENTS_SAVEDSEARCH_WITH_IS_TRUE = {
    "threatq_update_matched_indicators": {
        "ss_1": '`threatq_match_indices` `threatq_match_sourcetypes` sourcetype!="threatq:indicators"',
        "ss_2": '| threatqmatchiocs `threatq_match_process_count` is_update=true'
    }
}

DATAMODEL_TO_SAVEDSEARCH_MAPPING = {
    "network_traffic": ["threatq_match_indicators_network_traffic", "threatq_match_indicators_network_traffic_tstats"],
    "malware": ["threatq_match_indicators_malware", "threatq_match_indicators_malware_tstats"],
    "incident_management": ["threatq_match_indicators_incident_management_notable_events", "threatq_match_indicators_incident_management_suppressed_notable_events", "threatq_match_indicators_incident_management_suppression_audit_expired", "threatq_match_indicators_incident_management_suppression_audit", "threatq_match_indicators_incident_management_notable_events_tstats", "threatq_match_indicators_incident_management_suppressed_notable_events_tstats", "threatq_match_indicators_incident_management_suppression_audit_expired_tstats", "threatq_match_indicators_incident_management_suppression_audit_tstats"],
    "intrusion_detection": ["threatq_match_indicators_intrusion_detection", "threatq_match_indicators_intrusion_detection_tstats"],
    "authentication": ["threatq_match_indicators_authentication", "threatq_match_indicators_authentication_tstats"],
    "certificates": ["threatq_match_indicators_certificates", "threatq_match_indicators_certificates_tstats"],
    "endpoint": ["threatq_match_indicators_endpoint_filesystem", "threatq_match_indicators_endpoint_services", "threatq_match_indicators_endpoint_processes", "threatq_match_indicators_endpoint_filesystem_tstats", "threatq_match_indicators_endpoint_services_tstats", "threatq_match_indicators_endpoint_processes_tstats"],
    "email": ["threatq_match_indicators_email", "threatq_match_indicators_email_tstats"],
    "compute_inventory": ["threatq_match_indicators_compute_inventory", "threatq_match_indicators_compute_inventory_tstats"],
    "network_resolution": ["threatq_match_indicators_network_resolution", "threatq_match_indicators_network_resolution_tstats"],
    "updates": ["threatq_match_indicators_updates", "threatq_match_indicators_updates_tstats"],
    "web": ["threatq_match_indicators_web", "threatq_match_indicators_web_tstats"]
}

SAVEDSEARCHES_BREAKDOWN = {
    "threatq_match_indicators_network_traffic": {
        "ss_1": '| datamodel Network_Traffic All_Traffic search | fillnull value="" All_Traffic.src',
        "ss_11": '| stats count by All_Traffic.src',
        "ss_2": '| rename All_Traffic.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address" match_fields="src" datamodel_name="Network Traffic"'
    },
    "threatq_match_indicators_malware": {
        "ss_1": '| datamodel Malware Malware_Attacks search | fillnull value="" Malware_Attacks.file_name, Malware_Attacks.file_hash, Malware_Attacks.signature, Malware_Attacks.sender, Malware_Attacks.src, Malware_Attacks.user',
        "ss_11": '| stats count by Malware_Attacks.file_name, Malware_Attacks.file_hash, Malware_Attacks.signature, Malware_Attacks.sender, Malware_Attacks.src, Malware_Attacks.user',
        "ss_2": '| rename Malware_Attacks.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512, String, Email Address, IP Address, IPv6 Address, Username" match_fields="file_name, file_hash, signature, sender, src, user" datamodel_name=Malware'
    },
    "threatq_match_indicators_incident_management_notable_events": {
        "ss_1": '| datamodel Incident_Management Notable_Events search | fillnull value="" Notable_Events.src',
        "ss_11": '| stats count by Notable_Events.src',
        "ss_2": '| rename Notable_Events.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address" match_fields="src" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_incident_management_suppressed_notable_events" : {
        "ss_1": '| datamodel Incident_Management Suppressed_Notable_Events search | fillnull value="" Suppressed_Notable_Events.src',
        "ss_11": '| stats count by Suppressed_Notable_Events.src',
        "ss_2": '| rename Suppressed_Notable_Events.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address" match_fields="src" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_incident_management_suppression_audit_expired": {
        "ss_1": '| datamodel Incident_Management Suppression_Audit_Expired search | fillnull value="" Notable_Event_Suppressions.Suppression_Audit_Expired.signature',
        "ss_11": '| stats count by Notable_Event_Suppressions.Suppression_Audit_Expired.signature',
        "ss_2": '| rename Notable_Event_Suppressions.Suppression_Audit_Expired.* as * | threatqfieldsmatchiocs indicator_types="String" match_fields="signature" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_incident_management_suppression_audit": {
        "ss_1": '| datamodel Incident_Management Suppression_Audit search | fillnull value="" Notable_Event_Suppressions.Suppression_Audit.signature, Notable_Event_Suppressions.Suppression_Audit.user',
        "ss_11": '| stats count by Notable_Event_Suppressions.Suppression_Audit.signature, Notable_Event_Suppressions.Suppression_Audit.user',
        "ss_2": '| rename Notable_Event_Suppressions.Suppression_Audit.* as * | threatqfieldsmatchiocs indicator_types="String, Username" match_fields="signature, user" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_intrusion_detection": {
        "ss_1": '| datamodel Intrusion_Detection IDS_Attacks search | fillnull value="" IDS_Attacks.src, IDS_Attacks.signature, IDS_Attacks.user',
        "ss_11": '| stats count by IDS_Attacks.src, IDS_Attacks.signature, IDS_Attacks.user',
        "ss_2": '| rename IDS_Attacks.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address, String, Username" match_fields="src, signature, user" datamodel_name="Intrusion Detection"'
    },
    "threatq_match_indicators_authentication": {
        "ss_1": '| datamodel Authentication Authentication search | fillnull value="" Authentication.src_user, Authentication.user',
        "ss_11": '| stats count by Authentication.src_user, Authentication.user',
        "ss_2": '| rename Authentication.* as * | threatqfieldsmatchiocs indicator_types="Username" match_fields="src_user, user" datamodel_name="Authentication"'
    },
    "threatq_match_indicators_certificates": {
        "ss_1": '| datamodel Certificates SSL search | fillnull value="" All_Certificates.SSL.ssl_hash, All_Certificates.SSL.ssl_issuer_email, All_Certificates.SSL.ssl_subject_email, All_Certificates.SSL.ssl_subject_common_name, All_Certificates.SSL.ssl_issuer_common_name, All_Certificates.SSL.ssl_subject_organization, All_Certificates.SSL.ssl_issuer_organization, All_Certificates.SSL.ssl_serial, All_Certificates.SSL.ssl_subject_unit, All_Certificates.SSL.ssl_issuer_unit',
        "ss_11": '| stats count by All_Certificates.SSL.ssl_hash, All_Certificates.SSL.ssl_issuer_email, All_Certificates.SSL.ssl_subject_email, All_Certificates.SSL.ssl_subject_common_name, All_Certificates.SSL.ssl_issuer_common_name, All_Certificates.SSL.ssl_subject_organization, All_Certificates.SSL.ssl_issuer_organization, All_Certificates.SSL.ssl_serial, All_Certificates.SSL.ssl_subject_unit, All_Certificates.SSL.ssl_issuer_unit',
        "ss_2": '| rename All_Certificates.SSL.* as * | threatqfieldsmatchiocs indicator_types="SHA-1, SHA-256, SHA-384, SHA-512, Email Address, String" match_fields="ssl_hash, ssl_issuer_email, ssl_subject_email, ssl_subject_common_name, ssl_issuer_common_name, ssl_subject_organization, ssl_issuer_organization, ssl_serial, ssl_subject_unit, ssl_issuer_unit" datamodel_name="Certificates"'
    },
    "threatq_match_indicators_endpoint_filesystem": {
        "ss_1": '| datamodel Endpoint Filesystem search | fillnull value="" Filesystem.file_name, Filesystem.file_hash',
        "ss_11": '| stats count by Filesystem.file_name, Filesystem.file_hash',
        "ss_2": '| rename Filesystem.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512" match_fields="file_name, file_hash" datamodel_name="Endpoint"'
    },
    "threatq_match_indicators_endpoint_services": {
        "ss_1": '| datamodel Endpoint Services search | fillnull value="" Services.service',
        "ss_11": '| stats count by Services.service',
        "ss_2": '| rename Services.* as * | threatqfieldsmatchiocs indicator_types="Service Name" match_fields="service" datamodel_name="Endpoint"'
    },
    "threatq_match_indicators_endpoint_processes": {
        "ss_1": '| datamodel Endpoint Processes search | fillnull value="" Processes.process_name',
        "ss_11": '| stats count by Processes.process_name',
        "ss_2": '| rename Processes.* as * | threatqfieldsmatchiocs indicator_types="Service Name" match_fields="process_name" datamodel_name="Endpoint"'
    },
    "threatq_match_indicators_email": {
        "ss_1": '| datamodel Email All_Email search | fillnull value="" All_Email.file_name, All_Email.file_hash, All_Email.subject, All_Email.src_user',
        "ss_11": '| stats count by All_Email.file_name, All_Email.file_hash, All_Email.subject, All_Email.src_user',
        "ss_2": '| rename All_Email.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512, Email Subject, Email Address" match_fields="file_name, file_hash, subject, src_user" datamodel_name="Email"'
    },
    "threatq_match_indicators_compute_inventory": {
        "ss_1": '| datamodel Compute_Inventory User search | fillnull value="" All_Inventory.User.user',
        "ss_11": '| stats count by All_Inventory.User.user ',
        "ss_2": '| rename All_Inventory.User.* as * | threatqfieldsmatchiocs indicator_types="Username" match_fields="user" datamodel_name="Inventory"'
    },
    "threatq_match_indicators_network_resolution": {
        "ss_1": '| datamodel Network_Resolution DNS search | fillnull value="" DNS.query, DNS.answer',
        "ss_11": '| stats count by DNS.query, DNS.answer',
        "ss_2": '| rename DNS.* as * | threatqfieldsmatchiocs indicator_types="FQDN, String" match_fields="query, answer" datamodel_name="Network Resolution (DNS)"'
    },
    "threatq_match_indicators_updates": {
        "ss_1": '| datamodel Updates Updates search | fillnull value="" Updates.file_name, Updates.file_hash',
        "ss_11": '| stats count by Updates.file_name, Updates.file_hash',
        "ss_2": '| rename Updates.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512" match_fields="file_name, file_hash" datamodel_name="Updates"'
    },
    "threatq_match_indicators_web": {
        "ss_1": '| datamodel Web Web search | fillnull value="" Web.user, Web.http_referrer, Web.url, Web.http_user_agent, Web.src, Web.dest',
        "ss_11": '| rex field=Web.url "^([A-Za-z]*:\/\/)?(?<url>(.*))" | eval Web.url=url | stats count by Web.user, Web.http_referrer, Web.url, Web.http_user_agent, Web.src, Web.dest',
        "ss_2": '| rename Web.* as * | threatqfieldsmatchiocs indicator_types="Username, URL, User-agent, IP Address, IPv6 Address" match_fields="user, http_referrer, url, http_user_agent, src, dest" `enable_url_partial_match_datamodel` datamodel_name="Web"'
    },
    "threatq_match_indicators_network_traffic_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Network_Traffic.All_Traffic by All_Traffic.src',
        "ss_2": '| rename All_Traffic.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address" match_fields="src" datamodel_name="Network Traffic"'
    },
    "threatq_match_indicators_malware_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Malware.Malware_Attacks by Malware_Attacks.file_name, Malware_Attacks.file_hash, Malware_Attacks.signature, Malware_Attacks.sender, Malware_Attacks.src, Malware_Attacks.user',
        "ss_2": '| rename Malware_Attacks.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512, String, Email Address, IP Address, IPv6 Address, Username" match_fields="file_name, file_hash, signature, sender, src, user" datamodel_name=Malware'
    },
    "threatq_match_indicators_incident_management_notable_events_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Incident_Management where nodename=Incident_Management.Notable_Events by Notable_Events.src',
        "ss_2": '| rename Notable_Events.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address" match_fields="src" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_incident_management_suppressed_notable_events_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Incident_Management where nodename=Incident_Management.Suppressed_Notable_Events by Suppressed_Notable_Events.src',
        "ss_2": '| rename Suppressed_Notable_Events.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address" match_fields="src" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_incident_management_suppression_audit_expired_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Incident_Management where nodename= Incident_Management.Suppression_Audit_Expired by Notable_Event_Suppressions.Suppression_Audit_Expired.signature',
        "ss_2": '| rename Notable_Event_Suppressions.Suppression_Audit_Expired.* as * | threatqfieldsmatchiocs indicator_types="String" match_fields="signature"'
    },
    "threatq_match_indicators_incident_management_suppression_audit_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Incident_Management where nodename = Incident_Management.Suppression_Audit by Notable_Event_Suppressions.Suppression_Audit.signature, Notable_Event_Suppressions.Suppression_Audit.user',
        "ss_2": '| rename Notable_Event_Suppressions.Suppression_Audit.* as * | threatqfieldsmatchiocs indicator_types="String, Username" match_fields="signature, user" datamodel_name="Incident Management"'
    },
    "threatq_match_indicators_intrusion_detection_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Intrusion_Detection.IDS_Attacks by IDS_Attacks.src, IDS_Attacks.signature, IDS_Attacks.user',
        "ss_2": '| rename IDS_Attacks.* as * | threatqfieldsmatchiocs indicator_types="IP Address, IPv6 Address, String, Username" match_fields="src, signature, user" datamodel_name="Intrusion Detection"'
    },
    "threatq_match_indicators_authentication_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Authentication.Authentication by Authentication.src_user, Authentication.user',
        "ss_2": '| rename Authentication.* as * | threatqfieldsmatchiocs indicator_types="Username" match_fields="src_user, user" datamodel_name=Authentication'
    },
    "threatq_match_indicators_certificates_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Certificates where nodename=All_Certificates.SSL by All_Certificates.SSL.ssl_hash, All_Certificates.SSL.ssl_issuer_email, All_Certificates.SSL.ssl_subject_email, All_Certificates.SSL.ssl_subject_common_name, All_Certificates.SSL.ssl_issuer_common_name, All_Certificates.SSL.ssl_subject_organization, All_Certificates.SSL.ssl_issuer_organization, All_Certificates.SSL.ssl_serial, All_Certificates.SSL.ssl_subject_unit, All_Certificates.SSL.ssl_issuer_unit',
        "ss_2": '| rename All_Certificates.SSL.* as * | threatqfieldsmatchiocs indicator_types="SHA-1, SHA-256, SHA-384, SHA-512, Email Address, String" match_fields="ssl_hash, ssl_issuer_email, ssl_subject_email, ssl_subject_common_name, ssl_issuer_common_name, ssl_subject_organization, ssl_issuer_organization, ssl_serial, ssl_subject_unit, ssl_issuer_unit" datamodel_name=Certificates'
    },
    "threatq_match_indicators_endpoint_filesystem_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Endpoint.Filesystem by Filesystem.file_name, Filesystem.file_hash',
        "ss_2": '| rename Filesystem.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512" match_fields="file_name, file_hash" datamodel_name=Endpoint'
    },
    "threatq_match_indicators_endpoint_services_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Endpoint.Services by Services.service',
        "ss_2": '| rename Services.* as * | threatqfieldsmatchiocs indicator_types="Service Name" match_fields="service" datamodel_name=Endpoint'
    },
    "threatq_match_indicators_endpoint_processes_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Endpoint.Processes by Processes.process_name',
        "ss_2": '| rename Processes.* as * | threatqfieldsmatchiocs indicator_types="Service Name" match_fields="process_name" datamodel_name=Endpoint'
    },
    "threatq_match_indicators_email_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Email.All_Email by All_Email.file_name, All_Email.file_hash, All_Email.subject, All_Email.src_user ',
        "ss_2": '| rename All_Email.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512, Email Subject, Email Address" match_fields="file_name, file_hash, subject, src_user" datamodel_name=Email'
    },
    "threatq_match_indicators_compute_inventory_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Compute_Inventory where nodename=All_Inventory.User by All_Inventory.User.user',
        "ss_2": '| rename All_Inventory.User.* as * | threatqfieldsmatchiocs indicator_types="Username" match_fields="user" datamodel_name=Inventory'
    },
    "threatq_match_indicators_network_resolution_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Network_Resolution.DNS by DNS.query, DNS.answer',
        "ss_2": '| rename DNS.* as * | threatqfieldsmatchiocs indicator_types="FQDN, String" match_fields="query, answer" datamodel_name="Network Resolution (DNS)"'
    },
    "threatq_match_indicators_updates_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Updates.Updates by Updates.file_name, Updates.file_hash',
        "ss_2": '| rename Updates.* as * | threatqfieldsmatchiocs indicator_types="Filename, SHA-1, SHA-256, SHA-384, SHA-512" match_fields="file_name, file_hash" datamodel_name=Updates'
    },
    "threatq_match_indicators_web_tstats": {
        "ss_1": '| tstats `threatq_summariesonly` count from datamodel=Web.Web by Web.user, Web.http_referrer, Web.url, Web.http_user_agent, Web.src, Web.dest',
        "ss_2": '| rex field=Web.url "^([A-Za-z]*:\/\/)?(?<url>(.*))" | eval Web.url=url | rename Web.* as * | threatqfieldsmatchiocs indicator_types="Username, URL, User-agent, IP Address, IPv6 Address" match_fields="user, http_referrer, url, http_user_agent, src, dest" `enable_url_partial_match_datamodel` datamodel_name=Web'
    }
}