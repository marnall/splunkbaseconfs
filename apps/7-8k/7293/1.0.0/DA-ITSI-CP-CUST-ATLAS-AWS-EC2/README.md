# AWS EC2 Performance Monitoring ITSI Content Pack

## Summary
The AWS EC2 Performance Monitoring ITSI Content Pack by Presidio Splunk Solutions is a comprehensive solution for monitoring and analyzing the performance of Amazon Web Services EC2 instances. It provides a suite of services and KPIs to track CPU, disk, and network utilization, ensuring that EC2 instances are running efficiently and effectively. This content pack is a valuable asset for system administrators and DevOps teams to proactively manage and optimize their cloud infrastructure.

- **In-depth Instance Monitoring**: Gain visibility into the performance of EC2 instances with detailed metrics on CPU, disk, and network usage.
- **Proactive Issue Detection**: Quickly identify and troubleshoot performance bottlenecks or system health issues to minimize downtime.
- **Optimized Cloud Operations**: Make informed decisions on resource management and scaling with real-time data and historical trends.

This content pack is open-source and can be found on [GitHub](https://www.github.com/kinneygroup).

## Details
The AWS EC2 Performance Monitoring ITSI Content Pack is designed to provide users with the tools necessary to monitor the key aspects of their EC2 instances. It includes predefined services and KPIs that can be easily imported into Splunk ITSI, offering a streamlined setup process. The content pack helps solve common problems related to resource utilization, system performance, and operational efficiency.

For detailed installation instructions, please refer to the [Presidio Splunk Solutions documentation](https://www.kinneygroup.com/installing-content-packs).

### Services
The content pack includes the following services, each representing a critical component of EC2 performance monitoring:
- **AWS EC2 Instance Performance**: The primary service that aggregates CPU, disk, and network performance data to provide a holistic view of instance health.
- **AWS EC2 CPU Performance**: Monitors CPU utilization and credit usage, crucial for processing capabilities and burstable performance instances.
- **AWS EC2 Disk Performance**: Tracks disk I/O and throughput, essential for storage subsystem performance.
- **AWS EC2 Network Performance**: Ensures adequate network bandwidth and connectivity for the instance.

### KPIs
Key Performance Indicators (KPIs) included in the content pack are designed to provide actionable insights into the performance of EC2 instances:
- **CPU Utilization**: Measures the percentage of compute units in use, indicating the processing load on the instance.
- **Disk I/O Operations**: Counts the read and write operations, reflecting the instance's ability to handle storage operations.
- **Network Throughput**: Monitors inbound and outbound network traffic, assessing the instance's data transfer capabilities.

### Relationships
The content pack defines dependencies between services to reflect the interconnected nature of EC2 instance performance metrics. For example, the overall AWS EC2 Instance Performance is dependent on the CPU, Disk, and Network Performance services.

## Installation

### Installation prerequisites:

[Splunk Addon for AWS](https://splunkbase.splunk.com)

[Splunk App for Content Packs](https://splunkbase.splunk.com/app/5391)

[Splunk ITSI](https://www.splunk.com/en_us/products/it-service-intelligence.html)

## Troubleshooting

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

[Github and Readme](https://www.github.com/kinneygroup)

atlassupport@presidio.com

## Contact

To provide feedback, visit our [Github and Readme](https://www.github.com/kinneygroup) for our content packs.

atlassupport@presidio.com

For more information about Presidio Splunk Solutions' Splunk Products, visit our [website](https://kinneygroup.com/atlas).

## Version History

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.4   | 04/16/2024 | Prerelease changes to Readme   |
| 1.0.0   | 05/15/2025 | Update to Documentation |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)