##Readme for the Perficient Splunk Plus TM1 Technology Add-on (TA)
##Authors: Tony Marrazzo and Edward Denzler
##Version: 1.0

#PREREQUISITES:
* Splunk 6.3.x or above
* TM1 10.1 or higher
* Python 2.7
* SA-Eventgen (if using Demo Mode)

#INSTALLATION:
1. Unzip the perficient_tm1_add_on_for_splunk_v100.zip file.  This file contains the .spl file you will install into Splunk Enterprise.

2. Install app in Splunk Enterprise
	a. Navigate to "Manage Apps" then "Install app from file"
	b. Select the ".spl" file containing the Perficient Splunk Plus TM1 Add-on and click upload
	c. Restart Splunk as prompted
	d. Fill in the setup screen as prompted
		i.  Check the box to "Enable Demo Mode" ONLY if you wish to use eventgen data, fed into the tm1_eventgen index.  This is based on the sample files located within the samples directory.  SA-Evengten will need to be installed in order to use this feature.
		ii. Enter the name of the index that the TM1 events should be indexed to.  Set this to "tm1_eventgen" if using demo mode
		iii.  Check the box for "Distributed Environment" ONLY if you are using forwarders to collect the tm1 logs located on the TM1 Servers.  For more details regarding distributed environments, please see section 5.
		iv.  Enter in the top level directory for where your TM1 instances are installed.  For example, if you have multiple TM1 instances on a single server, inside of C:\Program Files\TM1, you can just enter this in, and the configuration will search for and ingest all TM1 log files of interest inside nested directories.  In order for the automatic lookup to function properly, this path also should include the tm1s.cfg property file, for mapping the ServerName property to the tm1_instance field. For more details regarding the lookup tables, please see the Perficient Splunk Plus for TM1 Documentation.

3. Restart Splunk to apply configurations

4. Ensure TM1 is configured with the proper logging settings:
	a. TM1.Server events are required for calculating downtime and identifying restart events
	b. TM1.Process events are required for identifying process execution and status 
	c. Process error log files are required for the TM1 Error Investigation view
	d. tm1s.cfg property file(s) will need to be within the path specified during setup for Splunk to automatically map the ServerName property to the tm1_instance field

5. ONLY IF USING FORWARDERS - Install TA on Forwarder(s)
	a. Perficient_TA_TM1_FWD is generated in $SPLUNK_HOME/etc/apps/Perficient_TA_TM1/appserver/addons
		i. This is a technology add-on for the forwarders.
		ii. Go into Perficient_TA_TM1_FWD/local/inputs.conf and add 'disabled = 0' to each stanza (to enable the inputs for the forwarder)
	b. Perficient_SA_TM1_IDX is generated in $SPLUNK_HOME/etc/apps/Perficient_TA_TM1/appserver/addons
		i. This is a support add-on for the indexers (just basic definitions for interpreting data from forwarders)
		ii. No changes are required to this app.
	c. DO NOT CHANGE APP NAMES.
	d. After completing installation on Search Head:
		- All indexers (if using tiered architecture) need copy of "Perficient_SA_TM1_IDX".
		- All forwarders require a copy of "Perficient_TA_TM1_FWD" with inputs.conf ENABLED manually. (As noted in section 6.a above)
	d. If using a deployment server, copy Perficient_TA_TM1_FWD and Perficient_SA_TM1_IDX to $SPLUNK_HOME/etc/deployment-apps and deploy to the 
	   appropriate Splunk instances. Select the option to 'Restart Splunkd' when defining serverclasses.conf.
	e. If not using a deployment server, copy Perficient_SA_TM1_IDX and Perficient_TA_TM1_FWD to the $SPLUNK_HOME/etc/apps directory of the
	   appropriate Splunk instances. Restart each instance after files are copied.

6. Troubleshooting Notes and Tips:
	- If using forwarders, ensure Perficient_TA_TM1_FWD’/local/inputs.conf are ENABLED (disabled = 0 in each stanza).
	- Make sure app names "Perficient_TM1_App","Perficient_TA_TM1","Perficient_TA_TM1_FWD", and Perficient_SA_TM1_IDX are NOT changed - there are dependencies in the scripts)
	- Make sure each instance of Splunk was restarted after receiving the app
	- Remember when using forwarders:
		During setup, click 'Distributed Splunk'
		During setup, give the parameters AS IF YOU ARE ON THE FORWARDER

7.  Known Issues
	-Rerunning setup multiple times can produce unexpected results in the local .conf files
	-If you need to rerun setup, you must delete the local directory first!