"""This is a field mapping of API fields to Syslog fields to normalize the data for data model."""
mapping = {
    "jobId": "simulation_id",
    "runId": "test_id",
    "MITRE_Tactic": [
        {
            (("tacticId", "(", ")"), ("value", " ", "")): "mitre_tactic",
        }
    ],
    "attackerOSType": "attacker_platform",
    "planName": "plan_name",
    "Security_Controls": [
        {
            "value": "security_control_category"
        }
    ],
    "destinationIp": "destination_ip",
    "deploymentId": [
        "deployment_id"
    ],
    "attackerNodeName": "attacker",
    "targetOSType": "target_platform",
    "planId": "plan_id",
    "planRunId": "plan_run_id",
    "moveId": "attack_id",
    "Threat_Name": [
        {
            "value": "threat_name"
        }
    ],
    "sourceIp": "source_ip",
    "MITRE_Sub_Technique": [
        {
            "value": "mitre_sub_technique"
        }
    ],
    "moveDesc": "attack_description",
    "status": "result",
    "finalStatus": "status",
    "moveName": "attack_name",
    "NIST_Control": [
        {
            "value": "nist_control"
        }
    ],
    "moveTags": {
        "opponent": "attacker_profile",
        "impact": "leak_rate",
        "noiseLevel": "footprint",
        "approach": "attack_approach",
    },
    "MITRE_Technique": [
        {
            "value": "mitre_technique"
        }
    ],
    "targetNodeName": "target",
    "securityAction": "security_action",
    "behavioral": [
        {
            "value": "behavioral"
        }
    ],
    "packageName": "attack_phase",
    "lastStatusChangeDate": "last_change",
    "attackerOSVersion": "attacker_os_version",
    "direction": "direction",
    "executionTime": "simulation_time",
    "attackProtocol": "protocol",
    "targetOSVersion": "target_os_version",
    "srcNodeName": "source_host",
    "destNodeName": "destination_host",
    "sourcePort": ["source_port"],
    "Threat_Actor": [
        {
            "value": "threat_groups"
        }
    ],
    "labels": ["labels"],
    "assetName": "data_asset",
    "Attack_Type": [
        {
            "value": "attack_type"
        }
    ],
    "parameters": {
        "PROXY": [
            {
                "value": "proxy",
            }
        ],
        "SIMULATION_USER_DESTINATION": [
            {
                "value": "impersonated_user",
            }
        ],
        "HOST": [
            {
                "value": "host",
            }
        ],
        "FQDN_IP": [
            {
                "value": "fqdn_ip",
            }
        ],
        "REGISTRY": [
            {
                "value": "registry",
            }
        ],
        "PATH": [
            {
                "value": "path",
            }
        ],
        "URI": [
            {
                "value": "uri",
            }
        ],
        "CLIENT_HTTP_HEADERS": [
            {
                "value": "client_headers",
            }
        ],
        "COMMAND": [{"value": "command"}],
        "CONTENT_TYPE_HEADERS": [{"value": "content"}],
        "COOKIES": [{"value": "cookies"}],
        "BINARY": [{"value": "hash"}],
        "SERVER_HTTP_HEADERS": [{"value": "server_headers"}],
        "PORT": [{"value": "destination_port"}],
    },
    "testName": "test_name",
    "deploymentName": ["deployment_name"],
    "simulationEvents": ["simulation_data"],
    "remediationData": "remedation_suggestions",
    "resultCode" : "result_code",
    "resultDetails" : "result_details",
    "originalExecutionId":"tracking_id",
    "securityEvents": [
        {"alertName":"alert_name"}
    ],
    "loggedBy":"logged_by",
    "reportedBy": "reported_by",
    "preventedBy": "prevented_by",
    "alertedBy": "alerted_by",
}

