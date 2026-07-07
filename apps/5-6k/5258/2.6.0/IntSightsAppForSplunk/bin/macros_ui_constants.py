ADDITIONAL_SETTINGS_STANZA = "additional_parameters"

ALERT_MACRO_DICT = {
    "alert_indices": "intsights_alert_indices"
}


ALERT_FIELDS_LABEL_DICT = {
    "alert_indices": "Alert Indices"
}


VULNERABILITY_MACRO_DICT = {
    "vuln_indices": "intsights_vuln_indices",
    "vuln_target_indices": "intsights_vuln_target_indices",
    "vuln_target_sourcetypes": "intsights_vuln_target_sourcetypes",
    "vuln_target_indicator_fields": "intsights_vuln_target_indicator_fields"
}


VULNERABILITY_FIELDS_LABEL_DICT = {
    "vuln_indices": "Vuln Indices",
    "vuln_target_indices": "Vuln Target Indices",
    "vuln_target_sourcetypes": "Vuln Target Sourcetypes",
    "vuln_target_indicator_fields": "Vuln Target Indicator Fields"
}


IOC_MACRO_DICT = {
    "ioc_indices": "intsights_ioc_indices",
    "enable_tags_comments_api_calls": "intsights_enable_tags_comments_api_calls",
    "enable_maintain_corr_indexes_actions": "intsights_enable_maintain_corr_indexes_actions",
    "ips_target_indices": "intsights_ips_target_indices",
    "ips_target_sourcetypes": "intsights_ips_target_sourcetypes",
    "ips_target_ioc_fields": "intsights_ips_target_indicator_fields",
    "ips_target_action_fields": "intsights_ips_target_indicator_action_fields",
    "emails_target_indices": "intsights_emails_target_indices",
    "emails_target_sourcetypes": "intsights_emails_target_sourcetypes",
    "emails_target_ioc_fields": "intsights_emails_target_indicator_fields",
    "emails_target_action_fields": "intsights_emails_target_indicator_action_fields",
    "domains_target_indices": "intsights_domains_target_indices",
    "domains_target_sourcetypes": "intsights_domains_target_sourcetypes",
    "domains_target_ioc_fields": "intsights_domains_target_indicator_fields",
    "domains_target_action_fields": "intsights_domains_target_indicator_action_fields",
    "urls_target_indices": "intsights_urls_target_indices",
    "urls_target_sourcetypes": "intsights_urls_target_sourcetypes",
    "urls_target_ioc_fields": "intsights_urls_target_indicator_fields",
    "urls_target_action_fields": "intsights_urls_target_indicator_action_fields",
    "hashes_target_indices": "intsights_hashes_target_indices",
    "hashes_target_sourcetypes": "intsights_hashes_target_sourcetypes",
    "hashes_target_ioc_fields": "intsights_hashes_target_indicator_fields",
    "hashes_target_action_fields": "intsights_hashes_target_indicator_action_fields"
}


IOC_FIELDS_LABEL_DICT = {
    "ioc_indices": "IOC Indices",
    "enable_tags_comments_api_calls": "Enable Tags Comments API Call",
    "enable_maintain_corr_indexes_actions": "Enable maintaining correlation per IOC, correlation index and actions",
    "ips_target_indices": "IP's Target Indices",
    "ips_target_sourcetypes": "IP's Target Sourcetypes",
    "ips_target_ioc_fields": "IP's Target IOC Fields",
    "ips_target_action_fields": "IP's Target Action Fields",
    "emails_target_indices": "Email's Target Indices",
    "emails_target_sourcetypes": "Email's Target Sourcetypes",
    "emails_target_ioc_fields": "Email's Target IOC Fields",
    "emails_target_action_fields": "Email's Target Action Fields",
    "domains_target_indices": "Domain's Target Indices",
    "domains_target_sourcetypes": "Domain's Target Sourcetypes",
    "domains_target_ioc_fields": "Domain's Target IOC Fields",
    "domains_target_action_fields": "Domain's Target Action Fields",
    "urls_target_indices": "URL's Target Indices",
    "urls_target_sourcetypes": "URL's Target Sourcetypes",
    "urls_target_ioc_fields": "URL's Target IOC Fields",
    "urls_target_action_fields": "URL's Target Action Fields",
    "hashes_target_indices": "Hash's Target Indices",
    "hashes_target_sourcetypes": "Hash's Target Sourcetypes",
    "hashes_target_ioc_fields": "Hash's Target IOC Fields",
    "hashes_target_action_fields": "Hash's Target Action Fields"
}


