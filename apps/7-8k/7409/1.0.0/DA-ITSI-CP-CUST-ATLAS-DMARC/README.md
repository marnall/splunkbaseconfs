## Summary
The ITSI Content Pack for DMARC from Presidio Splunk Solutions is specifically designed to monitor the health and enforcement of DMARC policies across email domains. It leverages Splunk ITSI to provide in-depth analysis and visualization of DMARC reports, ensuring the integrity and security of email communications. This content pack is an essential tool for IT professionals looking to enhance email security and compliance.

* Comprehensive DMARC Monitoring: Offers detailed insights into DMARC policy enforcement, domain spoofing attempts, and email authentication mechanisms, enabling optimized email security.
* Critical Email Domain Tracking: Monitors the real-time operational status of email domains, helping IT professionals swiftly identify and address potential issues.
* Enhanced Email Authentication: Facilitates better decision-making on email authentication and policy enforcement by analyzing trends and detecting anomalies across email traffic.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for DMARC contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive view of DMARC policy enforcement and email authentication mechanisms.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
DMARC monitoring encompasses several specialized services, each targeting specific aspects of email security and policy enforcement:

1. DMARC Monitoring
    * Description: Centralized monitoring of DMARC policies and their enforcement across email domains.
2. Email Domain
    * Description: Monitoring the domains from which emails claim to originate.
3. Authentication Mechanisms
    * Description: Monitoring the mechanisms used to authenticate emails, including SPF and DKIM.
4. Report Analysis
    * Description: Analyzing DMARC aggregate and forensic reports to identify trends and anomalies.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Domain Spoofing Attempts
    * Description: Number of emails failing DMARC checks due to domain spoofing.
2. Delivery Error Rate
    * Description: Percentage of emails that failed to be delivered.
3. SPF Authentication Success Rate
    * Description: Percentage of emails passing SPF checks.
4. DKIM Authentication Success Rate
    * Description: Percentage of emails passing DKIM checks.
5. Aggregate Report Count
    * Description: Number of DMARC aggregate reports received.
6. Forensic Report Count
    * Description: Number of DMARC forensic reports received.
7. Policy Enforcement Rate
    * Description: Percentage of emails subjected to DMARC policy actions (none, quarantine, reject).
8. Bounce Rate
    * Description: Percentage of emails that bounced back.
9. Volume Spike Detection
    * Description: Detection of unusual spikes in email volume.

### Relationships
#### Dependencies:
Services are interconnected; for instance, DMARC Monitoring is dependent on the Email Domain, Authentication Mechanisms, and Report Analysis services. Similarly, Email Domain relies on Delivery Status and Volume to detect anomalies and ensure proper domain usage.

#### Hierarchical Structure:
Some services form a hierarchy, such as Authentication Mechanisms depending on SPF and DKIM Authentication, illustrating a layered approach to email security where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for DMARC](https://splunkbase.splunk.com)

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

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.1   | 6/6/24 | Initial Preview Release    |
| 1.0.0   | 5/15/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)