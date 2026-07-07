# F5® LTM Pool Monitoring


* F5 LTM Pool Monitoring App provides means to monitor F5 LTM Pools using SNMP.


# Version 1.3.3


# Release Notes


	1.0: January 2018

		- Initial release
		
	1.1: January 2018

		- Adjusted documentation
		
	1.2: January 2018
	
		- Improved "Pool Status" dashboard (queries, drilldowns)
		- Added "Data Check" dashboard
		- Added "MIB Objects" dashboard
		- Added a default search for each data sourcetype
		- Added a "LTM - Pool Down Checking" alert which alerts when a pool comes back up after a downtime
		- Added a "Log Event" trigger action to the "LTM - Pool Down" alert (needed for the new alert mentioned above)

	1.3: January 2018

		- Fixed a typo

	1.3.1: January 2018

		- Minor adjustments

	1.3.2: February 2018

		- Added a chart for current connections

	1.3.3: February 2018

		- Added eventgen capability
		- Improved MIB Objects dashboard by adding object descriptions
		- Fixed a typo in Maintenance List link to remain in the App

		
# Insight


F5 LTM devices provide information on pool availability through syslog:

Jan 16 02:41:14 f5-ltm mcpd[6896]: 01070727:5: Pool /Common/Pool_A member /Common/Server1:80 monitor status up. [ /Common/Pool_A: up ]  [ was down for 0hr:0min:23sec ]
Jan 16 02:40:51 f5-ltm mcpd[6896]: 01070638:5: Pool /Common/Pool_A member /Common/Server1:80 monitor status down. [ /Common/Pool_A: down ]  [ was up for 23hrs:59mins:37sec ]
Jan 16 03:45:36 f5-ltm tmm1[9827]: 01010221:3: Pool /Common/Pool_A now has available members

It seemed however not handy enough to monitor pool as "up" messages are only being generated after a downtime.

Instead of using syslog data, this App polls F5 devices every two minutes using snmpwalk:

snmpwalk -v3 -u <user> -l authPriv -a <authentication_method> -A <passphrase> -x AES -X <passphrase> -m +F5-BIGIP-LOCAL-MIB <F5_IP> ltmPoolMemberMonitorStatus 

It first retrieves pool members state:

F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."/Common/Pool_A"."/Common/Server1".443 = INTEGER: down(19)
F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."/Common/Pool_B"."/Common/Server2".80 = INTEGER: up(4)
F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."/Common/Pool_C"."/Common/Server3".80 = INTEGER: forced-down(20)

Device answer is then formatted using sed in key-value format to profit from Splunk automatic key-value field extraction:

snmpwalk -v3 -u <user> -l authPriv -a <authentication_method> -A <passphrase> -x AES -X <passphrase> -m +F5-BIGIP-LOCAL-MIB <F5_IP> ltmPoolMemberMonitorStatus | sed -n 's/F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."\/Common\//pool=/p' | sed -n 's/"."\/Common\// member=/p' | sed -n 's/"./ monitor=/p' | sed -n 's/ = INTEGER: / status=/p' | sed -n 's/([0-9]*)//p'

pool=Pool_A member=Server1 monitor=443 status=down
pool=Pool_B member=Server2 monitor=80 status=up
pool=Pool_C member=Server3 monitor=80 status=forced-down

This is the data that gets indexed. From there, the App uses it to provide visibility on pools.


Besides monitoring pool member status, this App also monitors servers' connections, failover and synchronization status.

This data is gathered using the same method, snmpwalk and sed formatting.


