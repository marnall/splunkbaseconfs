## Summary
The ITSI Content Pack for Rubrik from Presidio Splunk Solutions is specifically designed to monitor system health related to Rubrik environments. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for Rubrik, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their Rubrik infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into Rubrik cluster performance, node metrics, storage health, and network throughput, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of Rubrik clusters and nodes, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for Rubrik contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for Rubrik environments.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions Products, visit our [website](https://atlas.presidio.com).

This Content Pack's KPIs are normalized to the Splunk Common Information Model and depend on either a Technical Add-on from SplunkBase or user-configured field aliases to comply with the [Common Information Model Documents](https://docs.splunk.com/Documentation/CIM/5.3.2/User/Overview).

### Services
Rubrik monitoring encompasses several specialized services, each targeting specific aspects of system performance:

1. RubrikCluster
    * Description: Represents individual nodes within the Rubrik Cluster.
2. Storage
    * Description: Manages disk health and capacity utilization within a node.
3. Network
    * Description: Manages network throughput and latency within a node.
4. Compute
    * Description: Manages CPU and memory usage within a node.
5. Security
    * Description: Manages access and audit logs within a node.

### Relationships
#### Dependencies:
Services are interconnected; for instance, the Cluster service is dependent on the Nodes service. Similarly, Nodes rely on various subsystems like Storage, Network, Compute, Services, and Security to function properly.

#### Hierarchical Structure:
Some services form a hierarchy, such as Nodes depending on Storage, Network, Compute, Services, and Security, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Rubrik](https://splunkbase.splunk.com)

[Splunk App for Content Packs](https://splunkbase.splunk.com/app/5391)

[Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html)

## Troubleshooting

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

[Github and Readme](https://www.github.com/kinneygroup)

atlassupport@presidio.com

## Contact

To provide feedback, visit our [Github and Readme](https://www.github.com/kinneygroup) for our content packs.

atlassupport@presidio.com

For more information about Presidio Splunk Solutions Products, visit our [website](https://atlas.presidio.com)

## Version History

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.1   | 8/26/24 | Initial Preview Release    |
| 1.0.0   | 5/14/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)