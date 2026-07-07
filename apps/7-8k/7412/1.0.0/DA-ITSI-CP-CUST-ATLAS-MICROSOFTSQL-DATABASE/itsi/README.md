## Summary
The ITSI Content Pack for Microsoft SQL Server from Presidio Splunk Solutions is specifically designed to monitor the health and performance of Microsoft SQL Server databases. It leverages Splunk ITSI to provide in-depth analysis and visualization of various metrics, ensuring the database operates optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their SQL Server infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into SQL Server performance, including CPU usage, memory usage, disk I/O, and index performance, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of SQL Server instances, availability groups, and replication status, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the database infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for Microsoft SQL Server contains service definitions and KPIs ready to import to ITSI. The KPI thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for SQL Server databases.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
Microsoft SQL Server monitoring encompasses several specialized services, each targeting specific aspects of database performance:

1. **SQL Server Environment**
    * Description: Core service representing the Microsoft SQL Server database.
    * Source: N/A (Core service)
2. **Availability Groups**
    * Description: Monitors the availability and health of the database.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/AddOns/released/MSSQLServer/Datatypes)
3. **Query and Procedure Stats**
    * Description: Tracks resource usage and performance metrics.
    * Source: [MSSQL Tips](https://www.mssqltips.com/sqlservertip/6195/sql-server-function-to-measure-cpu-usage-per-database/)
4. **Cluster States**
    * Description: Monitors the performance and health of database indexes.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/AddOns/released/MSSQLServer/Datatypes)
5. **Sessions and Connections**
    * Description: Tracks sessions and connections to the database.
    * Source: [MSSQL Tips](https://www.mssqltips.com/sqlservertip/2522/sql-server-monitoring-checklist/)
6. **Transactions**
    * Description: Monitors database transactions and their performance.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/AddOns/released/MSSQLServer/Datatypes)
7. **ReplicaStates**
    * Description: Monitors database mirroring and replication status.
    * Source: [ManageEngine](https://www.manageengine.com/products/applications_manager/help/ms-sql-db-servers.html)
8. **SystemInfo**
    * Description: Provides system information and status.
    * Source: [Splunk Documentation](https://docs.splunk.com/Documentation/AddOns/released/MSSQLServer/Datatypes)
9. **BackgroundJobs**
    * Description: Monitors background jobs and their performance.
    * Source: [MSSQL Tips](https://www.mssqltips.com/sqlservertip/2522/sql-server-monitoring-checklist/)

### Relationships
#### Dependencies:
Services are interconnected; for instance, the Database service is dependent on Availability, ResourceUsage, IndexPerformance, SessionMonitoring, TransactionMonitoring, MirroringReplication, SystemInfo, and BackgroundJobs services. Each dependent service monitors a specific aspect of the database's operation, contributing to the overall health score of the Database service.

#### Hierarchical Structure:
Some services form a hierarchy, such as ResourceUsage depending on CPU, memory, and disk I/O metrics, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Microsoft SQL Server](https://splunkbase.splunk.com)

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
| 0.0.1   | 06/07/24 | Initial Preview Release    |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)