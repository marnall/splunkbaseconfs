WINDOWS_SOURCES = '"*WinEventLog:Application","*WinEventLog:Security","*WinEventLog:System","powershell://generate_windows_update_logs"'
WINDOWS_SOURCE_TYPES = '"Script:ListeningPorts","WinRegistry","WindowsFirewallStatus","windows:certstore:local","DhcpSrvLog","WindowsUpdateLog","WMI:Version","WMI:InstalledUpdates"'
WINDOWS_AD_SOURCES = '"WinEventLog:DFS Replication","WinEventLog:Directory Service","WinEventLog:Microsoft-AzureADPasswordProtection-DCAgent/Admin"'
WINDOWS_AD_SOURCE_TYPES = '"MSAD:NT6:Netlogon","MSAD:NT6:Replication","MSAD:NT6:Health","MSAD:NT6:SiteInfo","windows:certstore:ca:issued","ActiveDirectory"'
WINDOWS_DNS_SOURCES = '"WinEventLog:DNS Server"'
WINDOWS_DNS_SOURCE_TYPES = '"MSAD:NT6:DNS","MSAD:NT6:DNS-Health","MSAD:NT6:DNS-Zone-Information"'


def build_search_query(macro, by, values, important_fields={}, first_call=True):
    search = ""
    values = values.split(",")

    for index in range(len(values)):
        important_fields_dict = important_fields.get(values[index].strip('"'), dict())
        important_fields_key =  ",".join(important_fields_dict.keys())
        important_fields_values = ",".join(important_fields_dict.values())
        if index > 0 or first_call is False:
            search += " | append ["
        search += """| tstats count where `{macro}` {by} IN ("{value}") | eval {by}="{value}" | rename {by} as sources | table sources count 
        | appendcols [ search `{macro}` {by} IN ("{value}") | fieldsummary {important_fields_key} | table field, count, distinct_count, values | rename count as field_count | streamstats count as row | eval confidence_list=split("{confidence}", ",")
| eval confidence=tonumber(mvindex(confidence_list, row-1)) | rex field=values "(?<values>\\{{\\\"value\\\":\\\"[^\\\"]+\\\",\\\"count\\\":\\d+\\}}(?:,\\{{\\\"value\\\":\\\"[^\\\"]+\\\",\\\"count\\\":\\d+\\}})?)" | eval values="[".values."]" ] | filldown sources, count | eval field_coverage=round((field_count/count)*100,2), field_coverage=if(isnull(field_coverage),"-",field_coverage), important_fields = field."||".field_count."||".distinct_count."||".values."||".field_coverage."||".confidence  |  fields - field, field_count, distinct_count, values,field_coverage, row, confidence_list, confidence | stats values(*) as * | table sources, count, important_fields""".format(
            macro=macro, by=by, value=values[index].strip('"'), important_fields_key=important_fields_key, confidence=important_fields_values
        )
        if index > 0 or first_call is False:
            search += "]"

    return search


def build_source_latency_search(macro, by, values):
    return "`{macro}` {by} IN ({values}) | eval diff=(_indextime - _time) / 60 | rename {by} as sources | stats max(diff) as max_delay avg(diff) as avg_delay by sources".format(
        macro=macro, by=by, values=values
    )


def build_host_reviewer_search(by, values):
    return "| tstats count where index=* {by} IN ({values}) by {by} host | rename {by} as sources".format(
        by=by, values=values
    )


def build_metadata_count_search(by, values):
    return "{by} IN ({values}) OR ".format(by=by, values=values)


def build_source_reviewer_search(by, values, first_call=True):
    search = ""
    values = values.split(",")

    for index in range(len(values)):
        if index > 0 or first_call is False:
            search += " | append ["
        search += """| tstats values(host) as hosts where index=* {by} IN ("{value}") by {by} index
        | stats count values(*) as * dc(hosts) as host_count by {by}
        | stats count values(*) as * sum(host_count) as host_count
        | eval {by}=if(count>0,{by},"{value}")
        | rename {by} as sources""".format(
            by=by, value=values[index].strip('"')
        )
        if index > 0 or first_call is False:
            search += "]"
    return search


def build_data_availablity_panel_search(macro, by, values, first_call=True):
    search = ""
    values = values.split(",")

    for index in range(len(values)):
        if index > 0 or first_call is False:
            search += " | append ["
        search += """| tstats count where `{macro}` {by}="{value}"
        | eval label="`{macro}` {by}=\\"{value}\\""
        """.format(
            macro=macro, by=by, value=values[index].strip('"')
        )
        if index > 0 or first_call is False:
            search += "]"
    return search


def build_app_dependency_search(app_list):
    search = ""
    count = 0
    for app in app_list:
        if count > 0:
            search += " | append ["

        search += """| rest /services/apps/local splunk_server=local
            | search label="{app}"
            | eval is_installed="Installed"
            | table label, is_installed, disabled
            | append
                [| makeresults count=1
                | eval label="{app}", disabled="-", is_installed="Not Installed", link="{link}"
                | table label, is_installed, disabled, link]
            """.format(app=app['label'], link=app['link'])
        if count > 0:
            search += "]"
        count += 1

    if len(search) > 0:
        search += """| stats first(*) as * by label
            | eval disabled = case(disabled=0, "Enabled", disabled=1, "Disabled", 1==1, "-")
            | table label, is_installed, disabled, link
            | rename label as "App Name", is_installed as "Installation Status", link as "Splunkbase Link", disabled as "Enabled/Disabled"
            """
    return search

def resolve_macro_configurations(macro_configurations):
    for config in macro_configurations:
        important_fields = config.get("important_fields", {})
        if callable(config.get("search")):
            # Lambda pattern — Windows, Windows AD, Windows DNS
            config["search"] = config["search"](important_fields)
    return macro_configurations


