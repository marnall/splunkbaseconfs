## Summary
The ITSI Content Pack for Zscaler from Presidio Splunk Solutions is specifically designed to monitor system health related to Zscaler services. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for Zscaler, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into Zscaler service performance, including application, network, and user experience metrics, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of Zscaler services, helping IT professionals swiftly identify and address potential issues.
* Enhanced User Experience: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Details
The ITSI Content Pack for Zscaler contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive view of Zscaler service performance, helping to ensure optimal digital experiences.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

### Services
Zscaler monitoring encompasses several specialized services, each targeting specific aspects of performance:

1. Zscaler Digital Experience
    * Description: Monitors the overall digital experience by collecting and analyzing various performance and availability metrics.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
2. Application Performance
    * Description: Monitors the performance of critical applications, including load times and error rates.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
3. Network Performance
    * Description: Monitors network latency, packet loss, bandwidth utilization, and hop-by-hop performance metrics.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
4. User Experience
    * Description: Monitors user activity, page load times, transaction times, and session metrics.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
5. Database Performance
    * Description: Monitors database query performance, connection counts, and other relevant metrics to ensure database health.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
6. Service Response Times
    * Description: Measures the response times of critical services and APIs to ensure they are performing within acceptable thresholds.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
7. Network Traffic
    * Description: Measures inbound and outbound network traffic to detect potential bottlenecks or unusual activity.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
8. Service Dependencies
    * Description: Maps and monitors dependencies between services to understand the impact of one service's health on another.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
9. Security Events
    * Description: Monitors for security-related events, such as unauthorized access attempts or malware detections.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
10. Log Analysis
    * Description: Collects and analyzes logs for any anomalies or patterns that could indicate underlying issues.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. System Availability
    * Description: Uptime and downtime of the digital experience service.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
2. Response Times
    * Description: Measures application and API response times.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
3. Application Load Time
    * Description: Measures the time taken for applications to load.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
4. Application Error Rate
    * Description: Tracks the rate of errors occurring in applications.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
5. Network Latency
    * Description: Measures the delay in network communication.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
6. Packet Loss
    * Description: Tracks the percentage of packets lost during transmission.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
7. Bandwidth Utilization
    * Description: Monitors the amount of bandwidth being used.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
8. Response Time
    * Description: Measures the time taken to receive a response in the network session event.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
9. Transaction Time
    * Description: Tracks the time taken to complete user transactions.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
10. User Session Metrics
    * Description: Monitors metrics related to user sessions, such as duration and activity.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
11. Unauthorized Access Attempts
    * Description: Tracks attempts to access the system without authorization.
    * Source: [Zscaler Digital Experience Data Sheet](https://www.zscaler.com/resources/data-sheets/zscaler-digital-experience.pdf)
12. Database Query Response Time
    * Description: Measures the time taken to execute database queries.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
13. Database Connection Count
    * Description: Tracks the number of active database connections.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
14. Database Error Rate
    * Description: Monitors the rate of errors occurring in the database.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
15. API Response Time
    * Description: Measures the time taken for APIs to respond.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
16. Service Uptime
    * Description: Tracks the uptime of critical services.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
17. Service Error Rate
    * Description: Monitors the rate of errors in service responses.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
18. Inbound Traffic Volume
    * Description: Measures the volume of incoming network traffic.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
19. Outbound Traffic Volume
    * Description: Measures the volume of outgoing network traffic.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
20. Dependency Health
    * Description: Monitors the health of dependent services.
    * Source: [Zscaler and Splunk Solution Brief](https://www.zscaler.com/resources/solution-briefs/partner-splunk.pdf)
21. Malware Detections
    * Description: Monitors for the presence of malware.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
22. Security Incident Logs
    * Description: Analyzes logs for security incidents.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)
23. Log Collection Rate
    * Description: Measures the rate at which logs are collected.
    * Source: [Zscaler and Splunk Deployment Guide](https://help.zscaler.com/downloads/zscaler-technology-partners/operations/zscaler-and-splunk-deployment-guide/Zscaler-Splunk-Deployment-Guide-FINAL.pdf)

### Relationships
#### Dependencies:
Services are interconnected; for instance, Zscaler Digital Experience is dependent on Application Performance, Network Performance, and User Experience services. Similarly, Application Performance relies on Database Performance and Service Response Times.

#### Hierarchical Structure:
Some services form a hierarchy, such as Network Performance depending on Network Traffic, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Zscaler](https://splunkbase.splunk.com/app/3865)

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

| Version | Date  | Description               |
|---------|-------|---------------------------|
| 0.0.1   | 06/06/2024 | Initial Preview Release   |
| 1.0.0   | 05/14/2025 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)