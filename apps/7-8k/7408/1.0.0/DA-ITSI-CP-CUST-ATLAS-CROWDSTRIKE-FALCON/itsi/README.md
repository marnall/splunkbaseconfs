## Summary
The ITSI Content Pack for CrowdStrike-Falcon from Presidio Splunk Solutions is specifically designed to monitor system health related to the CrowdStrike Falcon platform. It leverages Splunk ITSI to provide in-depth analysis and visualization of detections, incidents, indicators, and authentications for CrowdStrike Falcon, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their security infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into the health and performance of the CrowdStrike Falcon system, including detections, incidents, indicators, and authentications.
* Critical System Status Tracking: Monitors the real-time operational status of CrowdStrike Falcon components, helping IT professionals swiftly identify and address potential issues.
* Enhanced Security Efficiency: Facilitates better decision-making on security measures and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for CrowdStrike-Falcon contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive view of the health and performance of the CrowdStrike Falcon system.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
CrowdStrike Falcon monitoring encompasses several specialized services, each targeting specific aspects of system performance:

1. System Health
    * Description: Monitors the overall health and performance of the CrowdStrike Falcon system.
2. Detections
    * Description: Monitors detections which may indicate a security threat.
3. Incidents
    * Description: Monitors incident scores, which are calculated based on patterns in detections found over time.
4. Indicators
    * Description: Monitors indicator security events.
5. Authentication
    * Description: Monitors authentication events in the CrowdStrike Falcon system.

### Relationships
#### Dependencies:
Services are interconnected; for instance, System Health is dependent on the health of Detections, Incidents, Indicators, and Authentication to provide a comprehensive view of system health.

#### Hierarchical Structure:
Some services form a hierarchy, such as System Health depending on the status of Detections, Incidents, Indicators, and Authentication, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for CrowdStrike](https://splunkbase.splunk.com/app/5082)

[Splunk App for Content Packs](https://splunkbase.splunk.com/app/5391)

[Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html)

## Troubleshooting

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

[Github and Readme](https://www.github.com/kinneygroup)

atlassupport@presidio.com

## Contact

To provide feedback, visit our [Github and Readme](https://www.github.com/kinneygroup) for our content packs.

atlassupport@presidio.com

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Version History

| Version | Date       | Description                |
|---------|------------|----------------------------|
| 0.0.1   | 06/06/2024 | Initial Preview Release    |
| 1.0.0   | 05/15/2025 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)