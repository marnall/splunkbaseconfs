## Summary
The ITSI Content Pack for F5 BIG-IP from Presidio Splunk Solutions is specifically designed to monitor system health related to F5 BIG-IP. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for F5 BIG-IP, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into F5 BIG-IP performance, including load balancing, network metrics, application performance, and security events.
* Critical System Status Tracking: Monitors the real-time operational status of F5 BIG-IP components, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Details
The ITSI Content Pack for F5 BIG-IP contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for F5 BIG-IP environments.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

### Services
F5 BIG-IP monitoring encompasses several specialized services, each targeting specific aspects of system performance:

1. Load Balancer
    * Description: Manages the distribution of network or application traffic across multiple servers.
2. Network
    * Description: Handles network performance metrics such as throughput, latency, and packet loss.
3. Application
    * Description: Monitors application performance metrics like HTTP request/response time, application errors, and connection counts.
4. Security
    * Description: Manages security events including firewall events, access policy manager events, and application security manager events.
5. Global Traffic Management
    * Description: Manages global traffic metrics such as DNS query response time and DNS errors.
6. System Health
    * Description: Monitors overall system health metrics including CPU utilization, memory utilization, disk usage, and system uptime.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Load Balancer
    * Description: Manages the distribution of network or application traffic across multiple servers.
2. Network Throughput
    * Description: Measures the amount of data passing through the network.
3. Network Latency
    * Description: Measures the delay in data transmission across the network.
4. Packet Loss
    * Description: Measures the percentage of packets lost during transmission.
5. HTTP Response Time
    * Description: Measures the time taken for HTTP requests to be processed.
6. App Errors
    * Description: Counts the number of errors occurring in the application.
7. Connection Counts
    * Description: Measures the number of active connections to the application.
8. Firewall Events
    * Description: Counts the number of firewall-related events.
9. APM Events
    * Description: Counts the number of Access Policy Manager events.
10. ASM Events
    * Description: Counts the number of Application Security Manager events.
11. DNS Response Time
    * Description: Measures the time taken to respond to DNS queries.
12. DNS Errors
    * Description: Counts the number of errors occurring in DNS queries.
13. CPU Pct
    * Description: Measures the percentage of CPU utilization.
14. Memory Pct
    * Description: Measures the percentage of memory utilization.
15. Disk Usage
    * Description: Measures the percentage of disk space used.
16. System Uptime
    * Description: Measures the total uptime of the system.

### Relationships
#### Dependencies:
Services are interconnected; for instance, the Load Balancer is dependent on Network, Application, Security, and Global Traffic Management services. Similarly, Network performance relies on System Health to ensure network components are functioning correctly.

#### Hierarchical Structure:
Some services form a hierarchy, such as System Health being the foundational component that supports all other services, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for F5 BIG-IP](https://splunkbase.splunk.com)

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
| 0.0.1   | 6/10/24 | Initial Preview Release    |
| 1.0.0   | 5/14/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)