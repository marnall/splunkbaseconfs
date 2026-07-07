# rhebo industrial protector app

## Summary
The specific cyber attack surface of industrial environments consists of hundreds or even more sensors, actors and controllers connected by a diversity of standard busses and protocols. Often industrial processes are used 7*24 and components are sometimes sensitive against timing conditions. To effectively reduce risk, you need to maximize your insight and control of all devices on your network. 
Rhebo Industrial Protector monitors all communication within, to and from the operational technology 24/7. The monitoring is integrated non-intrusively and passively at key points of the OT. Any communication that indicates cyberattacks, tampering, espionage or technical error conditions is reported in real time. This allows early detection of progressive attack patterns as outlined by the MITRE ATT&CK for ICS framework (see left). Companies can then respond quickly to risks and professional attack pattern to ensure the security and availability of their industrial processes.
By combining Rhebos industrial device visibility, rich contextual device and network properties data with Splunk’s comprehensive data correlation, analytics and incident management, security operations teams can efficiently reduce time to incident identification, analysis and mitigation. They are alerted on relevant anomalies, vulnerabilities and threats for their specific environment.  

Integration of the Rhebo platform with Splunk Enterprise, Splunk Cloud and Splunk Enterprise Security (ES) is enabled by UNeedSecurity servicing the Rhebo Industrial Protector App which is not bound to any other technical addons (TA).   

## Details
### Architecture
The data is transferred in fieldbus/plantbus/terminal bus between components within the industrial environment. It is detected by locally installed sensors. They are connected to one or more controllers, which are delivering syslog data to splunk.
<div align="center">
  <right><p><img src="static/archs.png" width="400" height="400"></p></left>
</div>

The ingestion should be done via best practices Rhebo Industrial Protector->syslog->splunk, dependent on the existing splunk infrastructure. 

### Use Cases
The Rhebo App for Splunk provides customizable, out-of-the-box alerts and dashboards to visualize Controller data in Splunk, announcing critical situations such as:
* Device types connected to the network and connection details
* Protocol anomalies Patterns of network access over time
* Potential MACFlooding
The detection of multiple new MAC-adresses in a
considerably short amount of time should be monitored. An
unusual amount of new MAC-adresses has to be alerted.
* Potential IPFlooding (DOS)
The detection of multiple new IP-adresses in a considerably
short amount of time should be monitored. An unusual
amount of new IP-adresses has to be alerted.
* Potential DNS Amplification Attacks
Unsolicited DNS responses have to be monitored. An
unusual amount has to be alerted.
* Cyclic Message Anomalies
The detection of multiple anomalies concerning cyclic
messages should be monitored. An unusual amount that
occur consecutively has to be alerted.
* Potential TCP SYN flood attack
The detection of multiple TCP-SYN-Portscans in a
considerably short amount of time should be monitored. 
* Potential teardrop attack
The detection of IP-fragments and invalid field lengths in a
considerably short amount of time should be monitored. An
unusual amount of IP-fragments and occuring invalid field
lengths has to be alerted.
* Potential smurf attack
The detection of an IP-address using another MAC-address
in combination with ICMP address scan alerts has to be
alerted.
* Potential session hijacking
An IP address switching MAC address in an open session
has to be alerted as an attacker might be communicating
with the server.
* Potential replay attack
The detection of an IP-address using another MAC-address
in combination with repeating cyclic messages has to be
alerted.
* Potential password attack
The detection of an insecure login or plain text password in
combination with an IP-address using another MAC-address
has to be alerted
* Potential hardware failure
The detection of IP, DNP3, ICMP or TCP checksum errors
should be monitored. An unusual amount of checksum
errors has to be alerted

### Usage
Show, don't tell: many splunk Apps just don't show the dashboards in action. To show the apparently critical situations, a demo dashboard is provided, which is used to verify the current installation.
<div align="center">
  <right><p><img src="static/demo-screen.png" width="623" height="350"></p></left>
</div>

## Installation
### Prerequisites
There are no prerequisites besides of data ingestion into the 'rhebo' index and existing sourcetypes 'rhebo_syslog' and 'rhebo_syslog_demo'. 
### Data ingestion
The app is based on incoming syslog data from Rhebo Controllers within your infrastructure. The ingestion to splunk cloud should be realized with one or more syslog server(s). On premise splunk installations could ingest syslog directly but with higher data volume it is recommended to use solutions like Splunk Connect for Syslog.
A sample dataset is provided together with the sources on ![gitlab](https://gitlab.com/splunk-apps-uns/rhebo) for ingestion into index 'rhebo' with sourcetype 'rhebo_syslog_demo'.
### Index
The Rhebo App is expecting an index "rhebo", assuming that all messages are forwarded from the Rhebo controllers to splunk.
### Sourcetypes
There are two sourcetypes: 'rhebo_syslog' to contain all regular production data and sourcetype='rhebo_syslog_demo' to contain only generated data based on Rhebo samples. The demo data is used to visualize the dashboard in action.
### Lookups
The Rhebo Protectors collect huge information about the network infrastructure. The information can be part of the asset inventory according to ISO 27001. Therefore we organize certain information regarding the device manufacturers as lookup tables. 
### Data modell
The Intrusion Detection datamodell is the nearest, even that Rhebo Protector is working on industrial networks, not only TCP/IP/UDP/ICMP.

## Troubleshooting
The app is designed with quick usability in mind. Please follow the steps below: 
- if data are not visible within the demo dashboard, please make sure there is an index 'rhebo'. After the index is created please install the Rhebo App again to ingest the sample data.
- if data are shown within the demo dashboard, but the are not comming in from Rhebo Controllers, please verify the connection from Rhebo Controllers to the splunk indexers (index=_internal rhebo) If you find any WARNING or ERROR messages work them out.
- if you find demo data within your customized reports please filter them out based on the sourcetype='rhebo_syslog'. Demo data are ingested to the sourcetype='rhebo_syslog_demo'
- if you ingest data from the Rhebo Controller and you don't see them in splunk, be aware that the Controller sends it in UTC. Depending on the timezone of your splunk server, it might be that you don't see them.
- any other problems should be forwarded to the creators within UNeedSecurity, see below. 

## Support
Please contact us by mail (see below), if you have trouble to get it running within your linux/unix environment. 

## Roadmap
Further extensions depend on the Rhebo Controller functionality itself.

## Contributing
We are open to contributions, the app in particular has to pass the appinspect and splunk cloud acceptance tests.  If you have just ideas for further correlations/dashboards, contact us as well.

## Authors and acknowledgment
The app is provided by www.uneedsecurity.com. If something goes wrong, don't hesitate to contact the authors by email devsec_rhebo@uneedsecurity.com.

## License
The content is licensed under the splunk End User License Agreement for Third-Party Content.