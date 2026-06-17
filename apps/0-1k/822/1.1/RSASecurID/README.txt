RSA SecurID App for Splunk

Description:  This application was designed to give users usable data surrounding the activity taking place on their RSA SecurID appliances.  This application will work with both the RSA SecurID Appliance 130 and 230 models.


Pre-deployment Assumptions:

   1. The RSA appliances are configured to send SNMP traps and allow SNMP read access using SNMPv2.
   2. The Splunk server is accepting SNMP traps and logging them to /var/log/snmptraps.log or the SNMP traps are being absorbed by Splunk in some manner and given a sourcetype name "snmptrap".
   3. The Splunk server has SNMP access to the RSA appliance.
   4. The snmpget command is installed and in your $PATH

Application Configuration:

 Scripted Inputs:  For the "Network Activity" view to properly work there is a scripted input that needs to be configured. This scripted input uses the snmpget command to retrieve specific values from the device.  If you have multiple devices then you need to configure multiple scripted inputs.  Follow these steps:
     1. Copy the sample inputs.conf file from $SPLUNK_HOME/etc/apps/RSASecurID/default/inputs.conf to your local folder, just so no changes are overwritten if the application is updated.
     2. Edit the inputs.conf file and change the script stanza to reflect your device configuration:

	[script://$SPLUNK_HOME/etc/apps/RSASecurID/bin/getSnmpData.sh public 1.1.1.1]
	disabled = 1

	Change "public" to be the community name configured on your appliance that has read access.  Change "1.1.1.1" to be the IP Address of your appliance.  Change "disabled = 1" to "disabled = 0" to enable the scripted input.

     3. If you have multiple appliances, just copy/paste the [script://] stanza for as many appliances as you have and configure the appropriate values as mentioned above.

 Monitored Inputs:  There is an example [monitor://] stanza in the inputs.conf file.  Configure this for the proper location of the file that your SNMP traps are being logged to.  If the SNMP traps are already being indexed by Splunk then this can be ignored.


Reports in this Application:

 Summary View:
   All Users Accessing the Device(s)
   Count of Events (5min spans)
   Total Failed/Successful Logins (5min spans)
   Top Ten Connecting Hosts
   Top Ten Actions

 User Activity View:
   Successful Actions
   Failed Actions
   Successful Action Reasons
   Failed Action Reasons
   Login Failures by User
   After Hours (<9am and >5pm) Admin Events
   System Level Actions
   Runtime Level Actions
   Admin Level Actions

 Network Activity View:
   Received KBytes by Interface
   Transferred KBytes by Interface
   Total Inbound Packets by Interface
   Total Outbound Packets by Interface
   Total TCP In/Out Segments
   Total UDP In/Out Segments
   Total TCP Active/Passive Connections Opened
   Total TCP and UDP Error Counts
   ICMP In/Out Messages
   ICMP Inbound Echos
   ICMP In/Out Destination Unreachables
