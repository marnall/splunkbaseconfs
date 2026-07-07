## Summary
The ITSI Content Pack for MySQL from Presidio Splunk Solutions is specifically designed to monitor system health related to MySQL databases. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for MySQL, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their MySQL infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into MySQL database performance, including connections, storage, and replication metrics, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of MySQL instances, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Details
The ITSI Content Pack for MySQL contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for MySQL databases, ensuring optimal performance and reliability.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

### Services
MySQL monitoring encompasses several specialized services, each targeting specific aspects of database performance:

1. Database
    * Description: Core MySQL database service responsible for data storage and retrieval.
2. Connections
    * Description: Manages client connections to the MySQL database.
3. Storage
    * Description: Manages the storage and retrieval of data within the MySQL database.
4. Performance
    * Description: Monitors and optimizes the performance of the MySQL database.
5. Replication
    * Description: Manages data replication between MySQL instances.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Conn Count
    * Description: Number of active connections.
2. Aborted Conns
    * Description: Number of aborted connections.
3. Threads Running
    * Description: Number of running threads.
4. Threads Connected
    * Description: Number of connected threads.
5. Disk IO
    * Description: Disk input/output operations.
6. Buffer Hit Rate
    * Description: Rate of buffer pool hits.
7. Open Files
    * Description: Number of open files.
8. Open Tables
    * Description: Number of open tables.
9. CPU Pct
    * Description: CPU usage percentage.
10. Mem Usage
    * Description: Memory usage.
11. Query Time
    * Description: Average query execution time.
12. Slow Queries
    * Description: Number of slow queries.
13. Repl Lag
    * Description: Replication lag time.
14. Repl Errors
    * Description: Number of replication errors.
15. Repl Events
    * Description: Number of replication events.

### Relationships
#### Dependencies: 
Services are interconnected; for instance, the Database service is the central component of MySQL, upon which other services like connections, storage, performance, and replication depend.

#### Hierarchical Structure: 
Some services form a hierarchy, such as the Database service being the core, with other services like Connections, Storage, Performance, and Replication building upon it, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for MySQL](https://splunkbase.splunk.com)

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
| 0.0.1   | 05/31/24 | Initial Preview Release    |
| 1.0.0   | 05/20/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)
