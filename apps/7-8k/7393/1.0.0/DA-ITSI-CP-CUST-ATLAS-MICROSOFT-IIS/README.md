## Summary
The ITSI Content Pack for Microsoft IIS from Presidio Splunk Solutions is specifically designed to monitor system health related to Microsoft IIS. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for Microsoft IIS, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their web server infrastructure.

* Comprehensive Performance Monitoring: Offers detailed insights into Microsoft IIS server performance, including CPU and memory usage, request load, and error rates, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of Microsoft IIS services and application pools, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Details
The ITSI Content Pack for Microsoft IIS contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for Microsoft IIS environments.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/) 

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

### Services
Microsoft IIS monitoring encompasses several specialized services, each targeting specific aspects of server performance:

1. Microsoft IIS Web Server
    * Description: The primary service responsible for hosting and managing web applications on Microsoft IIS.

2. Application Process Layer
    * Description: Manages the critical web server processes, including CPU and memory usage, and monitors event logs for application and system-related errors.

3. dotNet Framework Layer
    * Description: Monitors the interactions between the ASP .NET server and databases, as well as the performance of the .NET applications and the Common Language Runtime (CLR).

4. Web Server Layer
    * Description: Collects statistics on request load, data transmission, error rates, and monitors the performance of web sites and application pools hosted by the IIS server.

5. IIS Transactions Layer
    * Description: Monitors web transactions, including request rates, error rates, and response times for web sites hosted on the IIS server.


### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. CPU Usage
    * Description: Monitors the CPU usage of the web server processes.

2. Memory Usage
    * Description: Tracks the memory usage of the web server processes.

3. Application Events
    * Description: Monitors event logs for application-related errors.

4. System Events
    * Description: Reports on system events, including errors and warnings.

5. SQL Data Provider Connections
    * Description: Monitors connection rates and pool usage for SQL Server.

6. Oracle Data Provider Connections
    * Description: Monitors connection rates and pool usage for Oracle databases.

7. ASP SQL Clients
    * Description: Reports on client connections to the ASP .NET server.

8. CLR Performance
    * Description: Monitors exceptions, heap memory usage, and garbage collection.

9. Request Load
    * Description: Collects statistics on the number of requests handled by the server.

10. Data Transmission Rates
    * Description: Monitors the rate of data transmission.

11. Error Rates
    * Description: Tracks the rate of errors occurring on the server.

12. Application Pool Status
    * Description: Monitors the status and resource usage of application pools.

13. HTTP Errors
    * Description: Parses HTTP error logs to report on various error types.

14. Request Rates
    * Description: Monitors the rate of web requests.

15. Response Times
    * Description: Measures the response times for web transactions.


### Relationships
#### Dependencies: 
Services are interconnected; for instance, the Microsoft IIS Web Server is dependent on the Application Process Layer, dotNet Framework Layer, Web Server Layer, and IIS Transactions Layer. Each of these layers supports the overall performance and health of the IIS environment.

#### Hierarchical Structure: 
Some services form a hierarchy, such as the Application Process Layer supporting the Microsoft IIS Web Server, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Microsoft IIS](https://docs.splunk.com/Documentation/AddOns/released/MSIIS/About)

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

| Version | Date    | Description                |
|---------|---------|----------------------------|
| 0.0.1   | 06/03/24 | Initial Preview Release    |
| 1.0.0   | 05/19/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)