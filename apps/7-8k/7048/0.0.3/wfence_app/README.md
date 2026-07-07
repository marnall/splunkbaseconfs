# wfence integration app

## Summary
The specific cyber attack surface of todays enterprise wordpress websites consists of a wealth of complex plugins, templates and components which are permanently inspected by criminals around the world to find entrypoints for their attacks against the publishing organization. Even large Organizations tend to decouple their secured internal infrastructure from their website. Often they outsource the creative publishing work together with the operation to an agency, which might lack the experience and manpower for secure operations. And even when the agency provides a secure service, their Security Operation Center (SOC) will handle incidents on the website - Information about adversaries and direct alerts will not necessarily rich out to the organization. 
This is where WEB Application Firewalls and the current integration into splunk comes into play. The anomalies and apparent attacks on the website are classified by the WAF. Even when the website is operated without grants to install a Splunk Universal Forwarder, a python script to forward wordfence findings is provided.
This app contains functionality to show data extracted from the wordpress wordfence plugin (see https://www.wordfence.com) from Defiant Inc (see www.defiant.com) forwarded to splunk instances. The wfence WAF monitors all communication to the website and the changes made to files on the server 24/7. The forwarding of these data is provided as python skript outside of the splunk app. It is realized non-intrusively and passively. Any communication that indicates cyberattacks, tampering, espionage or technical error conditions is forwarded in configurable schedules. This allows early detection of progressive attack patterns as outlined by the MITRE ATT&CK framework. Companies can then respond quickly to risks and professional attack pattern to ensure the security and availability of their website.
By combining the wordfence attack recognition with Splunk’s comprehensive data correlation, analytics and incident management, security operations teams can efficiently reduce time to incident identification, analysis and mitigation. They are alerted on relevant anomalies, vulnerabilities and threats for their specific environment.  

Integration of the wfence platform with Splunk Enterprise, Splunk Cloud and Splunk Enterprise Security (ES) is enabled by UNeedSecurity servicing the wfence App which is not bound to any other technical addons (TA).   

## Details
### Architecture
The data is created as wordfence detects attack patterns on the website itself. It is then transferred to the splunk HTTP Event Collector (HEC). There it can be correlated with other security information relevant for your organization or its processes.
<div align="center">
  <right><p><img src="static/archs.png" width="558" height="834"></p></left>
</div>

The ingestion via python skript + HEC does work even for *-as-a-service offerings, where you are not allowed to work with the splunk universal forwarder.  

### Use Cases
The wfence App for Splunk provides customizable, out-of-the-box alerts and dashboards to visualize attack data in Splunk, announcing critical situations such as:
* missing patches
* Potential administrator login takeover
* Brute force attacks on the login pages
* Potential integrity loss on the website
* attack distribution patterns over certain users over time

The distribution of attacking clients based on IP Geolocation services has to be monitored.

### Usage
Show, don't tell: many splunk Apps just don't show the dashboards in action. To show the apparently critical situations, a demo dashboard is provided, which is used to verify the current installation.
<div align="center">
  <right><p><img src="static/demo-screen.svg" width="623" height="350"></p></left>
</div>

## Installation
### Prerequisites
There are no prerequisites besides of data ingestion into the 'wfence' resp. 'wfence_demo' index and existing sourcetypes 'wflogins', 'wfblockediplog', 'wp_wfhits', 'wfblocks7', 'wffilemods', 'wp_wflocs' and 'wfsecurityevents'.
### Data ingestion
The app is based on incoming json data from wfence installations within your infrastructure. The python skript to forward the data is provided.  
### Index
The wfence App is expecting an index 'wfence', assuming that all messages are forwarded from the wfence controllers to splunk. The index 'wfence_demo' is expected to import demo data. The demo data is used to visualize the dashboard in action.
### Sourcetypes
There are a bunch of sourcetypes: 'wp_wflogins', 'wp_wfblockediplog', 'wp_wfhits',
'wp_wfblocks7','wp_wffilemods','wp_wflocs', 'wp_wfsecurityevents', 'wp_wfissues' which can be used to present the findings which are produced by the wfence plugin. 
### Data modell
There is currently no CIM datamodell which seems helpfull.

## Troubleshooting
The app is designed with quick usability in mind. We are aware that the wfence data could be exploited even more to draw significant conclusions.
Regarding bugs please follow the steps below: 
- if data are not visible within the demo dashboard, please make sure there is an index 'wfence_demo'. After the index is created please install the wfence App again to ingest the sample data.
- if data are shown within the demo dashboard, but the are not comming in from wfence forwarder, please verify the connection from wfence site to the splunk indexers (index=_internal wfence) If you find any WARNING or ERROR messages work them out.
- if you find demo data within your customized reports please filter them out based on the index='wfence'. Demo data are ingested to the index='wfence_demo'
- any other problems should be forwarded to the creators within UNeedSecurity, see below. 

## Version history
This is the first version, currently there is a limitation with regard to changed files, so further versions will probably contain more infos about changed files based on the wfence scans. This depends on the wordpress wfence module itself.

## Authors and acknowledgment
The app is provided by www.uneedsecurity.com. If something goes wrong, don't hesitate to contact the authors by email devsec_wfence@uneedsecurity.com.

## License
The app is licensed under the splunk End User License Agreement for Third-Party Content.