PRODUCTS = [
    {
        "name": "CrowdStrike EventStream",
        "app_dependencies": [
            {
                "label": "CrowdStrike Falcon Event Streams",
                "link": "https://splunkbase.splunk.com/app/5082/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_crowdstrike_eventstream",
                "label": "CrowdStrike EventStream Data",
                "search_by": "sourcetype",
                "search_values": "CrowdStrike:Event:Streams:JSON",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "CrowdStrike:Event:Streams:JSON" : {"metadata.eventType": "50", "action": "75", "event.SeverityName": "15", "event.LocalIP": "50", "event.Hostname":"50", 'event.ComputerName': "50"}
                }
            }
        ],
    },
    {
        "name": "Kaspersky",
        "app_dependencies": [
            {
                "label": "Kaspersky Add-on for Splunk",
                "link": "https://splunkbase.splunk.com/app/4656/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_kaspersky",
                "label": "Kaspersky Data",
                "search_by": "sourcetype",
                "search_values": "kaspersky:leef,kaspersky:klaud,kaspersky:klprci,kaspersky:klbl,kaspersky:klsrv,kaspersky:gnrl,kaspersky:klnag",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "kaspersky:leef": {"log_type": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_KL_PRODUCT_DISPVER": "50", "EVC_EV_KL_PRODUCT_NAME": "50","EVC_EV_TASK_ID": "50"},
                    "kaspersky:klaud": {"log_type": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_KL_PRODUCT_DISPVER": "50", "EVC_EV_KL_PRODUCT_NAME": "50","EVC_EV_TASK_ID": "50"},
                    "kaspersky:klprci": {"log_type": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_KL_PRODUCT_DISPVER": "50", "EVC_EV_KL_PRODUCT_NAME": "50","EVC_EV_TASK_ID": "50"},
                    "kaspersky:klbl": {"log_type": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_KL_PRODUCT_DISPVER": "50", "EVC_EV_KL_PRODUCT_NAME": "50","EVC_EV_TASK_ID": "50"},
                    "kaspersky:klsrv": {"log_type": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_DISP_HOST_NAME": "50", "EVC_EV_DESC": "50", "EVC_EV_KL_PRODUCT_DISPVER": "50"},
                    "kaspersky:gnrl": {"log_type": "50", "usrName": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_EXT_DEV_ID": "50", "EVC_EV_TASK_NAME": "50"},
                    "kaspersky:klnag": {"log_type": "50", "EVC_EV_DESC": "50", "EVC_EV_DISP_HOST_NAME": "50", "EVC_EV_GROUP_NAME": "50", "EVC_EV_KL_PRODUCT_DISPVER": "50"}
                }
            }
        ],
    },
    {
        "name": "Office 365 Defender ATP",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Microsoft Security",
                "link": "https://splunkbase.splunk.com/app/6207/"
            },
            {
                "label": "Defender ATP Status Check Add-on",
                "link": "https://splunkbase.splunk.com/app/5691/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_o365_defender_atp",
                "label": "Microsoft 365 Defender ATP Data",
                "search_by": "sourcetype",
                "search_values": "ms:defender:atp:alerts",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "ms:defender:atp:alerts" : {"computerDnsName": "50", "category": "50", "threatName": "50", "threatFamilyName": "50", "incidentId": "50"}
                }
            },
            {
                "macro_name": "cs_o365_defender_atp_audit",
                "label": "Microsoft 365 Defender ATP Audit Data",
                "search_by": "sourcetype",
                "search_values": "DefenderATPStatusLog",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "DefenderATPStatusLog" : {"OnboardingState": "50", "status": "50", "LastConnected": "50", "host": "50"}
                }
            },
        ],
    },
    {
        "name": "Sophos Endpoint Protection",
        "app_dependencies": [
            {
                "label": "Sophos Central Addon for Splunk",
                "link": "https://splunkbase.splunk.com/app/6186/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_sophos",
                "label": "Sophos Endpoint Protection Data",
                "search_by": "sourcetype",
                "search_values": "sophos_events,sophos_endpoints",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "sophos_events": {"source_info.ip": "50", "user": "50", "location": "50", "type": "50", "dhost": "50"},
                    "sophos_endpoints": {"id": "50", "tenant.id": "50", "type": "50", "associatedPerson.viaLogin": "50", "health.overall": "50"}
                }
            }
        ],
    },
    {
        "name": "Trendmicro",
        "app_dependencies": [
            {
                "label": "Trend Vision One for Splunk (XDR)",
                "link": "https://splunkbase.splunk.com/app/5364/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_trendmicro",
                "label": "Trendmicro Data",
                "search_by": "sourcetype",
                "search_values": "xdr_oat,xdr_audit,xdr_alerts_wb,xdr_detection",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "xdr_oat": {"filter.level": "50", "endpoint.name": "50", "filter.techniques{}": "50", "filter.tactics{}": "50", "detail.processFilePath": "50"},
                    "xdr_audit": {"activity": "50", "role": "50", "user": "50", "category": "50", "loggedTime": "50"},
                    "xdr_alerts_wb": {"incidentId": "50", "score": "50", "status": "50", "dest": "50", "app": "50"},
                    "xdr_detection": {"app": "50", "action": "50", "msg": "50", "remarks": "50", "severity": "50"}
                }
            }
        ],
    },
    {
        "name": "Windows Defender",
        "app_dependencies": [
            {
                "label": "Microsoft Windows Defender Add-on for Splunk",
                "link": "https://splunkbase.splunk.com/app/3734/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_windows_defender",
                "label": "Windows Defender Data",
                "search_by": "source",
                "search_values": '"*WinEventLog:Microsoft-Windows-Windows Defender/Operational"',
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "*WinEventLog:Microsoft-Windows-Windows Defender/Operational" : {"EventCode": "50", "AVSignature_version": "20", "Platform_version": "35", "action": "2", "Threat_Name": "2"}
                }
            }
        ],
    },
    {
        "name": "AWS",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for AWS",
                "link": "https://splunkbase.splunk.com/app/1876/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_aws",
                "label": "AWS Data",
                "search_by": "sourcetype",
                "search_values": "aws:cloudtrail",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "aws:cloudtrail" : {"eventName": "50", "errorCode": "50", "user": "50", "src": "50", "eventSource": "70", "awsRegion": "50", "aws_account_id": "70"}
                }
            }
        ],
    },
    {
        "name": "Google Workspace",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Google Workspace",
                "link": "https://splunkbase.splunk.com/app/5556/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_gws",
                "label": "Google Workspace Data",
                "search_by": "sourcetype",
                "search_values": "gws:reports:admin,gws:reports:login,gws:reports:groups_enterprise,gws:alerts,gws:reports:drive,gws:gmail",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "gws:reports:admin": {"event.name": "50", "actor.email": "50", "user_email": "50", "action": "50", "user": "50"},
                    "gws:reports:login": {"event.name": "50", "user": "50", "ip_address": "50", "login_challenge_method": "50", "app": "50"},
                    "gws:reports:groups_enterprise": {"event.name": "50", "actor.email": "50", "group_id": "50", "user": "50", "member_id": "50"},
                    "gws:alerts": {"user": "50", "type": "50", "status": "50", "description": "50", "severity": "50"},
                    "gws:reports:drive": {"event.name": "50", "doc_title": "50", "doc_type":"50", "owner": "50", "email":"50"},
                    "gws:gmail": {"SenderAddress": "50", "MessageId": "50", "RecipientAddress": "50", "Subject": "50", "Status": "50"}  
                }
            }
        ],
    },
    {
        "name": "Office 365",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Microsoft Office 365",
                "link": "https://splunkbase.splunk.com/app/4055/"
            },
            {
                "label": "Microsoft Graph Security Score Add-on",
                "link": "https://splunkbase.splunk.com/app/5693/"
            },
            {
                "label": "Splunk Add-on for Microsoft Azure",
                "link": "https://splunkbase.splunk.com/app/3757/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_o365",
                "label": "Office 365 Data",
                "search_by": "sourcetype",
                "search_values": "o365:management:activity,o365:service:healthIssue,o365:reporting:messagetrace,o365:graph:messagetrace",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "o365:management:activity" : {"Operation": "50", "app": "50", "ClientIP": "40", "user": "50", "user_type": "95"},
                    "o365:service:healthIssue" : {"status": "50", "service": "50", "Status": "50", "WorkloadDisplayName": "50", "title": "50"},
                    "o365:reporting:messagetrace": {"SenderAddress": "50", "MessageId": "50", "RecipientAddress": "50", "Subject": "50", "Status": "50"},
                    "o365:graph:messagetrace": {"senderAddress": "50", "messageId": "50", "recipientAddress": "50", "subject": "50", "status": "50"},
                }
            },
            {
                "macro_name": "cs_azure_securityscore",
                "label": "Azure Security Score Data",
                "search_by": "sourcetype",
                "search_values": "GraphSecurity:Score",
                "earliest_time": "-2d@d",
                "latest_time": "now",
                "important_fields": {
                    "GraphSecurity:Score": {"currentScore": "50", "maxScore": "50"}
                }
            },
            {
                "macro_name": "cs_azure",
                "label": "Azure Active Directory Data",
                "search_by": "sourcetype",
                "search_values": "azure:aad:audit,azure:aad:signin",
                "earliest_time": "-2d@d",
                "latest_time": "now",
                "important_fields": {
                    "azure:aad:audit" : {"activityDisplayName": "50", "Actor": "50", "Command": "50", "Target_userPrincipalName": "50", "Target_DisplayName": "50"},
                    "azure:aad:signin" : {"userPrincipalName": "50", "ipAddress": "50", "status.additionalDetails": "50", "status.errorCode": "50", "status.failureReason": "50"}
                }
            },
        ],
    },
    {
        "name": "Email",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Google Workspace",
                "link": "https://splunkbase.splunk.com/app/5556/"
            },
            {
                "label": "Splunk Add-on for Microsoft Office 365",
                "link": "https://splunkbase.splunk.com/app/4055/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_email_sources",
                "label": "Email Data",
                "search_by": "sourcetype",
                "search_values": "ms:o365:reporting:messagetrace,o365:reporting:messagetrace,o365:graph:messagetrace,gws:gmail",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "ms:o365:reporting:messagetrace": {"SenderAddress": "50", "RecipientAddress": "50", "MessageId": "50", "Subject": "50", "Status": "50"},
                    "o365:reporting:messagetrace": {"SenderAddress": "50", "MessageId": "50", "RecipientAddress": "50", "Subject": "50", "Status": "50"},
                    "o365:graph:messagetrace": {"senderAddress": "50", "messageId": "50", "recipientAddress": "50", "subject": "50", "status": "50"},
                    "gws:gmail": {"SenderAddress": "50", "RecipientAddress": "50", "MessageId": "50", "Subject": "50", "message_info.is_spam": "50"}
                }
            }
        ],
    },
    {
        "name": "Network",
        "app_dependencies": [],
        "metadata_count_search": '`cs_network_indexes` tag=network tag=communicate | stats count',
        "macro_configurations": [
            {
                "macro_name": "cs_network_indexes",
                "label": "Network Data (indexes)",
                "search": '`cs_network_indexes` tag=network tag=communicate | stats count by index, sourcetype',
                "host_reviewer_search": '`cs_network_indexes` tag=network tag=communicate | stats count by sourcetype host | rename sourcetype as sources',
                "sources_reviewer_search": '`cs_network_indexes` tag=network tag=communicate | stats dc(host) as host_count values(index) as index by sourcetype | rename sourcetype as sources',
                "data_availablity_panel_search": '`cs_network_indexes` tag=network tag=communicate | head 1 | stats count | eval label="`cs_network_indexes` tag=network tag=communicate" ',
                "source_latency_search": '`cs_network_indexes` tag=network tag=communicate | eval diff=(_indextime - _time) / 60 | stats max(diff) as max_delay avg(diff) as avg_delay by sourcetype | rename sourcetype as sources',
                "earliest_time": "-4h@h",
                "latest_time": "now",
            }
        ],
    },
    {
        "name": "Cisco IOS",
        "app_dependencies": [
            {
                "label": "Cisco Networks Add-on",
                "link": "https://splunkbase.splunk.com/app/1467/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_cisco_ios",
                "label": "Cisco IOS Data",
                "search_by": "sourcetype",
                "search_values": "cisco:ios",
                "earliest_time": "-4h@h",
                "latest_time": "now",
                "important_fields": {
                    "cisco:ios": {"mnemonic": "50", "host": "50", "src": "50", "dest": "50", "cpu_load_percent": "50", "message_text": "50"}
                }
            }
        ],
    },
    {
        "name": "FortiGate",
        "app_dependencies": [
            {
                "label": "Fortinet Fortigate Add-on for Splunk",
                "link": "https://splunkbase.splunk.com/app/2846/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_fortigate",
                "label": "FortiGate Data",
                "search_by": "sourcetype",
                "search_values": "fortigate_event,fortigate_traffic,fortigate_utm",
                "earliest_time": "-4h@h",
                "latest_time": "now",
                "important_fields": {
                    "fortigate_event": {"severity": "50", "subtype": "50", "src_ip": "50", "action": "50", "logdesc": "50", "dvc": "50"},
                    "fortigate_traffic": {"src_ip": "50", "dest_ip": "50", "dest_port": "50", "dvc": "50", "action": "50", "app": "50"},
                    "fortigate_utm": {"src": "50", "dest": "50", "dvc": "50", "action": "50", "signature": "50", "url": "50"}
                }
            }
        ],
    },
    {
        "name": "Palo Alto",
        "app_dependencies": [
            {
                "label": "Palo Alto Networks Add-on",
                "link": "https://splunkbase.splunk.com/app/2757/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_palo",
                "label": "Palo Alto Data",
                "search_by": "sourcetype",
                "search_values": "pan:config,pan:globalprotect,pan:system,pan:threat,pan:traffic",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "pan:config" : {"log_subtype": "70", "dvc": "50", "user": "50", "command": "50", "configuration_path": "50"},
                    "pan:globalprotect" : {"log_subtype": "70", "app": "50", "src": "50", "dest": "50", "action": "50", "user": "50"},
                    "pan:system" : {"log_subtype": "70", "action": "50", "description": "50", "dvc": "50", "dvc_name": "50", "severity": "50"},
                    "pan:threat" : {"log_subtype": "70", "severity": "50", "action": "50", "threat": "50", "dvc_name": "50", "src_ip": "50"},
                    "pan:traffic" : {"log_subtype": "70", "dest": "50", "dvc": "50", "src_ip": "50", "dest_ip": "50", "app": "50", "rule": "50"}
                }
            }
        ],
    },
    {
        "name": "Sophos Firewall",
        "app_dependencies": [
            {
                "label": "Sophos XG Firewall Add-on For Splunk",
                "link": "https://splunkbase.splunk.com/app/6187/"
            },
            {
                "label": "Sophos Central Addon for Splunk",
                "link": "https://splunkbase.splunk.com/app/6186/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_sophos_firewall",
                "label": "Sophos Firewall Data",
                "search_by": "sourcetype",
                "search_values": "sophos:xg:firewall,sophos:xg:heartbeat,sophos:xg:system_health,sophos:xg:atp,sophos:xg:idp,sophos:xg:event",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "sophos:xg:firewall": {"app_name": "50", "dst_ip" : "50", "dst_port": "50", "src_ip": "50", "src_port": "50", "app_category": "50"},
                    "sophos:xg:heartbeat": {"device_name": "50", "device_model": "50", "log_subtype": "50", "severity": "50", "hb_status": "50"},
                    "sophos:xg:system_health": {"device_name": "50", "device_model": "50", "log_subtype": "50", "severity": "50", "log_component": "50"},
                    "sophos:xg:atp": {"src_ip": "50", "malware": "50", "message": "50", "classification": "50", "user_name": "50"},
                    "sophos:xg:idp": {"message": "50", "malware": "50", "src_ip": "50", "user_name": "50", "classification": "50"},
                    "sophos:xg:event": {"src_ip": "50", "user_name": "50", "message": "50", "severity": "50", "log_component": "50"},
                }
            },
            {
                "macro_name": "cs_sophos",
                "label": "Sophos Firewall Events Data",
                "search_by": "sourcetype",
                "search_values": "sophos_events",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "sophos_events" : {"name": "50", "location": "50", "type": "50", "host": "50"}
                }
            }
        ],
    },
    {
        "name": "Cisco Meraki",
        "app_dependencies": [
            {
                "label": "TA-meraki",
                "link": "https://splunkbase.splunk.com/app/3018/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_cisco_meraki",
                "label": "Cisco Meraki Data",
                "search_by": "sourcetype",
                "search_values": "meraki:securityappliances,meraki:organizationsecurity,meraki:audit,meraki:accesspoints,meraki:switches,meraki:networkdevices,meraki:devices",
                "earliest_time": "-3d@d",
                "latest_time": "now",
                "important_fields": {
                    "meraki:securityappliances": {"clientId": "50", "clientMac": "50", "description": "50", "deviceName": "50", "deviceSerial": "50"},
                    "meraki:organizationsecurity": {"eventType": "50", "priority": "50", "srcIp": "50", "destIp": "50", "classification": "50"},
                    "meraki:audit": {"adminName": "50", "adminEmail": "50", "networkName": "50", "networkId": "50", "page": "50"},
                    "meraki:accesspoints": {"clientId": "50", "clientMac": "50", "description": "50", "deviceName": "50", "deviceSerial": "50"},
                    "meraki:switches": {"clientId": "50", "clientMac": "50", "description": "50", "deviceName": "50", "deviceSerial": "50"},
                    "meraki:networkdevices": {"clientId": "50", "clientMac": "50", "description": "50", "deviceName": "50", "deviceSerial": "50"},
                    "meraki:devices": {"mac": "50", "model": "50", "name": "50", "firmware": "50", "productType": "50"}
                }
            }
        ],
    },
    {
        "name": "F5 BIGIP",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for F5 BIG-IP",
                "link": "https://splunkbase.splunk.com/app/2680/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_f5_bigip",
                "label": "F5 BIGIP Data",
                "search_by": "sourcetype",
                "search_values": "f5:bigip:syslog,f5:bigip:asm:syslog",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "f5:bigip:syslog": {"ip_client": "50", "dest_ip": "50", "dest_port": "50", "severity": "50", "attack_type": "50"},
                    "f5:bigip:asm:syslog": {"policy_name": "50", "dest_ip": "50", "enforcement_action": "50", "severity": "50", "attack_type": "50"}
                }
            }
        ],
    },
    {
        "name": "Imperva WAF",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Imperva SecureSphere WAF",
                "link": "https://splunkbase.splunk.com/app/2874/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_imperva_waf",
                "label": "Imperva WAF Data",
                "search_by": "sourcetype",
                "search_values": "imperva:waf",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "imperva:waf": {"src": "50", "ccode": "50", "category": "50", "severity": "50", "action": "50", "dest_ip": "50"}
                }
            }
        ],
    },
    {
        "name": "Imperva DAM",
        "app_dependencies": [],
        "macro_configurations": [
            {
                "macro_name": "cs_imperva_dam",
                "label": "Imperva DAM Data",
                "search_by": "sourcetype",
                "search_values": "imperva:dam:alerts,imperva:dam:internal_audit",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "imperva:dam:alerts": {"dst": "50", "dpt": "50", "duser": "50", "src": "50", "spt": "50", "Severity": "50"},
                    "imperva:dam:internal_audit": {"event_type": "50", "suser": "50", "src_ip": "50"}
                }
            }
        ],
    },
    {
        "name": "Cloudflare",
        "app_dependencies": [
            {
                "label": "Cloudflare App for Splunk",
                "link": "https://splunkbase.splunk.com/app/4501"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_cloudflare",
                "label": "Cloudflare Data",
                "search_by": "sourcetype",
                "search_values": "cloudflare:json",
                "earliest_time": "-4h@h",
                "latest_time": "now",
                "important_fields": {
                    "cloudflare:json": {"LeakedCredentialCheckResult": "50", "Action": "50", "ClientCountry": "50", "ClientIP": "50", "Kind": "50"}
                }
            }
        ],
    },
    {
        "name": "CrowdStrike Devices",
        "app_dependencies": [
            {
                "label": "CrowdStrike Falcon Devices",
                "link": "https://splunkbase.splunk.com/app/5570/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_crowdstrike_devices",
                "label": "CrowdStrike Devices Data",
                "search_by": "sourcetype",
                "search_values": "crowdstrike:device:json",
                "earliest_time": "-3d@d",
                "latest_time": "now",
                "important_fields": {
                    "crowdstrike:device:json" : {"connection_ip": "50", "connection_mac_address": "50", "filesystem_containment_status": "50", "hostname": "50", "os_product_name": "50"}
                }
            }
        ],
    },
    {
        "name": "Vulnerability",
        "app_dependencies": [],
        "metadata_count_search": '`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences | stats count',
        "macro_configurations": [
            {
                "macro_name": "cs_vulnerabilities_indexes",
                "label": "Vulnerability Data (indexes)",
                "search": '`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences | stats count by index, sourcetype',
                "host_reviewer_search": '`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences | stats count by sourcetype host | rename sourcetype as sources',
                "sources_reviewer_search": '`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences | stats dc(host) as host_count values(index) as index by sourcetype | rename sourcetype as sources',
                "data_availablity_panel_search": '`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences | head 1 | stats count | eval label="`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences" ',
                "source_latency_search": '`cs_vulnerabilities_indexes` tag=vulnerability tag=report tag=cyences | eval diff=(_indextime - _time) / 60 | stats max(diff) as max_delay avg(diff) as avg_delay by sourcetype | rename sourcetype as sources',
                "earliest_time": "-1d@d",
                "latest_time": "now",
            }
        ],
    },
    {
        "name": "CrowdStrike Spotlight",
        "app_dependencies": [
            {
                "label": "CrowdStrike Falcon Spotlight Data",
                "link": "https://splunkbase.splunk.com/app/6167/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_crowdstrike_vuln",
                "label": "CrowdStrike Spotlight Data",
                "search_by": "sourcetype",
                "search_values": "crowdstrike:spotlight:vulnerability",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "crowdstrike:spotlight:vulnerability" : {"vul_id": "50", "vul_severity": "50", "vul_state": "50", "last_found": "50", "vul_cve": "50"},
                }
            }
        ],
    },
    {
        "name": "Qualys",
        "app_dependencies": [
            {
                "label": "Qualys Technology Add-on for Splunk",
                "link": "https://splunkbase.splunk.com/app/2964/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_qualys",
                "label": "Qualys Data",
                "search_by": "sourcetype",
                "search_values": "qualys:hostDetection",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "qualys:hostDetection": {"HOST_ID": "50", "IP": "50", "DNS": "50", "OS": "50", "TRACKING_METHOD": "50"}
                }
            }
        ],
    },
    {
        "name": "Tenable",
        "app_dependencies": [
            {
                "label": "Tenable Add-On for Splunk",
                "link": "https://splunkbase.splunk.com/app/4060/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_tenable",
                "label": "Tenable Data",
                "search_by": "sourcetype",
                "search_values": "tenable:io:assets,tenable:io:vuln,tenable:sc:assets,tenable:sc:vuln",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "tenable:io:assets": {"tenable_uuid": "50", "fqdns": "50", "ipv4s": "50", "ipv6s": "50", "mac_addresses": "50"},
                    "tenable:io:vuln": {"vul_id": "50", "vul_severity": "50", "vul_state": "50", "last_found": "50", "vul_cve": "50"},
                    "tenable:sc:assets": {"fqdns": "50", "ipv4s": "50", "ipv6s": "50", "mac_addresses": "50", "operating_systems": "50"},
                    "tenable:sc:vuln": {"vul_id": "50", "vul_severity": "50", "vul_state": "50", "last_found": "50", "vul_cve": "50"},
                }
            }
        ],
    },
    {
        "name": "Nessus",
        "app_dependencies": [
            {
                "label": "Nessus Professional Add-on for Splunk",
                "link": "https://splunkbase.splunk.com/app/7464/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_nessus",
                "label": "Nessus Data",
                "search_by": "sourcetype",
                "search_values": "nessus:pro:vuln,nessus_json",
                "earliest_time": "-7d@d",
                "latest_time": "now",
                "important_fields": {
                    "nessus:pro:vuln": {"nessus_uuid": "50", "vul_id": "50", "vul_severity": "50", "vul_state": "50", "last_found": "50"},
                    "nessus_json": {"nessus_uuid": "50", "vul_id": "50", "vul_severity": "50", "vul_state": "50", "last_found": "50"}
                }
            }
        ],
    },
    {
        "name": "Sysmon",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Sysmon",
                "link": "https://splunkbase.splunk.com/app/5709/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_sysmon",
                "label": "Sysmon Data",
                "search_by": "source",
                "search_values": "*WinEventLog:Microsoft-Windows-Sysmon/Operational",
                "earliest_time": "-4h@h",
                "latest_time": "now",
                "important_fields": {
                    "*WinEventLog:Microsoft-Windows-Sysmon/Operational" : {"EventCode": "50", "Image": "50", "User": "50", "Computer": "50", "CommandLine": "50"}
                }
            }
        ],
    },
    {
        "name": "Windows",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Microsoft Windows",
                "link": "https://splunkbase.splunk.com/app/742/"
            }
        ],
        "metadata_count_search": """| tstats count where index=* sourcetype IN ({windows_sourcetypes}) OR source IN ({windows_sources}) """.format(
            windows_sourcetypes=WINDOWS_SOURCE_TYPES,
            windows_sources=WINDOWS_SOURCES,
        ),
        "macro_configurations": [
            {
                "macro_name": "cs_windows_idx",
                "label": "Windows Data",
                "important_fields": {
                    "*WinEventLog:Application" : {"EventCode": "50", "Message": "50", "SourceName": "90", "TaskCategory": "50", "User": "5"},
                    "*WinEventLog:Security" : {"EventCode": "50", "Message": "50", "Account_Domain": "95", "Account_Name": "95", "ComputerName": "50"},
                    "*WinEventLog:System" : {"EventCode": "50", "Message": "50", "ComputerName": "50", "TaskCategory": "50", "User": "45"},
                    "powershell://generate_windows_update_logs" : {"HotFixID": "50", "dest": "50", "Description": "50", "InstalledOn": "50", "InstalledBy": "50"},
                    "Script:ListeningPorts": {"appname": "50", "transport": "50", "dst_ip": "50", "dst_port": "50", "pid": "50"},
                    "WinRegistry": {"registry_type": "50", "process_image": "50", "pid": "50", "key_path": "50", "event_status": "50"},
                    "WindowsFirewallStatus": {"State": "50"},
                    "windows:certstore:local": {"PSParentPath": "50", "IssuerName": "50", "SubjectName": "50", "Issuer": "50", "PSPath": "50"},
                    "DhcpSrvLog": {"action": "5", "dest_ip": "5", "signature": "50", "quarantine_info": "50", "qresult": "50"},
                    "WindowsUpdateLog": {"dest" : "50", "process_id": "50", "component": "50", "Status": "5"},
                    "WMI:Version": {"Caption": "50", "ServicePackMajorVersion": "50", "ServicePackMinorVersion": "50", "Version": "50"},
                    "WMI:InstalledUpdates": {"HotFixID": "50", "dest": "50", "Description": "50", "InstalledOn": "50", "InstalledBy": "50"},
                },
                "search": lambda imp: (build_search_query(macro="cs_windows_idx", by="source", values=WINDOWS_SOURCES, important_fields=imp) + build_search_query(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_SOURCE_TYPES,important_fields=imp, first_call=False)),
                "host_reviewer_search": build_host_reviewer_search(by="source", values=WINDOWS_SOURCES) + " | append [" + build_host_reviewer_search(by="sourcetype", values=WINDOWS_SOURCE_TYPES) + "]",
                "sources_reviewer_search": build_source_reviewer_search(by="source", values=WINDOWS_SOURCES) + build_source_reviewer_search(by="sourcetype", values=WINDOWS_SOURCE_TYPES, first_call=False),
                "data_availablity_panel_search": build_data_availablity_panel_search(macro="cs_windows_idx", by="source", values=WINDOWS_SOURCES) + build_data_availablity_panel_search(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_SOURCE_TYPES, first_call=False),
                "source_latency_search": build_source_latency_search(macro="cs_windows_idx", by="source", values=WINDOWS_SOURCES) + " | append [ | search " + build_source_latency_search(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_SOURCE_TYPES) + "]",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                
            }
        ],
    },
    {
        "name": "Windows AD",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Microsoft Windows",
                "link": "https://splunkbase.splunk.com/app/742/"
            }
        ],
        "metadata_count_search": """| tstats count where index=* source IN ({ad_sources}) OR sourcetype IN ({ad_sourcetypes}) """.format(
            ad_sources=WINDOWS_AD_SOURCES, ad_sourcetypes=WINDOWS_AD_SOURCE_TYPES
        ),
        "macro_configurations": [
            {
                "macro_name": "cs_windows_idx",
                "label": "Windows AD Data",
                "important_fields": {
                    "WinEventLog:DFS Replication": {"EventCode": "50", "Message": "50", "SourceName": "90", "TaskCategory": "50", "ComputerName": "50"},
                    "WinEventLog:Directory Service": {"EventCode": "50", "Message": "50", "SourceName": "90", "TaskCategory": "50", "ComputerName": "50"},
                    "WinEventLog:Microsoft-AzureADPasswordProtection-DCAgent/Admin": {"EventCode": "50", "Message": "50", "SourceName": "90", "TaskCategory": "50", "ComputerName": "50"},
                    "MSAD:NT6:Netlogon": {"src_host": "50", "src_ip": "50", "src_domain": "50", "msad_affinity": "50"},
                    "MSAD:NT6:Replication": {"CN": "50", "DC": "50", "usn": "50", "src_host": "50", "transport": "50"},
                    "MSAD:NT6:Health": {"Server": "50", "DomainDNSName": "50", "Changed": "50", "OSVersion": "50"},
                    "MSAD:NT6:SiteInfo": {"Type": "50", "ForestName": "50", "Name": "90", "Site": "90", "Location": "90"},
                    "windows:certstore:ca:issued": {"PSParentPath": "50", "IssuerName": "50", "SubjectName": "50", "Issuer": "50", "PSPath": "50"},
                    "ActiveDirectory": {"lockoutTime": "40", "mail": "40", "logonHours": "35", "department": "20", "displayName": "45"}
                },
                "search": lambda imp: (
                    build_search_query(macro="cs_windows_idx", by="source", values=WINDOWS_AD_SOURCES, important_fields=imp) +
                    build_search_query(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_AD_SOURCE_TYPES, important_fields=imp, first_call=False)
                ),
                "host_reviewer_search": build_host_reviewer_search(by="source", values=WINDOWS_AD_SOURCES) + " | append [" + build_host_reviewer_search(by="sourcetype", values=WINDOWS_AD_SOURCE_TYPES) + "]",
                "sources_reviewer_search": build_source_reviewer_search(by="source", values=WINDOWS_AD_SOURCES) + build_source_reviewer_search(by="sourcetype", values=WINDOWS_AD_SOURCE_TYPES, first_call=False),
                "data_availablity_panel_search": build_data_availablity_panel_search(macro="cs_windows_idx", by="source", values=WINDOWS_AD_SOURCES) + build_data_availablity_panel_search(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_AD_SOURCE_TYPES, first_call=False),
                "source_latency_search": build_source_latency_search(macro="cs_windows_idx", by="source", values=WINDOWS_AD_SOURCES) + " | append [ | search " + build_source_latency_search(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_AD_SOURCE_TYPES) + "]",
                "earliest_time": "-1d@d",
                "latest_time": "now",
            }
        ],
    },
    {
        "name": "Windows DNS",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Microsoft Windows",
                "link": "https://splunkbase.splunk.com/app/742/"
            }
        ],
        "metadata_count_search": """| tstats count where index=* source IN ({dns_sources}) OR sourcetype IN ({dns_sourcetypes}) """.format(
            dns_sources=WINDOWS_DNS_SOURCES,
            dns_sourcetypes=WINDOWS_DNS_SOURCE_TYPES,
        ),
        "macro_configurations": [
            {
                "macro_name": "cs_windows_idx",
                "label": "Windows DNS Data",
                "important_fields": {
                    "WinEventLog:DNS Server": {"EventCode": "50", "Message": "50", "SourceName": "90", "TaskCategory": "50", "ComputerName": "50"},
                    "MSAD:NT6:DNS": {"context": "50", "name": "50", "query_type": "50", "questionname": "50", "src": "50", "vendor_dns_action": "50"},
                    "MSAD:NT6:DNS-Health": {"OperatingSystem": "50", "Name": "50", "LogFilePath": "50", "DsPollingInterval": "50", "MaxCacheTTL": "50"},
                    "MSAD:NT6:DNS-Zone-Information": {"Aging": "50", "AllowUpdate": "50", "ContainerName": "50", "DnsServerName": "50", "DsIntegrated": "50"}
                },
                "search": lambda imp: (
                    build_search_query(macro="cs_windows_idx", by="source", values=WINDOWS_DNS_SOURCES, important_fields=imp) +
                    build_search_query(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_DNS_SOURCE_TYPES, important_fields=imp, first_call=False)
                ),
                "host_reviewer_search": build_host_reviewer_search(by="source", values=WINDOWS_DNS_SOURCES) + " | append [" + build_host_reviewer_search(by="sourcetype", values=WINDOWS_DNS_SOURCE_TYPES) + "]",
                "sources_reviewer_search": build_source_reviewer_search(by="source", values=WINDOWS_DNS_SOURCES) + build_source_reviewer_search(by="sourcetype", values=WINDOWS_DNS_SOURCE_TYPES, first_call=False),
                "data_availablity_panel_search": build_data_availablity_panel_search(macro="cs_windows_idx", by="source", values=WINDOWS_DNS_SOURCES) + build_data_availablity_panel_search(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_DNS_SOURCE_TYPES, first_call=False),
                "source_latency_search": build_source_latency_search(macro="cs_windows_idx", by="source", values=WINDOWS_DNS_SOURCES) + " | append [ | search " + build_source_latency_search(macro="cs_windows_idx", by="sourcetype", values=WINDOWS_DNS_SOURCE_TYPES) + "]",
                "earliest_time": "-1d@d",
                "latest_time": "now",
            }
        ],
    },
    {
        "name": "Lansweeper",
        "app_dependencies": [
            {
                "label": "Lansweeper Add-on for Splunk",
                "link": "https://splunkbase.splunk.com/app/5418/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_lansweeper",
                "label": "Lansweeper Data",
                "search_by": "sourcetype",
                "search_values": "lansweeper:asset:*",
                "earliest_time": "-2d@d",
                "latest_time": "now",
                "important_fields": {
                    "lansweeper:asset:*" : {"antivirus_name": "30", "assetBasicInfo.domain": "30", "assetBasicInfo.ipAddress": "30", "assetBasicInfo.mac": "30", "AssetName": "30"}
                }
            }
        ],
    },
    {
        "name": "Linux",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Unix and Linux",
                "link": "https://splunkbase.splunk.com/app/833/"
            },
            {
                "label": "Linux Auditd Technology Add-On",
                "link": "https://splunkbase.splunk.com/app/4232/"
            }
        ],
        "label": "Linux/Unix",
        "macro_configurations": [
            {
                "macro_name": "cs_linux",
                "label": "Linux Data",
                "search_by": "sourcetype",
                "search_values": "usersWithLoginPrivs,cyences:linux:groups,cyences:linux:users,cyences:aix:groups,interfaces,df,Unix:ListeningPorts,Unix:Service,Unix:Version,Unix:Uptime,hardware,linux_secure,linux:audit,linux:package",
                "earliest_time": "-2d@d",
                "latest_time": "now",
                "important_fields": {
                    "usersWithLoginPrivs": {"GID": "50", "HOME_DIR": "50", "UID": "50", "USER_INFO": "50", "USERNAME": "50"},
                    "cyences:linux:groups": {"group_name": "50", "users": "50"},
                    "cyences:linux:users": {"SUDOACCESS": "50", "HOME_DIR": "50", "UID": "50", "USER_INFO": "50", "USERNAME": "50"},
                    "cyences:aix:groups": {"group_name": "50", "users": "50", "admins": "50"},
                    "interfaces": {"interface": "50", "ip": "50", "RXBytes": "50", "Speed": "50", "TXBytes": "50"},
                    "df": {"Avail": "50", "Filesystem": "50", "MountedOn": "50", "UsePct": "50", "Used": "50"},
                    "Unix:ListeningPorts": {"dest_ip": "95", "dest_port": "95", "dvc_id": "95", "transport": "95", "user": "95"},
                    "Unix:Service": {"ACTIVE": "95", "DESCRIPTION": "95", "dest": "95", "service_name": "95", "status": "95"},
                    "Unix:Version": {"cpu_architecture": "50", "os": "50", "os_name": "50", "os_release": "50", "dest": "50"},
                    "Unix:Uptime": {"SystemUpTime": "50"},
                    "hardware": {"cpu_cores": "50", "cpu_freq": "50", "RealMemoryMB": "50", "SwapMemoryMB": "50", "cpu_type": "50"},
                    "linux_secure": {"dest": "95", "dvc": "95", "name": "95", "user_name": "95", "process": "95"},
                    "linux:audit": {"type": "95", "pid": "95", "subj": "95", "msg": "95", "comm": "95"},
                    "linux:package": {"action":"3", "package":"3", "version":"3", "arch":"3"}
                }
            }
        ],
    },
    {
        "name": "VPN",
        "app_dependencies": [],
        "metadata_count_search": '`cs_vpn_indexes` dest_category="vpn_auth" | stats count ',
        "macro_configurations": [
            {
                "macro_name": "cs_vpn_indexes",
                "label": "VPN Data (indexes)",
                "search": '`cs_vpn_indexes` dest_category="vpn_auth" | stats count by index, sourcetype',
                "host_reviewer_search": '`cs_vpn_indexes` dest_category="vpn_auth" | stats count by sourcetype host | rename sourcetype as sources',
                "sources_reviewer_search": '`cs_vpn_indexes` dest_category="vpn_auth" | stats dc(host) as host_count values(index) as index by sourcetype | rename sourcetype as sources',
                "data_availablity_panel_search": '`cs_vpn_indexes` dest_category="vpn_auth" | head 1 | stats count | eval label="`cs_vpn_indexes` dest_category=vpn_auth" ',
                "source_latency_search": '`cs_vpn_indexes` dest_category="vpn_auth" | eval diff=(_indextime - _time) / 60 | stats max(diff) as max_delay avg(diff) as avg_delay by sourcetype | rename sourcetype as sources',
                "earliest_time": "-1d@d",
                "latest_time": "now",
            }
        ],
    },
    {
        'name': 'Authentication',
        "app_dependencies": [],
        "metadata_count_search": '`cs_authentication_indexes` tag=authentication | stats count ',
        "macro_configurations": [
            {
                "macro_name": "cs_authentication_indexes",
                "label": "Authentication Data (indexes)",
                "search": '`cs_authentication_indexes` tag=authentication | stats count by index, sourcetype',
                "host_reviewer_search": '`cs_authentication_indexes` tag=authentication | stats count by sourcetype host | rename sourcetype as sources',
                "sources_reviewer_search": '`cs_authentication_indexes` tag=authentication | stats dc(host) as host_count values(index) as index by sourcetype | rename sourcetype as sources',
                "data_availablity_panel_search": '`cs_authentication_indexes` tag=authentication | head 1 | stats count | eval label="`cs_authentication_indexes`  tag=authentication" ',
                "source_latency_search": '`cs_authentication_indexes` tag=authentication | eval diff=(_indextime - _time) / 60 | stats max(diff) as max_delay avg(diff) as avg_delay by sourcetype | rename sourcetype as sources',
                "earliest_time": "-1d@d",
                "latest_time": "now",
            }
        ],
    },
    {
        'name': 'Radius Authentication',
        "app_dependencies": [
            {
                "label": "Palo Alto Networks Add-on",
                "link": "https://splunkbase.splunk.com/app/2757/"
            }
        ],
        "metadata_count_search": '`cs_radius_authentication_indexes` dest_category="radius_auth" | stats count ',
        "macro_configurations": [
            {
                "macro_name": "cs_radius_authentication_indexes",
                "label": "Radius Authentication Data (indexes)",
                "search": '`cs_radius_authentication_indexes` dest_category="radius_auth" | stats count by index, sourcetype',
                "host_reviewer_search": '`cs_radius_authentication_indexes` dest_category="radius_auth" | stats count by sourcetype host | rename sourcetype as sources',
                "sources_reviewer_search": '`cs_radius_authentication_indexes` dest_category="radius_auth" | stats dc(host) as host_count values(index) as index by sourcetype | rename sourcetype as sources',
                "data_availablity_panel_search": '`cs_radius_authentication_indexes` dest_category="radius_auth" | head 1 | stats count | eval label="`cs_radius_authentication_indexes` dest_category=radius_auth" ',
                "source_latency_search": '`cs_radius_authentication_indexes` dest_category="radius_auth" | eval diff=(_indextime - _time) / 60 | stats max(diff) as max_delay avg(diff) as avg_delay by sourcetype | rename sourcetype as sources',
                "earliest_time": "-7d@d",
                "latest_time": "now",
            }
        ],
    },
    {
        "name": "MSSQL",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Microsoft SQL Server",
                "link": "https://splunkbase.splunk.com/app/2648/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_mssql",
                "label": "MSSQL Data",
                "search_by": "sourcetype",
                "search_values": "mssql:audit,mssql:audit:json",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "mssql:audit": {"database_principal_name": "50", "server_principal_name": "50", "client_ip": "50", "application_name": "50", "server_instance_name": "50"},
                    "mssql:audit:json": {"database_principal_name": "50", "server_principal_name": "50", "client_ip": "50", "application_name": "50", "server_instance_name": "50"}, 
                }
            }
        ],
    },
    {
        "name": "Oracle",
        "app_dependencies": [
            {
                "label": "Splunk Add-on for Oracle",
                "link": "https://splunkbase.splunk.com/app/1910/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_oracle",
                "label": "Oracle Data",
                "search_by": "sourcetype",
                "search_values": "oracle:audit:xml,oracle:audit:unified,oracle:audit:text",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "oracle:audit:xml": {"ACTION_NAME": "50", "database_name": "50", "DBUSERNAME": "50", "SQL_TEXT": "50", "RETURN_CODE": "50"},
                    "oracle:audit:unified": {"vendor_action": "50", "DB_UNIQUE_NAME": "50", "DB_User": "50", "command": "50", "RETURNCODE": "50"},
                    "oracle:audit:text": {"ACTION_NAME": "50", "database_name": "50", "DBUSERNAME": "50", "SQL_TEXT": "50", "RETURN_CODE": "50"}
                }
            }
        ],
    },
    {
        "name": "DUO",
        "app_dependencies": [
            {
                "label": "Cisco Security Cloud",
                "link": "https://splunkbase.splunk.com/app/7404/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_duo",
                "label": "DUO Data",
                "search_by": "sourcetype",
                "search_values": "cisco:duo:authentication",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "cisco:duo:authentication": { "user": "50", "result": "50", "reason": "50", "factor": "50", "integration": "50" }
                }
            }
        ],
    },
    {
        "name": "Forcepoint DLP",
        "app_dependencies": [
            {
                "label": "Forcepoint DLP",
                "link": "https://splunkbase.splunk.com/app/6507"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_forcepoint_dlp",
                "label": "Forcepoint DLP Data",
                "search_by": "sourcetype",
                "search_values": "FP_DLP",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "FP_DLP" : { "SourceIP": "50", "Destination": "50", "User": "50", "Action": "50", "MessageDetails": "50" }
                }
            }
        ],
    },
    {
        "name": "Delinea PAM",
        "app_dependencies": [
            {
                "label": "Delinea PAM",
                "link": "https://splunkbase.splunk.com/app/6954/"
            }
        ],
        "macro_configurations": [
            {
                "macro_name": "cs_delinea_pam",
                "label": "Delinea PAM Data",
                "search_by": "sourcetype",
                "search_values": "centrify_css_syslog",
                "earliest_time": "-1d@d",
                "latest_time": "now",
                "important_fields": {
                    "centrify_css_syslog" : { "Src_IP": "70", "suser": "70", "msg": "70", "fname": "60", "action_event": "80", "cs3": "70" }
                }
            }
        ],
    },
]

