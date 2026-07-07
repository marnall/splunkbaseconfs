Requirements and Installation
## Software Requirements
Preempt Platform must be installed and configured to send syslog to Splunk.
## Installation Steps
1. In Preempt Platform, configure to send syslog to Splunk using the SIEM Connector.
2. In Splunk, after installing the Add on, go to Setting -> Data Inputs -> UDP (or TCP, depending configuration). Configure the port, and choose preempt_cef in the Source type.