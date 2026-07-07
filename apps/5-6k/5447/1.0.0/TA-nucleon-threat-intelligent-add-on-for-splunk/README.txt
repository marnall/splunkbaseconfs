
Nucleon Threat Intelligent Add-on v8.1
February 2021

Nucleon is a distributed, high-performance invisible and non-invasive platform that is tailored to secure environments from different common threats such as professional hacking groups, APTs and others. Our platform identifies what your adversaries are doing, how they’re doing it and whether they’re targeting you or your extended enterprise.
This add-on bring Nucleon Cyber intelligence feed to splunk. Get the most update indicators from Nucleon activeThreats and Hashes api to splunk enterprise.

**NOTE**
for seeing Nucleon real-time threat analysis and reporting dashboard,interact with this add-on you also need download the Nucleon Threat Intelligent app

Add splunk app to your Splunk Enterprise
1) connect to your splunk Enterprise web UI
2) install splunk app using splunk web UI:
	- in the top nav bar goto apps-> Manage Apps->install app from file (top left button)
	- upload the TA-nucleon-threat-intelligent-add-on-for-splunk-1.0.0.spl file
3) restart splunk
4) navigete to the add-on
	- in the top nav bar goto apps-> Manage Apps-> Nucleon Threat Intelligent Add-on for Splunk

Set splunk add-on - for getting data to splunk:

	- create inputs(if not exist) and set configuration details inorder to start streaming the API data to splunk nucleon_index

	
	- set inputs:	
		- in the top nav bar goto inputs tab
		- create the following inputs:
			- active Threats 
			- hash 
		* Interval field - delay time between API calls (in seconds)
		* Index - the splunk index were the data will be stored in, specify nucleon_index or any other index you intersted in
		
		
	- set configuration:
		- in the top nav bar goto Configuration tab
		- please enter your given addon- setting for API's authentication username, password,usrn and cliendID sported by Nucleon LTD


	- set log level 
		- in the top nav bar goto Logging tab
		- check nucleon_index to validate that the API's data streaming properly
		- if you can't see data indexing check if your configuration Add-on details: 
			- not set 
			- set but not properly 
		- to see add-on logs ( info/warrning /error ...)
			- in the splunk server:
				- cd to /opt/splunk/var/log/splunk/[add-on modular input name].log
				- for example: cat ta_nucleon_add_on_for_threat_intelligent_activeThreats.log (linux command)



for any question you can connect us via:
	support@nucleon.sh

