## Summary
The ITSI Content Pack for pfSense from Presidio Splunk Solutions is specifically designed to monitor and manage the security, performance, and log data of pfSense networks. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for pfSense, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and security of their network infrastructure.

* Comprehensive Network Security: Monitors and manages the security aspects of the network, including intrusion detection and firewall activities.
* Detailed Traffic Analysis: Analyzes network traffic to identify patterns, bandwidth usage, and potential anomalies.
* Efficient Log Management: Collects, parses, and stores logs from various network devices and applications for analysis and troubleshooting.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions's Splunk Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for pfSense contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for pfSense networks.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio's Splunk Products, visit our [website](https://atlas.presidio.com).

### Services
pfSense monitoring encompasses several specialized services, each targeting specific aspects of network performance and security:

1. Network Security
    * Description: Monitors and manages the security aspects of the network, including intrusion detection and firewall activities.
2. Intrusion Detection
    * Description: Monitors network traffic for suspicious activities and potential threats using tools like Snort.
3. Firewall Management
    * Description: Manages firewall rules and logs to control network traffic and prevent unauthorized access.
4. Traffic Analysis
    * Description: Analyzes network traffic to identify patterns, bandwidth usage, and potential anomalies.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/CIM/6.0.4/User/NetworkTraffic)
5. Log Management
    * Description: Collects, parses, and stores logs from various network devices and applications for analysis and troubleshooting.
6. Bandwidth Monitoring
    * Description: Monitors the usage of network bandwidth to identify high-usage IPs and potential network congestion.
7. Log Parsing
    * Description: Ensures that logs are properly parsed and fields are extracted for accurate querying and analysis.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Total Data Sent and Received
    * Description: Monitor the total bytes from source and destination IPs.
2. Snort Alerts
    * Description: Monitor for Snort alerts indicating potential security threats.
3. Firewall Logs
    * Description: Ensure all logs from pfSense are being sent to Splunk.
4. Failed Login Attempts
    * Description: Track the number of failed login attempts to identify potential security threats.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/CIM/6.0.4/User/Authentication)
5. Unusual Login Locations
    * Description: Monitor logins from unusual or unexpected geographic locations.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/CIM/6.0.4/User/Authentication)
6. Denied Connections
    * Description: Monitor traffic that is denied based on firewall rules.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/CIM/6.0.4/User/NetworkTraffic)
7. Allowed Connections
    * Description: Monitor traffic that is allowed based on firewall rules.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/CIM/6.0.4/User/NetworkTraffic)
8. Bandwidth Usage
    * Description: Identify which IPs are using the most bandwidth.
9. Traffic Flow
    * Description: Monitor the flow of data across network infrastructure components.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/CIM/6.0.4/User/NetworkTraffic)
10. Anomalies and Suspicious Traffic
    * Description: Use raw Snort alarms to investigate suspicious traffic.
11. Log Parsing and Field Extraction
    * Description: Ensure logs are properly parsed and fields are extracted for accurate querying.
12. Event Details
    * Description: Monitor specific event details for deeper insights.
13. Error Logs and Alerts
    * Description: Regularly review error logs and set up alerts for critical issues.
    * Source: [GitHub](https://github.com/barakat-abweh/ta-pfsense)
14. Network Throughput
    * Description: Monitor the usage of network bandwidth to identify high-usage IPs and potential network congestion.
    * Source: [GitHub](https://github.com/barakat-abweh/ta-pfsense)
15. Data Integrity and Completeness
    * Description: Ensure all expected data is being ingested without loss.
    * Source: [GitHub](https://github.com/barakat-abweh/ta-pfsense)

### Relationships
#### Dependencies:
Services are interconnected; for instance, Network Security is dependent on Intrusion Detection and Firewall Management. Similarly, Traffic Analysis relies on Bandwidth Monitoring to identify high-usage IPs and potential network congestion.

#### Hierarchical Structure:
Some services form a hierarchy, such as Network Security depending on Intrusion Detection and Firewall Management, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for pfSense](https://splunkbase.splunk.com/app/1527)

[Splunk App for Content Packs](https://splunkbase.splunk.com/app/5391)

[Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html)

## Troubleshooting

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

[Github and Readme](https://www.github.com/kinneygroup)

atlassupport@presidio.com

## Contact

To provide feedback, visit our [Github and Readme](https://www.github.com/kinneygroup) for our content packs.

atlassupport@presidio.com

For more information about Presidio's Splunk Products, visit our [website](https://atlas.presidio.com).

## Version History

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.1   | 05/23/24 | Initial Preview Release    |
| 1.0.0   | 05/14/25 | Documentation Update       |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)