for product in PRODUCTS:
    product["app_dependency_search"] = build_app_dependency_search(product["app_dependencies"])
    metadata_count_search = "| tstats count where index=* "
    product["macro_configurations"] = resolve_macro_configurations(product["macro_configurations"])
    for macro_config in product["macro_configurations"]:
        if not macro_config.get("search"):
            macro_config["search"] = build_search_query(
                macro=macro_config["macro_name"],
                by=macro_config["search_by"],
                values=macro_config["search_values"],
                important_fields=macro_config.get("important_fields", dict()),
            )
        if not macro_config.get("host_reviewer_search"):
            macro_config["host_reviewer_search"] = build_host_reviewer_search(
                by=macro_config["search_by"],
                values=macro_config["search_values"],
            )
        if not macro_config.get("sources_reviewer_search"):
            macro_config["sources_reviewer_search"] = build_source_reviewer_search(
                by=macro_config["search_by"],
                values=macro_config["search_values"],
            )
        if not product.get("metadata_count_search"):
            metadata_count_search += build_metadata_count_search(
                by=macro_config["search_by"],
                values=macro_config["search_values"],
            )
        if not macro_config.get("data_availablity_panel_search"):
            macro_config["data_availablity_panel_search"] = build_data_availablity_panel_search(
                macro=macro_config["macro_name"],
                by=macro_config["search_by"],
                values=macro_config["search_values"],
            )
        if not macro_config.get("source_latency_search"):
            macro_config["source_latency_search"] = build_source_latency_search(
                macro=macro_config["macro_name"],
                by=macro_config["search_by"],
                values=macro_config["search_values"],
            )

    if not product.get("metadata_count_search"):
        product["metadata_count_search"] = metadata_count_search[:-3]