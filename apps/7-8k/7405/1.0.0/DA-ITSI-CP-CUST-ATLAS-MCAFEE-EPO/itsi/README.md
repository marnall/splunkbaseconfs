## Summary
The ITSI Content Pack for McAfee ePO from Presidio Splunk Solutions is specifically designed to monitor the health and performance of McAfee ePO environments. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for McAfee ePO, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their McAfee ePO infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into McAfee ePO services, including agent communication, repository management, and policy enforcement, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of McAfee ePO components, helping IT professionals swiftly identify and address potential issues.
* Enhanced Security and Compliance: Facilitates better decision-making on policy management and event correlation by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for McAfee ePO contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for McAfee ePO environments.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information aboutPresidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
McAfee ePO monitoring encompasses several specialized services, each targeting specific aspects of system performance:

1. ePO Server
    * Description: Central management console for McAfee ePO.
2. Agent Communication
    * Description: Manages communication between ePO server and agents.
3. Repository Management
    * Description: Manages master and distributed repositories for updates.
4. Policy Management
    * Description: Manages creation, assignment, and enforcement of policies.
5. Notification Management
    * Description: Manages alerts and notifications for critical events.
6. Database Health
    * Description: Ensures the health and performance of the ePO database.
7. System Performance
    * Description: Monitors the performance of the ePO system.
8. User Management
    * Description: Manages user roles and activities within ePO.
9. Event Management
    * Description: Manages the collection and correlation of events.
10. Software Updates
    * Description: Manages the deployment and compliance of software updates.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Agent Conn Success Rate
    * Description: Measures the success rate of agent connections to the server.
2. Data Transfer Rate
    * Description: Monitors the rate at which data is transferred between agents and the server.
3. Agent Health Status
    * Description: Tracks the overall health status of agents.
4. Repo Sync Success Rate
    * Description: Measures the success rate of repository synchronization.
5. Repo Access Time
    * Description: Monitors the time taken to access repositories.
6. Repo Data Integrity
    * Description: Ensures the integrity of data within repositories.
7. Policy Deploy Success Rate
    * Description: Measures the success rate of policy deployments.
8. Policy Compliance Rate
    * Description: Tracks the compliance rate of policies across systems.
9. Policy Update Time
    * Description: Monitors the time taken to update policies.
10. SNMP Cmd Success Rate
    * Description: Measures the success rate of SNMP commands.
11. Ext Cmd Exec Time
    * Description: Monitors the execution time of external commands.
12. Notif Delivery Success Rate
    * Description: Tracks the success rate of notification deliveries.
13. DB Query Resp Time
    * Description: Measures the response time of database queries.
14. DB Conn Success Rate
    * Description: Tracks the success rate of database connections.
15. DB Integrity Checks
    * Description: Ensures the integrity of the database.
16. CPU Pct
    * Description: Monitors CPU utilization percentage.
17. Memory Pct
    * Description: Tracks memory utilization percentage.
18. Disk I/O Perf
    * Description: Measures disk I/O performance.
19. User Login Success Rate
    * Description: Measures the success rate of user logins.
20. User Activity Monitoring
    * Description: Monitors user activities for security and compliance.
21. Event Log Coll Success Rate
    * Description: Measures the success rate of event log collection.
22. Event Corr Accuracy
    * Description: Tracks the accuracy of event correlation.
23. Event Resp Time
    * Description: Monitors the response time to events.
24. Update Deploy Success Rate
    * Description: Measures the success rate of software update deployments.
25. Update Rollback Success Rate
    * Description: Monitors the success rate of update rollbacks.

### Relationships
#### Dependencies:
Services are interconnected; for instance, the ePO Server is dependent on Agent Communication, Repository Management, Policy Management, Notification Management, Database Health, System Performance, User Management, Event Management, and Software Updates.

#### Hierarchical Structure:
Some services form a hierarchy, such as Policy Management depending on Repository Management, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for McAfee ePO](https://splunkbase.splunk.com)

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
| 0.0.1   | 6/5/24 | Initial Preview Release    |
| 1.0.0   | 5/19/25 | Documentation Update

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)