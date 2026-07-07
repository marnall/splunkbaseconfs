## Summary
The ITSI Content Pack for Windows from Presidio Splunk Solutions is specifically designed to monitor system health related to Windows operating systems. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for Windows environments, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their infrastructure.

* **Comprehensive Performance Monitoring:** Offers detailed insights into Windows operating system health, network performance, hardware integrity, and security compliance, enabling optimized resource utilization.
* **Critical System Status Tracking:** Monitors the real-time operational status of Windows systems, helping IT professionals swiftly identify and address potential issues.
* **Enhanced Resource Efficiency:** Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the infrastructure.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Details
The ITSI Content Pack for Windows contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

### Services
Windows monitoring encompasses several specialized services, each targeting specific aspects of system performance:

1. **Operating System Health**
    * **Description:** Monitors the overall health and performance of the Windows operating system.
    * **Dependent Services:** Application Performance, Hardware Integrity, Security and Compliance, Network Infrastructure, User Experience
    * **Source:** [https://www.makeuseof.com/tag/check-health-windows-pc/](https://www.makeuseof.com/tag/check-health-windows-pc/)

2. **Hardware Integrity**
    * **Description:** Monitors the physical components of a system such as CPU, memory, storage, and power supply.
    * **Dependent Services:** None
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

3. **Security and Compliance**
    * **Description:** Tracks security events, manages patches, and ensures compliance with security policies.
    * **Dependent Services:** None
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

4. **Network Infrastructure**
    * **Description:** Monitors network performance, including bandwidth usage, latency, and error rates.
    * **Dependent Services:** None
    * **Source:** [https://www.eventsentry.com/features/system-health-monitoring](https://www.eventsentry.com/features/system-health-monitoring)

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. **Startup Performance**
    * **Description:** Monitors the time it takes for the operating system to boot up and be ready for use.
    * **Service:** Operating System Health
    * **Source:** [https://learn.microsoft.com/en-us/mem/intune/configuration/windows-health-monitoring](https://learn.microsoft.com/en-us/mem/intune/configuration/windows-health-monitoring)

2. **Event Log Error Rate**
    * **Description:** Tracks the rate of errors in the system event logs.
    * **Service:** Operating System Health
    * **Source:** [https://www.eventsentry.com/features/system-health-monitoring](https://www.eventsentry.com/features/system-health-monitoring)

3. **System Update Status**
    * **Description:** Status of system updates and patches applied to the operating system.
    * **Service:** Operating System Health
    * **Source:** [https://www.makeuseof.com/tag/check-health-windows-pc/](https://www.makeuseof.com/tag/check-health-windows-pc/)

4. **CPU Health**
    * **Description:** Monitors CPU load and utilization to ensure hardware is functioning properly.
    * **Service:** Hardware Integrity
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

5. **Disk Health**
    * **Description:** Checks for disk errors, bad sectors, and overall disk health.
    * **Service:** Hardware Integrity
    * **Source:** [https://www.eventsentry.com/features/system-health-monitoring](https://www.eventsentry.com/features/system-health-monitoring)

6. **Power Supply Status**
    * **Description:** Monitors the status of the power supply to ensure consistent operation.
    * **Service:** Hardware Integrity
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

7. **Security Event Management**
    * **Description:** Monitors security events to manage and track potential breaches.
    * **Service:** Security and Compliance
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

8. **Patch Status**
    * **Description:** Tracks the status of security patches and updates.
    * **Service:** Security and Compliance
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

9. **Configuration Compliance**
    * **Description:** Ensures system configurations adhere to security policies and compliance standards.
    * **Service:** Security and Compliance
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

10. **Bandwidth Usage**
    * **Description:** Monitors network bandwidth usage to detect abnormal patterns.
    * **Service:** Network Infrastructure
    * **Source:** [https://www.eventsentry.com/features/system-health-monitoring](https://www.eventsentry.com/features/system-health-monitoring)

11. **Network Latency and Errors**
    * **Description:** Tracks network latency and error rates to ensure reliable performance.
    * **Service:** Network Infrastructure
    * **Source:** [https://www.eventsentry.com/features/system-health-monitoring](https://www.eventsentry.com/features/system-health-monitoring)

12. **Network Device Health**
    * **Description:** Monitors the health of network devices to prevent connectivity issues.
    * **Service:** Network Infrastructure
    * **Source:** [https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring](https://www.solarwinds.com/server-application-monitor/use-cases/server-health-monitoring)

### Relationships
#### Dependencies: 
Services are interconnected; for instance, Operating System Health is dependent on Hardware Integrity, Security and Compliance, and Network Infrastructure.

#### Hierarchical Structure: 
Some services form a hierarchy, such as Operating System Health depending on lower-level KPIs like Startup Performance and Event Log Error Rate, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

## Installation

### Installation prerequisites:

[Splunk Addon for Windows](https://splunkbase.splunk.com)

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
| 0.0.1   | 05/28/25 | Initial Preview Release    |
| 1.0.0   | 05/20/25 | Documentation Update |


## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)