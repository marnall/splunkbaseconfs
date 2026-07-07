## Summary
The ITSI Content Pack for Nginx from Presidio Splunk Solutions is specifically designed to monitor the health and performance of Nginx servers. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for Nginx, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their Nginx deployments.

* Comprehensive Performance Monitoring: Offers detailed insights into Nginx performance, including request rates, response times, and server health metrics, enabling optimized resource utilization.
* Critical System Status Tracking: Monitors the real-time operational status of Nginx servers, helping IT professionals swiftly identify and address potential issues.
* Enhanced Security Monitoring: Facilitates better decision-making on security measures by analyzing SSL certificate status and HTTP response codes.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for Nginx contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for Nginx deployments, ensuring optimal performance and security.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
Nginx monitoring encompasses several specialized services, each targeting specific aspects of server performance and security:

1. Nginx Deployment
    * Description: This represents the overall deployment of Nginx, encompassing all aspects of its operation and performance.
2. Web Traffic Management
    * Description: This service focuses on monitoring and managing the traffic handled by Nginx, including request rates and response times.
3. Request Handling
    * Description: This service monitors the rate and efficiency of request processing by Nginx.
4. Connection Management
    * Description: This service monitors the connections to the Nginx server, including active, idle, and dropped connections.
5. Server Health
    * Description: This service monitors the overall health of the servers running Nginx, including CPU, memory, and disk usage.
6. Process Health
    * Description: This service monitors the health of Nginx processes, including master and worker processes.
7. Security Monitoring
    * Description: This service focuses on monitoring the security aspects of the Nginx deployment, including SSL certificate expiration and HTTP response codes.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. Nginx Deployment
    * Description: This represents the overall deployment of Nginx, encompassing all aspects of its operation and performance.
    * Source: N/A (General knowledge)
2. Requests per Second
    * Description: Monitor the rate at which Nginx is handling requests.
3. Server Error Rate
    * Description: Track the number of 5xx errors divided by the total number of status codes.
4. Response Time
    * Description: Measure how quickly requests are being handled.
5. Request Processing Time
    * Description: Measure the time taken to process client requests.
6. Total Requests
    * Description: Monitor the total number of requests handled by Nginx.
7. Reading Request Headers
    * Description: Monitor the number of requests currently being read.
8. Active Connections
    * Description: Current number of active connections.
9. Dropped Connections
    * Description: Number of connections dropped due to resource limits.
10. Connection Limits
    * Description: Monitor the total number of connections Nginx can handle.
11. CPU Usage
    * Description: Monitor the CPU usage of the server.
12. Memory Usage
    * Description: Monitor the memory usage of the server.
13. Disk Space Usage
    * Description: Monitor the disk space usage to prevent system failures due to full disks.
14. Nginx Processes
    * Description: Monitor the health of Nginx processes (master, worker, and caching processes).
15. Load Average
    * Description: Summarize CPU and disk usage with 1-minute, 5-minute, and 15-minute running load averages.
16. SSL Certificate Expiration
    * Description: Monitor SSL certificate expiration to avoid security issues and site unavailability.
17. HTTP Response Codes
    * Description: Analyze HTTP response codes logged by Nginx to identify potential issues.

### Relationships
#### Dependencies:
Services are interconnected; for instance, Nginx Deployment is dependent on Web Traffic Management, Server Health, and Security Monitoring. Similarly, Web Traffic Management relies on Request Handling and Connection Management to ensure efficient traffic flow.

#### Hierarchical Structure:
Some services form a hierarchy, such as Server Health depending on Resource Monitoring and Process Health, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Nginx](https://splunkbase.splunk.com/app/3258)

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
| 0.0.1   | 06/03/24 | Initial Preview Release   |
| 1.0.0   | 05/20/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)