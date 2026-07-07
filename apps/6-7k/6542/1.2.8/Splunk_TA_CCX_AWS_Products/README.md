**About Us:**

CyberCX is Australia’s greatest force of cyber security experts. Our highly skilled professional services team operates a 24x7 on-shore security operations centre (SOC) servicing corporate and public sector organisations across Australia and New Zealand, specialising in Security Operations services leveraging Splunk.

**Description:**

CCX Security Operations has taken it upon ourselves to develop a CCX Add-on for AWS Products to provide further CIM compliance coverage not only for logs ingested via 'Splunk Add-on for AWS'.
This TA was built using a large dataset and endeavours to be the most CIM compliant comprehensive field extraction for AWS various products listed.
The Technical Addon is designed for ingest based on an SQS-Based S3 "Custom Data Type" via the Splunk Add-on for AWS or Syslog and is to be used on Search Heads.

Listed products supported:

- AWS Network Firewall
- AWS Web Application Firewall
- AWS S3 VPC Flow
- AWS Macie
- AWS API Gateway Access Logs
- AWS Security Hub Custom (HEC|JSON)
- AWS Security Lake
- AWS Security Findings (Vulnerability)

**Features:**

- This TA currently supports logtypes tagged under the following CIM datamodels: Alert, Change, Network Traffic, DNS, Vulnerability and Web.

**Compatibility:**

| Splunk Versions | 10.4, 10.3, 10.2, 9.4   |
| -------------------------- | -------------------- |
| CIM                        | 8.x, 6.x             |
| Platforms                  | Platform independent |
| Vendor Products            | AWS Cloud Products   |
| Service Provider           | CyberCX              |

**Requirements:**

- To retrieve AWS Network Firewall logs based on an SQS-Based S3 "Custom Data Type" is required additional Add-on 'Splunk Add-on for AWS' version 7.10.0 or higher (https://splunkbase.splunk.com/app/1876/).
- This Add-on is intended to be installed on Search Heads and where 'Splunk Add-on for AWS' inputs are configured.
- The AWS S3 VPC Flow logs ingested via syslog has the field extractions dependencies on Add-on 'Splunk Add-on for AWS' version 7.10.0 or higher (https://splunkbase.splunk.com/app/1876/) and it is required to be installed along 'CCX Add-on for AWS Products'

**Installation:**

- To retrieve AWS Network Firewall logs based on an SQS-Based S3 "Custom Data Type" is required additional Add-on 'Splunk Add-on for AWS' version 7.10.0 or higher (https://splunkbase.splunk.com/app/1876/) installed where inputs is to be configured.
- This Add-on is intended to be installed on Search Heads and where 'Splunk Add-on for AWS' inputs are configured.
- The AWS S3 VPC Flow logs ingested via syslog has the field extractions dependencies on Add-on 'Splunk Add-on for AWS' version 7.10.0 or higher (https://splunkbase.splunk.com/app/1876/) and it is required to be installed along 'CCX Add-on for AWS Products'

**Addressed issues:**
For customers ingesting AWS security hub findings vulnerabilites logs.

- Disable the following tag field value pair: "eventtype=securityhub_events"
