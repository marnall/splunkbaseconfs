CLOSE_REASONS = {
    'other': 1,
    'benign activity': 2,
    'true positive': 3,
    'environment misconfiguration': 4,
    'alert recently customized': 5,
    'inaccurate alert logic': 6,
    'authorized activity': 7
}
MAX_DAYS_BACK = 180
THREAT_MODEL_ENUM_ID = 5821
ALERT_STATUSES = {'new': 1, 'under investigation': 2, 'closed': 3}
ALERT_SEVERITIES = {'high': 0, 'medium': 1, 'low': 2}
ALERT_CATEGORIES = {"privilege escalation": "1",
                    "lateral movement": "2",
                    "reconnaissance": "0",
                    "exploitation": "3",
                    "exfiltration": "4",
                    "intrusion": "5",
                    "denial of service": "7",
                    "other": "9",
                    "obfuscation (anti-forensics)": "10"}
app_name = 'varonis_saas_realm'