# Prerequisites


	1 - Deploy Lookup File Editor (https://splunkbase.splunk.com/app/1724/) on your Splunk Search Head.


	2 - Snmpwalk (SNMP) must be available from the Splunk instance that will run the SNMP poller.
	
	
	3 - As using snmpwalk through shell scripts, this Splunk instance must be hosted on a Linux system.
	
	
# Configuration Steps


	# App deployment
	
	
	The App must be deployed on your Search Head.
	
	
	# Define an index
	
	
	Create a dedicated index or, if preferred, pick an already existing index such as your usual f5 index or the default main index.
	
	The index will be used when configuring data inputs.
	
	Chosen index must be searchable by default.
	
	
	# Poller Deployment
	
	
		# Define the SNMP poller

		
		The SNMP poller - F5LTMPoolMonitoring-Poller - is provided in the install directory.
	
		It can be deployed to any Splunk instance hosted on a Linux system.
	
		On a standalone deployment, it is deployed on the unique Splunk instance while it could be installed to remote Universal or Heavy Forwarders in a distributed environment.
	
	
		# Get F5 MIBS
		
	
		Once the Splunk instance that will run the SNMP poller has been chosen, F5 BIG-IP MIBS must be downloaded from the F5 device and uploaded to MIBS default directory.
	
		F5 MIBS can be downloaded from the BIG-IP GUI under Overview : Welcome : Downloads : https://BIGIP_IP/docs/mibs/mibs_f5.tar.gz.
	
		The usual default MIB directory is /usr/local/share/snmp/mibs. It might differ depending on your system.
	
	
		# Test & adapt snmpwalk command
	
	
		The snmpwalk command used in the shell script must be adapted and tested.
	
	    Copy the snmpwalk command from ./install/F5LTMPoolMonitoring-Poller/bin/snmp_f5_monitor_status_big-ip_name.sh and test it:
	
		snmpwalk -v3 -u <user> -l authPriv -a <authentication_method> -A <passphrase> -x AES -X <passphrase> -m +F5-BIGIP-LOCAL-MIB <F5_IP> ltmPoolMemberMonitorStatus
		
		SNMP user, authentication method and passphrases are needed at this point.
	
	    The expected result is:

		F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."/Common/Pool_A"."/Common/Server1".443 = INTEGER: down(19)
		F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."/Common/Pool_B"."/Common/Server2".80 = INTEGER: up(4)
		F5-BIGIP-LOCAL-MIB::ltmPoolMemberMonitorStatus."/Common/Pool_C"."/Common/Server3".80 = INTEGER: forced-down(20)
		
		Apply the same method for the three others shell scripts:
		
		- snmp_f5_cur_conns_big-ip_name.sh which retrieves servers' current connection count;
		
		- snmp_f5_failover_status_big-ip_name which retrieves failover status;
		
		- snmp_f5_sync_status_big-ip_name.sh which retrieves synchronization status;		
		
		
		# Create scripts
		
		
		Create as many scripts as needed to poll your active and passive F5 devices using different IP addresses and file names.

		Each shell script contains a unique snmpwalk command dedicated to poll one F5 BIG-IP.
		
		Scrips must be executable (chmod +x filename.sh).
		
		
		# Adapt and create inputs.conf
		
		
		Adapt ./local/inputs.conf file:
		
		[script://./bin/snmp_f5_monitor_status_big-ip_name.sh]
		interval = 120
		index = <index_name>
		sourcetype = f5:bigip:ltm:snmp:monitor:status
		host = <big-ip_name>
		
		Index name must be filled.
		
		Host parameter and script filename from the stanza should be adapted to shell scripts created in the previous step.
		
		Adapt the other inputs in the same way:
		
		[script://./bin/snmp_f5_cur_conns_big-ip_name.sh]
		interval = 120
		index = <index_name>
		sourcetype = f5:bigip:ltm:snmp:stat:server:cur:conns
		host = <big-ip_name>
		
		[script://./bin/snmp_f5_failover_status_big-ip_name.sh]
		interval = 120
		index = <index_name>
		sourcetype = f5:bigip:ltm:snmp:failover:status
		host = <big-ip_name>

		[script://./bin/snmp_f5_sync_status_big-ip_name.sh]
		interval = 120
		index = <index_name>
		sourcetype = f5:bigip:ltm:snmp:sync:status
		host = <big-ip_name>
		
		
		# Deploy the poller App
		
		
		Once done, deploy F5LTMPoolMonitoring-Poller to the Splunk instance of your choice as defined in first step.
		
		
		# Check on indexed data
		
		
		Searching for sourcetype="f5:bigip:ltm:snmp:monitor:status" should provide results. 
		
		The other configured sourcetypes as well:
		
		f5:bigip:ltm:snmp:stat:server:cur:conns | f5:bigip:ltm:snmp:failover:status | f5:bigip:ltm:snmp:sync:status
		
		The "Data Check" dashboard could be used to verify if the expected data is being indexed.
		
		If positive, configure the App.
		
		
    # App configuration
	
	
		# Maintenance list view URL
		
		From the App, go to Settings : Knowledge : User interface : Navigations menus and edit default.xml

		Adjust the third line with the URL of your Search Head:
		
		href="https://<splunk_search_head>:<port>/en-US/app...
		
		
		# Maintenance lookup purpose and usage
	
	
		The maintenance lookup is used to avoid being alerted for pool members being down while in maintenance.

		The maintenance lookup could be filled in 3 different ways.

		If a pool member is in maintenance for an undefined period, simply configure maintenance as true as for Server1 example.
	
		If a pool member is in maintenance for a limited period, configure start and date dates following Server2 example.
	
		If a pool member is in maintenance every day on specific hours, only configure start and end hours as done with Server3.
	
	
		Note that maintenance lookup is useful when it is not possible to configure the pool member to a forced-down state which does not generate alerts.
		
		
		# Adjust alerts
	
	    Three alerts are provided in this App:
		
		"LTM - Pool Member Down":
		
		- executed every 3 minutes;
		- looking for down pool members in snmpwalk results - from -4 min to -1 min.
		
		"LTM - Pool Down":
		
		- executed every 3 minutes;
		- looking for down pools on active BIG-IP devices in snmpwalk results - from -4 min to -1 min;
		- pool are considered down when no pool member is available;
		- configured to suppress alert triggering after a 3 hours period;
		- configured to log alerts as events in the default index.
		
		"LTM - Pool Down Checking":
		
		- executed every 15 minutes;
		- looking for pool back up on active BIG-IP devices after a downtime in snmpwalk results - from -30 min to -15 min;
		- identifying down pools from "LTM - Pool Down" log events from the 3 previous hours;
		- configured to suppress alert triggering after a 3 hours period.
		- configured to log alerts as events in the default index.
		
		Adjust these alerts with preferred trigger actions such as email notifications.
		
		Note that as described above, "LTM - Pool Down" and "LTM - Pool Down Checking" are tied together.
		
		If you need to adjust throttle period for "LTM - Pool Down" alert, the time range of "LTM - Pool Down Checking" alert should be adjusted accordingly.
		
		
# Additional notes


F5 Networks - Analytics App is a powerful and complete App that already provides visibility on LTM Pools among many other things.

We just had to build this simple way to monitor pools for a specific use case and wanted to share the result.


# For any help or suggestion on this App, contact splunk@nomios.fr







