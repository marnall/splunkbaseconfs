This application is used to visualize the topology of an enterprise network.

1) Splunk Enterprise setup

	1.1) Installing an additional application
	The application is based on the application - Network Topology - Custom 
	Visualization, therefore, before starting work, you need to install the 
	above application from the link - https://splunkbase.splunk.com/app/3762/.

	1.2) Install application Network Topology Dashboard

	1.3) Create new index 
	Recommended index name is topology, because dashboard and report are tuned to this
	index name. 
	
	1.4) Adding New Data Input
	In Data Inputs -> Files & Directories, specify the directory where the script`s
 	results will be stored (for example, you can create new directory for results -
	/opt/topology). Select the index for the events that you created in 1.3 or if 
	you did not create the index in 1.3, you can create right here.

2) Script preparation

	2.1) Specify the directory, that you added to the Data Input in 1.4, in the script`s
	variable <workingdir>.
	
		
	2.2) Install SNMP utility
	You can use the command:
	sudo yum -y install net-snmp net-snmp-utils

	2.3) Place the script and file with ip addresses in the directory, that you added to 
	the Data Input in 1.4, from <script> directory in the app`s directory.

	2.4) Scheduling a scan of network nodes using CRON
	You can use the command:
	crontab -e 
	0 2 * * * /opt/topology/network_topology.sh
	
	This CRON command runs a scan every day at 2 am. If desired, you can change this 
	parameter.

3) Edit Report in our application
	In the application, in the Reports tab, edit the <network_topology> request using 
	your required ip addresses and their sites, namely in the search line:
	| eval sourceRole = case(Host like ...)
	After modifying and executing the search query, save the Report.
	
	

	