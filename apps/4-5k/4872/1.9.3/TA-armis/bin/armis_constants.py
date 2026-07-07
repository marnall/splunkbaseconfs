"""This file is for declaring constant."""

import os

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]
STATUS_FORCELIST = list(range(500, 600)) + [429, ]
RETRY_COUNT = 3
PER_DAY_SECONDS = 86400
NO_OF_SECONDS_ALLOWED = 7776000
input_type_list = ["armis_alerts", "armis_api_alerts", "armis_device", "armis_vulnerability"]
VULNERABILITIES_PARAMS_LENGTH = 2000
DEVICE_PARAMS_LENGTH = 2000
APPLICATION_PARAMS_LENGTH = 5000
VULN_MATCH_PARAMS_LENGTH = 5000
URL_FOR_VULN_MATCH = "https://{}/api/v1/vulnerability-match/"
#1000 chars allowed in vuln-match API : Without values of vuln-ids the url contains around 130 chars including other params
URL_FOR_APPLICATION = "https://{}/api/v1/device-applications/"
DEFAULT_DEVICE_FIELDS = "tags,biosType,biosVendor,biosVersion,boundaries,category,firmwareVersion,firstSeen,id,imei,ipAddress,ipv6,lastSeen,macAddress,manufacturer,meid,model,name,operatingSystem,operatingSystemVersion,osBuildNumber,osEdition,osKernelType,osKernelVersion,osLastLoginTime,osServicePack,osTcpIpStack,phoneNumber,publicIp,riskLevel,serialNumber,site,type,udid,customProperties"