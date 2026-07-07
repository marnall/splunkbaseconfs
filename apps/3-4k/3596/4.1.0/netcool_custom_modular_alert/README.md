=== Netcool SNMP Alert App for Splunk ===

   Author: FDSE - Splunk
   Version/Date: 4.1.0 April 25, 2017

   Supported product(s):
   This add-on supports logs containing SNMP data for the Netcool app.

   Input requirements: 
   1. Alert Setup in Splunk
   2. Company Specific Enterprise OID
   3. Netcool Integration with current system

=== Using this Add-On ===

	Configuration
	-------------

	To use this add-on, manually configure the Splunk Alert with the following properties

	1. Configure the search for the alert
	2. List the alert to "Add to Triggered Alerts"
	3. List another alert action to include "Netcool Custom Modular Alert"
		1. Server IP : Specify the SNMP Server IP Address and Port numbers as per the below format
		 	"IP_Address_1:Port_Number_1;IP_Address_2:Port_Number_2"
		2. Community : Specify the SNMP Community, Ex : Public
		3. Host Name : Specify the host field from Splunk search like $result.splunk_field_name$. Note that 
			any field listed here must be part of the result from the search powering the alert.
		4. Custom Text : Specify any text you would like to send over in the trap.
		5. Alert Message : Use $result.splunk_field_name$ to pass in fields from Splunk search to create your custom Alert Message
		6. Severity : Specify severity as a value from 0-5 / Specify type in the text $result.splunk_field_name$ to pass in the field name from Splunk Search
			0 : Clear; 1 : Intermediate; 2 : Warning; 3 : Minor; 4 : Major; 5 : Critical
		7. Escalation : Specify the escalation parameter as the group to which you'd like to send the trap to
		8. Alert Key : Specify a Unique Alert Key. Can be a combination of fields from splunk search. Reference the fields as $result.splunk_field_name$
		9. Enterprise OID : This is unique to the company that uses the Netcool Tool. This field can be used to enter the Enterprise Specific OID to send netcool traps.
		10. Specific OID : This field combined with the Enterprise OID forms the unique identifier to send in the traps over SNMP. 
		11. Specific Trap ID : This field combined with the Enterprise OID forms part of the message delivered to Netcool sent over SNMP.

=== Sample Alert Configuration ===

	Search : sourcetype=pan:traffic| top limit=20 bytes, host, user, _time
	List in Triggered Alerts : Enabled
	Alert type : Real Time
	Alert Mode : Once Per Result
	Trigger Actions : Add to Triggered Alerts ; Severity : High
	Trigger Actions : Netcool Custom Modular Alert
		Sever IP : 172.16.235.129:10162;192.168.0.18:10152
		Community : public
		Host Name : $result.host$
		Custom Text : $result.host$ is the custom Text
		Alert Message : $result.host$ is the alert Message
		Severity : 0
		Escalation : Linux Admins
		Alert Key : UniqueKey
		Enterprise OID : 1.2.3.4.5.6.7.8
		Specific OID : 9
		Specific Trap ID : 10

	Once the above alert has been configured, I had installed PRTG Monitor on my windows machines (IP : 172.16.235.129 and 192.168.0.18) to view the traps on their specific ports. A sensor probe called SNMP Trap Monitor was configured to listen in on my MAC IP Address for SNMP Traps. As soon as alerts start to trigger, the traps collect on the PRTG Monitor Message board.

=== Netcool Configuration ===
On the netcool end, please configure in the below format:
case ".1.2.3.4.5.6.7.8":
    switch($specific-trap) { //In the above Sample Alert Configuration, the $specific-trap matches the value entered in Specific Trap ID, i.e, 10.
            case "0":  ###-Splunk Alert
		$hostname = $1
                $customtext = $2
                $alertkey = $3
                $alertmessage = $4
                $splunkapp = $5 //This is the app in which the alert was setup
                $severity = $6
                $escalation = $7
                $splunksearch = $8 //This is the name of the alert that was setup to send SNMP Traps in Splunk
