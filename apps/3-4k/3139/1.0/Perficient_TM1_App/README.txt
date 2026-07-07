##Readme for the Perficient Splunk Plus for TM1 App
##Authors: Tony Marrazzo and Edward Denzler
##Version: 1.0

#PREREQUISITES:
* Perficient Splunk Plus TM1 Technology Add-on (TA) for Splunk Enterprise (version 1.0)
* Splunk 6.3.x or above
* TM1 10.1 or higher 

#INSTALLATION:
The Perficient Splunk Plus TM1 App for Splunk Enterprise uses the data provided by the Perficient Splunk Plus TM1 Technology Add-on (TA) for Splunk.  The TA must be downloaded, installed and properly configured prior to using this App.

Steps:

1. Install the Perficient Splunk Plus TM1 Technology Add-on (TA)  for Splunk Enterprise version 1.0 (available from Splunkbase) and follow the installation instructions.

2. Unzip the perficient_tm1_app_for_splunk_v100.zip file.  This file contains the .spl file you will install.

3. Install the Perficient Splunk Plus TM1 App for Splunk Enterprise 
    a. In Splunk Enterprise, Navigate to "Manage Apps" then "Install app from file"
	b. Select the ".spl" file containing the Perficient Splunk Plus TM1 App for Splunk Enterprise and click upload
	c. Restart Splunk Enterprise as prompted
	d. In the setup screen, enter the name of the index your TM1 events are stored in - this should 	match the index name defined in the TA
	e. Restart Splunk Enterprise
	f. Allow time for the tm1s.cfg files to be ingested, then navigate to search>reports and execute the "Run Once-Setup Search".  This search will populate the lookup table used to drive the user inputs, for selecting the desired TM1 instances.  For more details, please see section 4.

4. Lookup Table Maintenance and TM1 Instance Mapping
-There are two lookup tables in use by this app, instance_lookup.csv and process_lookup.csv

The process_lookup.csv

	a.  The process_type lookup table is used for enriching searches within the dashboards, such as successful/failed loads, successful/failed exports, and so on.  Since the naming of these TI’s can be arbitrary, Splunk is not able to identify whether a process is a load, export, transfer, etc and relies upon a lookup table to perform this function.  By default, this lookup table is configured to work with the sample data as an example.
	b. The following column names are used:
		1.	Process_type
		2.	Examples of  possible entires include Load, Transfer, Export, Maintenance, Close Cycle, etc.
	c.	Business_process_name
		1.	This is the friendly name of the TI process
	d.	Process_Name
		1.	This field is used for matching purposes with the raw Splunk searches.  The interesting TI name should be defined in this field, and it should match the field name retrieved from the raw data.

The instance_lookup.csv

	a.  The instance_lookup table is used for enriching the log data with the TM1 instance name, from which the logs were obtained.  It also drives the tm1_instance selection options in the dashboard UI.  Proper configuration of this table is important as it is leveraged by all of the dashboard panels.  It functions as an automatic lookup, and is intended to map the ServerName field from the tm1s.cfg file with the LogDirectory (should a value be present), and if a value is not present, mapping the file path from the DataDirectory to the path the tm1serverlog and tm1processerror log files are obtained from. 
	b.  After installing both the TA and the Perficient Splunk Plus for TM1 app, the setup search under the saved searches view should be run.  When configured properly, it will extract all of the ServerName values from the tm1s.cfg files and the associated LogDirectory or DataDirectory values, and construct the lookup table.  In the event that this is not possible, you may manually edit the lookup table.
	c.  The lookup table consists of three columns
		1. cfg_source - this is the source path to the tm1s.cfg file and is present to prevent a conflict of shared directories
		2. tm1_instance - this is the ServerName value of the tm1_instance from which the logs are collected
		3. log_dir - this is the directory which the tm1_instance's tm1server.log and tm1processerror.log files are stored
	d.  To manually edit the lookup table, enter a unique value for each cfg_source column, while providing a tm1_instance name, and log_dir paths.  The log_dir path here MUST MATCH the source directory path which the tm1 serverlog and process error files are being ingested from!
 