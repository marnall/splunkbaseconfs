## Summary
The ITSI Content Pack for AWS-EBS from Presidio Splunk Solutions is specifically designed to monitor system health related to AWS EBS volumes. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for AWS EBS, ensuring critical systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their infrastructure.

* **Comprehensive Performance Monitoring:** Offers detailed insights into AWS EBS volume performance, including write and read operations, latency, and utilization, enabling optimized resource utilization.
* **Critical System Status Tracking:** Monitors the real-time operational status of AWS EBS volumes, helping IT professionals swiftly identify and address potential issues.
* **Enhanced Resource Efficiency:** Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the storage infrastructure.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Details
The ITSI Content Pack for AWS-EBS contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

### Services
AWS EBS monitoring encompasses several specialized services, each targeting specific aspects of volume performance:

1. **EBS Performance Optimization**
    * **Description:** Monitors key performance metrics of EBS volumes to ensure they are operating efficiently.
    * **Dependent Services:** EBS Write Operations, EBS Read Operations, EBS Latency Monitoring
    

2. **EBS I/O Balance**
    * **Description:** Ensures that EBS volumes are adequately balanced to handle current and future workloads.
    * **Dependent Services:** EBS Utilization Monitoring, EBS Burst Balance Monitoring
    

3. **EBS Throughput**
    * **Description:** Monitors the throughput of read and write operations on EBS volumes.
    * **Dependent Services:** EBS Write Operations, EBS Read Operations
    

4. **EBS Utilization Monitoring**
    * **Description:** Monitors the utilization levels of EBS volumes to ensure they are being used efficiently.
    * **Dependent Services:** None
    

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. **VolumeWriteOps**
    * **Description:** Average number of write operations per second to an EBS volume.
    * **Service:** EBS Performance Optimization
 

2. **VolumeReadOps**
    * **Description:** Number of read operations performed on the volume.
    * **Service:** EBS Performance Optimization
    

3. **VolumeTotalReadTime**
    * **Description:** Total time spent on read operations.
    * **Service:** EBS Performance Optimization
    

4. **VolumeTotalWriteTime**
    * **Description:** Total time spent on write operations.
    * **Service:** EBS Performance Optimization
    

5. **BurstBalance**
    * **Description:** Percentage of I/O credits available for burstable performance.
    * **Service:** EBS I/O Balance
    

6. **VolumeReadBytes**
    * **Description:** Total number of bytes read from the volume.
    * **Service:** EBS Throughput
    

7. **VolumeWriteBytes**
    * **Description:** Total number of bytes written to the volume.
    * **Service:** EBS Throughput
    

8. **VolumeIdleTime**
    * **Description:** Amount of time the volume is idle.
    * **Service:** EBS Utilization Monitoring
    

9. **VolumeQueueLength**
    * **Description:** Number of pending I/O requests in the queue.
    * **Service:** EBS Utilization Monitoring
    

### Relationships
#### Dependencies: 
Services are interconnected; for instance, EBS Performance Optimization is dependent on EBS Write Operations, EBS Read Operations, and EBS Latency Monitoring. Similarly, EBS I/O Balance relies on EBS Utilization Monitoring and EBS Burst Balance Monitoring.

#### Hierarchical Structure: 
Some services form a hierarchy, such as EBS Performance Optimization depending on lower-level KPIs like VolumeWriteOps and VolumeReadOps, illustrating a layered approach to performance monitoring where base metrics support broader performance indicators.

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

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com)

## Version History

| Version | Date  | Description                |
|---------|-------|----------------------------|
| 0.0.1 | 5/28/24 | Initial Preview Release |
| 1.0.0 | 5/15/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)