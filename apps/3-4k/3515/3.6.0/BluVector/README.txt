BluVector App for Splunk
===============================

Overview:

The BluVector App for Splunk provides several dashboards for viewing various information that can be provided by a BluVector Cortex sensor.  Since each dashboard reliest upon different types oflogs for rendering they have different requirements for setup.  Please be sure to follow the appropriate steps required for each set of dashboards. 

Views - BluVector Detections:
This view provides a look at Suspicious and Malicious events detected by a BluVector sensor.  It provides a means to pivot to the event on a BLuVector sensor as well as a pivot to the Targeted Logs for that event within the Splunk app.

Views - BluVector Targeted Logs:
When BluVector is configured to send Targted Logs to Splunk this view will render those logs as they relate to the event of interest.  It is easily accessed by clicking the event of interest on the BluVector Detections view, or can be accessed directly and the event ID of interest can be queried.

Reports - BluVector Health:
This dashboard provides a look at the status of various aspects of the sensor's functionality to include GUI status, Analysis Status, Bro Status, and Suricata Status.

Reports - BluVector Performance:
This dashboard provides a look at the performance of individual BluVector Cortex sensors to include throughput and CPU, Disk, and Memory Usage.

Reports - BluVector Analysis:
This dashboard provides metrics around the detection events seen by eithee the deployment of BluVector sensors, individual sensors, or multiple sensors.  It includes details on detection protocols, event detections by analytic engine, and file types. 


### Pre-requisites
- Splunk Enterprise server with user that can install the app.
- BluVector v3.5.0
- BluVector admin credentials that can setup the output.

### General Installation
- In the App Manager in Splunk, and press the **Install app from file** button.
- Choose the app an upload it.
- Back in the App manager, make sure the BluVector App is enabled and visible.
- Installation of the app will create three new Data Inputs:
  - TCP port 8066 for Targted Logs
  - TCP port 8067 for Detection Events, Health, Performance, and Event Metrics
  - TCP port 8068 for SSL/TLS encrypted transmission of Detection Events 

### BluVector sensor Installation Requirements

##### BluVector Detection Events
 
    1) Configure the BluVector sensor with the expected key/value pair mapping
     a) Login to the BluVector Cortex UI with administrator privileges
     b) Navigate to Config -> Outputs -> Key Mappings configuration page
     c) Select the creation of a new kep map button
     d) Use the provided KeyMap.txt file packaged within the splunk app ($SPLUNKHOME/etc/apps/BluVector/additional/KeyMap.txt) to configre the key mapping
     e) Stage the key map changes

    2) Configure the TCP Output
     a) Login to the BluVector Cortex UI with administrator privileges
     b) Navigate to Config -> Outputs -> TCP/UDP configuration page
     c) Modify the defaut output (if it's not already enabled, otherwise create a new Output) by again using the KeyMap.txt file packaged within the Splunk app.
       PLEASE NOTE:  If using SSL/TLS please ensure the correct destination port is configured to match the Splunk port for SSL/TLS connections.
     d) Stage the Output changes

    3) Review & deploy the staged changes

#### BluVector Targeted Logs

    1) Access the BluVector Cortex CLI with root privileges
    2) Enter into the bvintegrations docker container by executing:  docker exec -it bvintegrations bash
      PLEASE NOTE:  For the following step, if the default.example file has already been modified and moved to "default" just edit the existing "default" file
    3) Using vi, edit the "SPLUNKHOST=" and "SPLUNKPORT=" values within the file /opt/bvintegration/logstash/default/default.example to match the appropriate splunk destintation system and port
 (the default port for Targeted Logs is 8066)
    4) Copy (or rename) the default.example file to remove the ".example" extension (leaving it as "default" only)
    5) Copy the provided TargetedLogger.conf into the /opt/bvintegration/logstash/conf.d/ directory
      PLEASE NOTE:  Using scp to copy the file is preferred, but if copy/paste is used be sure to check and correct any <tab> characters that were copy/pasted as multiple <space> characters
    6) Restart the logstsh service by executing:  service logstash restart

#### BluVector Health, Performance, and Event Metrics

    1) Access the BluVector Cortex CLI with root privileges
    2) Enter into the bvintegrations docker container by executing:  docker exec -it bvintegrations bash
      PLEASE NOTE:  For the following step, if the default.example file has already been modified and moved to "default" just edit the existing "default" file
    3) Using vi, edit the "SPLUNKHOST=" value and add a "SPLUNKEVEPORT=" value within the file /opt/bvintegration/logstash/default/default.example to match the appropriate splunk destintation system and port (the default port for Health, Performance, and Metrics is 8067)
    4) Copy (or rename) the default.example file to remove the ".example" extension (leaving it as "default" only)
    5) Copy the provided HealthandPerformanceLogstash.conf into the /opt/bvintegration/logstash/conf.d/ directory
      PLEASE NOTE:  Using scp to copy the file is preferred, but if copy/paste is used be sure to check and correct any <tab> characters that were copy/pasted as multiple <space> characters
    6) Restart the logstsh service by executing:  service logstash restart


### Support
Email support available at support@bluvector.io
