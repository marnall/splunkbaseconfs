import os
from splunklib.modularinput import Argument

class AppConsts:
    APP_NAME = "drp"
    LOG_FILE_DIRECTORY = os.environ["SPLUNK_HOME"] + "/var/log/splunk/" + APP_NAME
    COLLECTION_LIST = {
        "violation/list": "Turn on Violations collection",
    }

    PRODUCT_DATA_FOR_POLLER = {
        "product_type": "SIEM",
        "product_name": "Splunk",
        "integration_name": "Group-IB Digital Risk Protection",
        "integration_version": "1.2.1",
    }

    DATA_INPUTS_ARGUMENTS_SCHEMA = [
        {
            "name": "gib_username",
            "title": "Username",
            "data_type": Argument.data_type_string,
            "description": "Username",
            "required_on_create": True,
            "required_on_edit": True,
        },
        {
            "name": "enable_proxy",
            "title": "Enable Proxy?",
            "data_type": Argument.data_type_boolean,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "proxy_address",
            "title": "Proxy Address",
            "data_type": Argument.data_type_string,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "proxy_port",
            "title": "Proxy Port",
            "data_type": Argument.data_type_number,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "proxy_protocol",
            "title": "Proxy Protocol",
            "data_type": Argument.data_type_string,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "use_additional_accounts",
            "title": "Use additional accounts",
            "data_type": Argument.data_type_boolean,
            "description": "Allows to work with several accounts, otherwise the work is done with the main one and indexes are not added to events",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "limit_the_size_of_logs_to_100_mb",
            "title": "Limit the size of logs to 100 MB.",
            "data_type": Argument.data_type_boolean,
            "description": "When this parameter is enabled, the size of the collected logs is limited to 100 MB. If this parameter is disabled, the log size limit is 2 GB.",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "brand_for_filtering",
            "title": "Filter by Brand",
            "data_type": Argument.data_type_string,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "approve_state_for_filtering",
            "title": "Filter by Approve State",
            "data_type": Argument.data_type_string,
            "description": "Avalible options: 1 - Not required; 2 - Rejected; 3 - Under review; 4 - approved",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "sub_types_for_filtering",
            "title": "Filter by Subtype",
            "data_type": Argument.data_type_string,
            "description": "Avalible options: 1 - counterfeit; 2 - piracy; 3 - partner_policy_compliance; 4 - trademark; 5 - malware; 6 - phishing; 7 - fraud; 8 - no_violation",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "violation_section_for_filtering",
            "title": "Filter by Violation Type",
            "data_type": Argument.data_type_string,
            "description": "Avalible options: 1-Web, 3-Marketplace, 5-Advertising, 2-Mobile Apps, 4-Social Networks, 6-Instant Messengers . To enable the filter, specify the selected number",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "only_typosquatting",
            "title": "Get Typosquatting only",
            "data_type": Argument.data_type_boolean,
            "description": "",
            "required_on_create": False,
            "required_on_edit": False,
        },
        {
            "name": "use_debug_log_level",
            "title": "Enable debug logging.",
            "data_type": Argument.data_type_boolean,
            "description": "Enabling this parameter allows you to collect debug logs of the application's operation.",
            "required_on_create": False,
            "required_on_edit": False,
        },   
    ]