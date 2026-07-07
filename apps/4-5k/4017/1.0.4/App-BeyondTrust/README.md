# BeyondTrust App for Splunk #

## OVERVIEW ##

The BeyondTrust App for Splunk allows users to see various charts and data using dashboards and also run searches on indexed data. 

* Author - BeyondTrust
* Version - 1.0.3
* Build - 1
* Creates Index - False
* Compatible with:
		- Splunk Enterprise version: 7.x to 8.x
		- OS: Independent of OS
* Prerequisites: Installed and Configured BeyondTrust on machine

## RELEASE NOTES ##

    - Version 1.0.3
	- Usage Statistics Dashboard
	- Session Audit Dashboard
	- Command Audit Dashboard
	- Event Statistics Dashboard
	- Rejected Commands Dashboard
	- User Activity Dashboard
	- Host Activity Dashboard

## SETTING UP SPLUNK ENVIRONMENT ##

### INSTALLATION ###
1. It can be installed in splunk using the following ways:
    * This app can be installed through UI using "Manage Apps" 
    * It can also be installed from the command line using following command(Linux) :
        ```
        sh $SPLUNK_HOME/bin/splunk install app $PATH_TO_SPL/BeyondTrust.spl/
        ```
    * Or, user can directly extract SPL file into $SPLUNK_HOME/etc/apps/ folder.
2. After this, configure the UDP data input from splunk web:
        ```
        Settings -> Data Inputs -> UDP and enter UDP port and Source Type
        ```
3. Then, go to 
        ```
        Settings -> Advanced Search -> Search Macros -> get_beyondtrust_index_sourcetype
        ```
        Input the required index and sourcetype *(Default index is 'main' and sourcetype is 'beyondtrust:syslog')*
## SUPPORT ##
On-Line: Submit a case online and find Support line phone numbers via the Customer Support
Portal: https://beyondtrustsecurity.force.com/customer/login
Phone: Contact BeyondTrust by phone: https://www.beyondtrust.com/support/
