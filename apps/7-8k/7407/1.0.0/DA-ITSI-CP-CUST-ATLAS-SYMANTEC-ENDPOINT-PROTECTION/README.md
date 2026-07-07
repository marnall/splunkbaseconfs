## Summary
The ITSI Content Pack for Symantec Endpoint Protection (SEP) from Presidio Splunk Solutions is specifically designed to monitor the health and performance of SEP across your network. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for SEP, ensuring that all endpoints are protected and compliant with security policies. This content pack is an essential tool for IT professionals looking to enhance the security and efficiency of their endpoint protection infrastructure.

* Comprehensive Endpoint Protection Monitoring: Offers detailed insights into the protection status, virus definitions, and policy compliance of endpoints, ensuring optimal security.
* Real-Time Threat Detection: Monitors and detects various types of threats, including viruses, malware, and spyware, enabling immediate response and mitigation.
* Enhanced System Performance: Tracks the impact of SEP on system performance, including CPU and memory usage, to ensure that endpoint protection does not hinder system operations.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for Symantec Endpoint Protection (SEP) contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. This content pack helps users monitor the overall protection status of endpoints, ensuring that virus definitions are up-to-date, real-time protection is enabled, and security policies are complied with.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
SEP monitoring encompasses several specialized services, each targeting specific aspects of endpoint protection:

1. Endpoint Protection
    * Description: Manages the overall protection status of endpoints, including real-time protection, virus definitions, and policy compliance.
2. Virus Definitions
    * Description: Ensures that all endpoints have the latest virus and spyware definitions.
3. Real-Time Protection
    * Description: Monitors and ensures that real-time protection features like Auto-Protect are enabled and functioning.
4. Policy Compliance
    * Description: Ensures that all endpoints comply with the defined security policies.
5. Threat Detection
    * Description: Monitors and detects various types of threats, including viruses, malware, and spyware.
6. System Performance
    * Description: Monitors the impact of Symantec Endpoint Protection on system performance, including CPU and memory usage.
7. Network Activity
    * Description: Monitors network traffic related to Symantec Endpoint Protection, including blocked and allowed connections.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Definition Status
    * Description: Status of virus definition updates.
2. Definition Age
    * Description: Age of the virus definitions on endpoints.
3. Auto-Protect Status
    * Description: Status of Auto-Protect.
4. Real-Time Enabled
    * Description: Check if real-time protection is enabled.
5. Compliance Status
    * Description: Compliance status of endpoints with security policies.
6. Non-Compliance Count
    * Description: Number of endpoints out of compliance.
7. Detected Threats
    * Description: Number of detected threats.
8. Threat Types
    * Description: Types of threats detected.
9. Resolved Threats
    * Description: Number of resolved threats.
10. CPU Usage
    * Description: CPU usage by SEP processes.
11. Memory Usage
    * Description: Memory usage by SEP processes.
12. Blocked Connections
    * Description: Number of blocked network connections.
13. Allowed Connections
    * Description: Number of allowed network connections.


### Relationships
#### Dependencies:
Services are interconnected; for instance, Endpoint Protection is dependent on Virus Definitions, Real-Time Protection, and Policy Compliance. Similarly, Virus Definitions rely on Update Distribution to ensure all endpoints receive the latest definitions.

#### Hierarchical Structure:
Some services form a hierarchy, such as Real-Time Protection depending on Threat Detection, illustrating a layered approach to protection where base metrics support broader security indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Symantec](https://splunkbase.splunk.com)

[Splunk App for Content Packs](https://splunkbase.splunk.com/app/5391)

[Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html)

## Troubleshooting

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

[Github and Readme](https://www.github.com/kinneygroup)

atlassupport@presidio.com

## Contact

To provide feedback, visit our [Github and Readme](https://www.github.com/kinneygroup) for our content packs.

atlassupport@presidio.com

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Version History

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.1   | 06/06/24 | Initial Preview Release    |
| 1.0.0   | 05/20/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)