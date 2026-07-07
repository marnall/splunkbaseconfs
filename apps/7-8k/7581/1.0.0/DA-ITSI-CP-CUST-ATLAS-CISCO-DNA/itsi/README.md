## Summary

The ITSI Content Pack for Cisco DNA from Presidio Splunk Solutions is designed to monitor the health and performance of enterprise networks using Cisco DNA. It leverages Splunk ITSI to provide comprehensive insights into network devices, client health, and network services, ensuring optimal network operations. This content pack is an essential tool for IT professionals aiming to enhance network reliability and performance.

* Comprehensive Network Monitoring: Offers detailed insights into network device performance, client health, and network services, enabling optimized network management.
* Critical System Health Tracking: Monitors the real-time operational status of network devices and services, helping IT professionals swiftly identify and address potential issues.
* Enhanced Network Efficiency: Facilitates better decision-making on network adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

## Details

The ITSI Content Pack for Cisco DNA provides service definitions and KPIs ready to import into ITSI. The KPI thresholds and importance values are set to defaults, allowing for manual tuning to fit specific use cases. This content pack helps solve network performance issues by providing detailed monitoring and analysis of network health, client health, and network services.

For installation guidance, refer to the [Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/).

### Services

Cisco DNA monitoring encompasses several specialized services, each targeting specific aspects of network performance:

1. Overall Health
   * Description: Provides a global view of the health of the enterprise, including network devices and clients. It aggregates data from various aspects of the network, making it the central point for monitoring the entire system's health.


2. Network Health
   * Description: Provides detailed health information for network devices, focusing on the status and performance of network devices.


3. Client Health
   * Description: Provides detailed health information for wired and wireless client devices, focusing on the status and performance of client devices.


4. Network Services
   * Description: Monitors the health of network services like AAA and DHCP, which are critical for network operations.


5. AAA
   * Description: Monitors the AAA network service, crucial for authentication, authorization, and accounting.


6. DHCP
   * Description: Monitors the DHCP network service, essential for IP address management.


### KPIs

Each service utilizes specific KPIs to measure its effectiveness:


1. CPU Pct
   * Description: Monitors the CPU usage percentage of network devices.


2. Memory Usage
   * Description: Tracks the memory usage of network devices.


3. Interface Errors
   * Description: Counts the number of errors on network interfaces.


4. Packet Loss Pct
   * Description: Measures the percentage of packet loss on network devices.


5. Client Connection Time
   * Description: Measures the time taken for clients to connect to the network.


6. Client Throughput
   * Description: Tracks the data throughput for client devices.


7. Client Latency
   * Description: Measures the latency experienced by client devices.


8. Client Error Rate
    * Description: Counts the error rate for client connections.


9. Service Response Time
    * Description: Measures the response time of network services.


10. Service Error Rate
    * Description: Tracks the error rate of network services.


11. Auth Success Rate
    * Description: Measures the success rate of authentication requests.


12. Auth Response Time
    * Description: Tracks the response time for authentication requests.


13. Auth Failure Count
    * Description: Counts the number of failed authentication attempts.


14. Lease Success Rate
    * Description: Measures the success rate of DHCP lease assignments.


15. Lease Response Time
    * Description: Tracks the response time for DHCP lease requests.


16. Lease Failure Count
    * Description: Counts the number of failed DHCP lease attempts.


### Relationships

#### Dependencies:
Services are interconnected; for instance, the Overall Health service depends on Network Health, Client Health, and Network Services to provide a comprehensive view of the network's health.

#### Hierarchical Structure:
Some services form a hierarchy, such as Network Services depending on AAA and DHCP, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Cisco DNA](https://splunkbase.splunk.com)

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

| Version | Date  | Description                      |
|---------|-------|----------------------------------|
| 0.0.1   | 10/04/2024 | Initial release of the content pack |
| 1.0.0   | 05/19/2025 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)