## Summary
The ITSI Content Pack for Okta-Identity-Cloud from Presidio Splunk Solutions is specifically designed to monitor system health related to Okta Identity Cloud services. It leverages Splunk ITSI to provide in-depth analysis and visualization of logs for Okta Identity Cloud, ensuring critical identity and access management systems are operating optimally. This content pack is an essential tool for IT professionals looking to enhance the reliability and performance of their Okta infrastructure.

* Comprehensive Authentication Monitoring: Offers detailed insights into user authentication processes, multi-factor authentication, and API interactions, enabling optimized security and user experience.
* Critical System Status Tracking: Monitors the real-time operational status of user management, directory synchronization, and single sign-on services, helping IT professionals swiftly identify and address potential issues.
* Enhanced Resource Efficiency: Facilitates better decision-making on resource allocation and system adjustments by analyzing performance trends and detecting inefficiencies across the identity management infrastructure.

This ITSI Content Pack is open source and available for community collaboration and enhancement on [GitHub](https://www.github.com/kinneygroup).

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

## Details
The ITSI Content Pack for Okta-Identity-Cloud contains service definitions and KPIs ready to import to ITSI. The KPI Thresholds and importance values are set to defaults so that they can be tuned manually for your use case. After configuration, this content pack provides a comprehensive monitoring solution for Okta Identity Cloud services.

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)

For more information about Presidio Splunk Solutions' Products, visit our [website](https://atlas.presidio.com).

### Services
Okta Identity Cloud monitoring encompasses several specialized services, each targeting specific aspects of identity and access management:

1. AuthService
    * Description: Manages user authentication processes.
2. MFAService
    * Description: Handles multi-factor authentication processes.
3. UserMgmt
    * Description: Manages user creation, deletion, and updates.
4. DirSync
    * Description: Synchronizes user data with directory services.
5. APIService
    * Description: Manages API requests and responses.
6. SSOService
    * Description: Manages single sign-on processes.
7. EventLogs
    * Description: Manages event logging and monitoring.
8. HealthCheck
    * Description: Monitors the overall health and uptime of the system.

### KPIs
Each service utilizes specific KPIs to measure its effectiveness:

1. AuthSuccessRate
    * Description: Measure the percentage of successful authentication attempts.
2. AuthFailRate
    * Description: Measure the percentage of failed authentication attempts.
3. AvgAuthTime
    * Description: Measure the average time taken for authentication.
4. MFASuccessRate
    * Description: Measure the percentage of successful MFA attempts.
5. MFAFailRate
    * Description: Measure the percentage of failed MFA attempts.
6. AvgMFATime
    * Description: Measure the average time taken for MFA.
7. UserAddRate
    * Description: Measure the rate of user additions.
8. UserDelRate
    * Description: Measure the rate of user deletions.
9. UserUpdRate
    * Description: Measure the rate of user updates.
10. SyncSuccessRate
    * Description: Measure the percentage of successful directory syncs.
11. SyncFailRate
    * Description: Measure the percentage of failed directory syncs.
12. AvgSyncTime
    * Description: Measure the average time taken for directory syncs.
13. APIReqRate
    * Description: Measure the rate of API requests.
14. APIFailRate
    * Description: Measure the percentage of failed API requests.
15. AvgAPIRespTime
    * Description: Measure the average response time of API requests.
16. SSOLoginRate
    * Description: Measure the rate of SSO logins.
17. SSOFailRate
    * Description: Measure the percentage of failed SSO attempts.
18. AvgSSOTime
    * Description: Measure the average time taken for SSO logins.
19. LogGenRate
    * Description: Measure the rate of log generation.
20. LogFailRate
    * Description: Measure the percentage of failed log generation attempts.
21. AvgLogProcTime
    * Description: Measure the average time taken to process logs.
22. Uptime
    * Description: Measure the system uptime.
23. Downtime
    * Description: Measure the system downtime.
24. HealthScore
    * Description: Measure the overall health score of the system.

### Relationships
#### Dependencies: 
Services are interconnected; for instance, AuthService is dependent on MFAService and APIService. Similarly, SSOService relies on AuthService and APIService for its operations.
#### Hierarchical Structure: 
Some services form a hierarchy, such as UserMgmt depending on DirSync and APIService, illustrating a layered approach to identity management where base services support broader functionalities.

## Installation

### Installation prerequisites:

[Splunk Addon for Okta](https://splunkbase.splunk.com)

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
| 0.0.1   | 6/7/24 | Initial Preview Release    |
| 1.0.0   | 5/14/25 | Documentation Update |

## Considerations:

[Presidio Splunk Solutions ITSI Content Pack Blog](https://kinneygroup.com/blog/installing-itsi-content-packs/)