ALL_MACROS_WITH_UI_FIELD = {
    "vuln_indices": "intsights_vuln_indices",
    "vuln_target_indices": "intsights_vuln_target_indices",
    "vuln_target_sourcetypes": "intsights_vuln_target_sourcetypes",
    "vuln_target_indicator_fields": "intsights_vuln_target_indicator_fields",
    "alert_indices": "intsights_alert_indices",
    "ioc_indices": "intsights_ioc_indices",
    "enable_tags_comments_api_calls": "intsights_enable_tags_comments_api_calls",
    "enable_maintain_corr_indexes_actions": "intsights_enable_maintain_corr_indexes_actions",
    "ips_target_indices": "intsights_ips_target_indices",
    "ips_target_sourcetypes": "intsights_ips_target_sourcetypes",
    "ips_target_ioc_fields": "intsights_ips_target_indicator_fields",
    "ips_target_action_fields": "intsights_ips_target_indicator_action_fields",
    "emails_target_indices": "intsights_emails_target_indices",
    "emails_target_sourcetypes": "intsights_emails_target_sourcetypes",
    "emails_target_ioc_fields": "intsights_emails_target_indicator_fields",
    "emails_target_action_fields": "intsights_emails_target_indicator_action_fields",
    "domains_target_indices": "intsights_domains_target_indices",
    "domains_target_sourcetypes": "intsights_domains_target_sourcetypes",
    "domains_target_ioc_fields": "intsights_domains_target_indicator_fields",
    "domains_target_action_fields": "intsights_domains_target_indicator_action_fields",
    "urls_target_indices": "intsights_urls_target_indices",
    "urls_target_sourcetypes": "intsights_urls_target_sourcetypes",
    "urls_target_ioc_fields": "intsights_urls_target_indicator_fields",
    "urls_target_action_fields": "intsights_urls_target_indicator_action_fields",
    "hashes_target_indices": "intsights_hashes_target_indices",
    "hashes_target_sourcetypes": "intsights_hashes_target_sourcetypes",
    "hashes_target_ioc_fields": "intsights_hashes_target_indicator_fields",
    "hashes_target_action_fields": "intsights_hashes_target_indicator_action_fields"
}

IOC_ADDITIONAL_MACRO_DICT = {
    "ips_target_ioc_fields_calc": "intsights_ips_target_indicator_fields_calc",
    "ips_target_action_fields_calc": "intsights_ips_target_indicator_action_fields_calc",
    "emails_target_ioc_fields_calc": "intsights_emails_target_indicator_fields_calc",
    "emails_target_action_fields_calc": "intsights_emails_target_indicator_action_fields_calc",
    "domains_target_ioc_fields_calc": "intsights_domains_target_indicator_fields_calc",
    "domains_target_action_fields_calc": "intsights_domains_target_indicator_action_fields_calc",
    "urls_target_ioc_fields_calc": "intsights_urls_target_indicator_fields_calc",
    "urls_target_action_fields_calc": "intsights_urls_target_indicator_action_fields_calc",
    "hashes_target_ioc_fields_calc": "intsights_hashes_target_indicator_fields_calc",
    "hashes_target_action_fields_calc": "intsights_hashes_target_indicator_action_fields_calc",
}

IOC_LAST_7_DAY_SEARCHES = [
    "intsights_remove_old_event_details",
    "intsights_correlation_hashes_event_details",
    "intsights_correlation_urls_event_details",
    "intsights_correlation_emails_event_details",
    "intsights_correlation_ips_event_details",
    "intsights_correlation_domain_event_details"
]
