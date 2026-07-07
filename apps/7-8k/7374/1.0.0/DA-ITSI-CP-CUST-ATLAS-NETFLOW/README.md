## Summary
The ITSI Content Pack for NetFlow from Presidio Splunk Solutions is specifically designed to monitor the health and performance of network infrastructure. It leverages Splunk ITSI to provide in-depth analysis and visualization of network traffic, flows, and interface metrics, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their network infrastructure.

* Comprehensive Network Monitoring: Offers detailed insights into network traffic volume, flow analysis, and interface performance, enabling optimized network management.
* Critical Network Health Tracking: Monitors the real-time operational status of network components, helping IT professionals swiftly identify and address potential issues.
* Enhanced Network Efficiency: Facilitates better decision-making on network resource allocation and adjustments by analyzing performance trends and detecting inefficiencies.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Splunk Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for NetFlow contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive view of network health and performance.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Splunk Products, visit our [website](https://atlas.presidio.com).

### Services
NetFlow monitoring encompasses several specialized services, each targeting specific aspects of network performance:

1. Network Health
    * Description: Network Health is the overarching service that encompasses all aspects of network performance and health. It relies on detailed monitoring of traffic, flow, and interface metrics to provide a comprehensive view.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
2. Traffic Monitoring
    * Description: Traffic Monitoring is essential for understanding the amount and type of data being transferred over the network. It depends on analyzing traffic volume, protocol distribution, and identifying top talkers.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
3. Flow Analysis
    * Description: Flow Analysis focuses on the behavior of network sessions. It requires detailed metrics on the number of flows, their duration, and direction to identify potential issues.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
4. Interface Monitoring
    * Description: Interface Monitoring ensures that network interfaces are performing optimally and not overburdened. It relies on metrics like utilization and error rates.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Traffic Volume
    * Description: Monitor the amount of data being transferred over the network.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
2. Top Talkers
    * Description: Identify the top sources and destinations of traffic.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
3. Protocol Dist
    * Description: Monitor the types of protocols being used and their respective traffic volumes.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
4. Flow Count
    * Description: Track the number of flows being created and terminated.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
5. Latency
    * Description: Measure the time it takes for data to travel from the source to the destination.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
6. Interface Util
    * Description: Monitor the utilization of network interfaces.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
7. Errors
    * Description: Track the rate of errors on the network.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)
8. Packet Loss
    * Description: Monitor the percentage of packets that are lost during transmission.
    * Source: [docs.netflowlogic.com](https://docs.netflowlogic.com/integrations-and-apps/integrations-with-splunk/)

### Relationships
#### Dependencies:
Services are interconnected; for instance, Network Health is dependent on Traffic Monitoring, Flow Analysis, and Interface Monitoring. Similarly, Traffic Monitoring relies on Volume Analysis, Protocol Distribution, and Top Talkers.

#### Hierarchical Structure:
Some services form a hierarchy, such as Traffic Monitoring depending on Volume Analysis, Protocol Distribution, and Top Talkers, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for NetFlow](https://splunkbase.splunk.com)

[Splunk App for Content Packs](https://splunkbase.splunk.com/app/5391)

[Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html)

## Troubleshooting

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

[Github and Readme](https://www.github.com/kinneygroup)

atlassupport@presidio.com

## Contact

To provide feedback, visit our [Github and Readme](https://www.github.com/kinneygroup) for our content packs.

atlassupport@presidio.com

For more information about Presidio Splunk Solutions' Splunk Products, visit our [website](https://atlas.presidio.com).

## Version History

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.1   | 05/21/24 | Initial Preview Release    |
| 1.0.0   | 05/14/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)