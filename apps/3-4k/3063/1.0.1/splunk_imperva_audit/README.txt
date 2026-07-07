Imperva Database Audit Analysis App for Splunk README 

Last Updated: January 2016

SUPPORTED VERSIONS
The Imperva Database Audit Analysis application is supported with SecureSphere v11.5 and later.


SYSTEM REQUIREMENTS
As this is an app for Splunk, Splunk system requirements apply. For more information regarding Splunk System Requirements, see http://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements.


OBTAINING THE APPLICATION
You can download the Imperva Database Audit Analysis application by browsing the Splunkbase and searching for Imperva.


INSTALLING THE APPLICATION
To install the Imperva Database Audit Analysis application, search for “Imperva Database Audit Analysis“ in the Splunkbase, then download and follow the on-screen instructions.


CONFIGURATION
Imperva exports data to Splunk via syslog. However, Splunk has various methods of importing data into the server.
Consult with your Splunk administrator to establish the optimum method to accomplish this on your Splunk environment.
In any event, it is vital that the data imported from SecureSphere is marked with the following sourcetype:
   sourcetype=imperva:dam:syslog

In the event that SecureSphere is your only input to Splunk via syslog, the simplest approach is given in the example below:

Example: Configuring Splunk to receive SecureSphere data via syslog (SecureSphere is the sole data source via syslog)

To enable syslog in Splunk:
1. SSH to the Splunk machine.
2. Open the file /etc/rsyslog.conf.
3. Uncomment (remove the preceding # from) the following lines:

   #$ModLoad imtcp
   #$InputTCPServerRun 514

4. Save the file.
5. Restart Splunk.

To configure the SecureSphere app to receive data via syslog:
1. SSH to the Splunk machine.
2. Assuming the app is located in the default location, create a new file: /opt/splunk/etc/apps/<app-name>/default/inputs.conf.
3. Add the following lines:

   [tcp://514]
   sourcetype=imperva:dam:syslog
   disabled = false
   source = network_input

   [monitor:///var/log/messages]
   disabled = false
   source = file_monitor
   sourcetype=imperva:dam:syslog

4. Save the file.
5. Restart Splunk.

ADDITIONAL CONFIGURATION
You additionally must configure the following to work with the Imperva Database Audit Analysis application:
• Syslog Message Size
• SecureSphere Action Set to send data to Splunk

For information on how to configure these options, see the Configuration Tab in the  Imperva Database Audit Analysis application in Splunk.


SUPPORT
For assistance with issues encountered using the Imperva Database Audit Analysis application for Splunk, please open a ticket with Imperva support via the Imperva Customer Support Portal via the following URL: https://www.imperva.com/Login
Note that credentials are required to access the portal.
