## Summary
The ITSI Content Pack for GCP Compute from Presidio Splunk Solutions is specifically designed to monitor system health related to Google Cloud Platform (GCP) Compute services. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for GCP Compute, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into GCP Compute instance performance, CPU metrics, disk operations, and network throughput, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of GCP Compute instances and associated resources, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about KPresidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for GCP Compute contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for GCP Compute services.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
GCP Compute monitoring encompasses several specialized services, each targeting specific aspects of instance performance:

1. GCP Compute Infrastructure
    * Description: Core infrastructure for running virtual machines and managing compute resources.

2. Instance Monitoring
    * Description: Monitors the performance and health of virtual machine instances.

3. Network Monitoring
    * Description: Monitors the performance and health of network components.

4. Security Monitoring
    * Description: Ensures the security of network components through firewall rules and access controls.

5. Storage Monitoring
    * Description: Monitors the performance and health of storage resources.


### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. CPU Usage
    * Description: Measures the CPU usage of instances.

2. CPU Utilization
    * Description: Tracks the percentage of CPU usage across instances.

3. Instance Uptime
    * Description: Measures the uptime of virtual machine instances.

4. Memory Usage
    * Description: Tracks the memory usage of instances.

5. Network Errors
    * Description: Tracks the number of errors in network operations.

6. Network Latency
    * Description: Measures the latency within the network.

7. Network Throughput
    * Description: Measures the network throughput of instances.

8. Network Traffic
    * Description: Measures the inbound and outbound network traffic.

9. Packet Loss
    * Description: Monitors the rate of packet loss in the network.

10. Disk I/O Operations
    * Description: Monitors the read/write operations on disks.

11. Network Latency
    * Description: Measures the latency within the network.

12. Error Rates
    * Description: Tracks the error rates in storage operations.

13. Storage Usage
    * Description: Tracks the usage of storage resources.

14. Firewall Rule Changes
    * Description: Monitors changes to firewall rules.

15. IAM Policy Changes
    * Description: Monitors changes to IAM policies for instances.

16. Policy Changes
    * Description: Monitors changes to security policies.

17. Instance Metadata Changes
    * Description: Tracks changes to instance metadata.

18. Patch Compliance
    * Description: Measures the compliance of instances with security patches.

19. Security Incidents
    * Description: Tracks the number of security incidents involving instances.

20. Unauthorized Access Attempts
    * Description: Tracks attempts to access instances without authorization.


### Relationships
#### Dependencies:
Services are interconnected; for instance, Compute Infrastructure is dependent on Instance Management, Network Management, and Storage Management. Similarly, Network Management relies on Network Monitoring and Network Security to ensure performance and security.

#### Hierarchical Structure:
Some services form a hierarchy, such as Instance Management depending on Instance Monitoring and Instance Security, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for GCP](https://splunkbase.splunk.com)

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

| Version | Date  | Description               |
|---------|-------|---------------------------|
| 0.0.1   | 06/04/24 | Initial Preview Release   |
| 1.0.0   | 05/19/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)
