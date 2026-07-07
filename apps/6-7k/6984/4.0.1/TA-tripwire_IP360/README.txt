##Readme for the Tripwire IP360 Add-on for Splunk 
##Author: Fortra's Tripwire
##Version: 4.0.1

#PREREQUISITES:
* Splunk Enterprise 8.x or above
* IP360 VnE 9.1.5 or above
* Splunk DB Connect 3.1.3 or above. 

#CHANGES AND NEW FEATURES:
VERSION 4.0.1
   1. Revised to meet the specifications for Splunkbase hosting for Splunk Enterprise.
   2. The add-on now outputs its logs to the Splunk desired location: $SPLUNK_HOME/var/log/splunk/tripwire_ip360.log on Linux 
   or $SPLUNK_HOME\var\log\splunk\tripwire_ip360.log on Windows.
   3. The warnings from the Upgrade Readiness App have been resolved to ensure compatibility with recent releases of Splunk.
   4. Added support for a custom Splunk Management Port number in addition to the default port 8089.

VERSION 4.0.0
   1. Added support for Python 3.
   2. Removed support for Splunk DB Connect v1 and v2 per the app's EOL.

VERSION 3.0.0
   1. Added support for Splunk DB Connect V3.

VERSION 2.1.2
   1. Fixed an issue with applications.

VERSION 2.1.1
   1. Added support for IP360 versions 8.0.0 and above.
   2. Fixed an issue with OS groups.
   3. Fixed an issue with ip360_scan_status input rising column.

VERSION 2.1.0
   1. Fixed an issue with pulling in network groups
   2. Renamed the Add-on to comply with Splunk Enterprise Security naming conventions
   
VERSION 2.0.0
   1. Added a stand-alone TA for Tripwire IP360

#INSTALLATION:
1. Unzip the tripwire-ip360-add-on-for-splunk_401.zip file.  This file contains the .spl file you will install.
2. Configuring the Tripwire IP360 VnE to accept remote connections
	In order to connect the Tripwire IP360 Add-on for Splunk Enterprise to an IP360 VnE, you will need to configure "Remote Access to the Database"
	on the source IP360 VnE.
	This setting allows IP360 to easily integrate with other products from the Tripwire product line. Remote access enables access to
        IP360 with a read-only database account, Tripwire uses SSL (Secure Socket Layer) to safely transmit your data.
 	Only Tripwire IP360 Administrators are able to change database settings.
	Configuring Remote Access to the Database
		a. In the IP360 VnE console, navigate to Administer: System > Database > Remote Access
		b. Check "Enable Remote Access"
		c. Enter a secure password for read-only access to the database.
		d. Enter the sources from which the database can be remotely accessed.  Sources can be hostnames, IP addresses, and CIDRs. Each source should be
		   entered on a separate line.
		e. Click Submit to save your changes. When you click submit, the top of the pane will display the information that will assist you configure
		   the remote PostgreSQL client.
	 For more information about configuring Remote Access please review the "IP360 Administrators Guide".
3. Install the Splunk DB Connect application
  	a. Download Splunk DB Connect from https://splunkbase.splunk.com/ ( version 3.1.3 or above)
	b. Follow the Splunk DB Connect installation instructions ensuring that the PostgreSQL drivers are installed.
	c. After installation is complete, create an Identity to connnect to the IP360 database in Splunk DB Connect.
	        1. Ensure that the Username field is "readonly" and the password matches the setting configured in step 2: "Remote Access to the Database".
	d. In Splunk DB Connect, set up the database connection to the IP360 database by clicking the "External Databases" link
			i.   If you have already set up the database connection it will be listed here, otherwise click the "New" button to set up the connection
			ii.  Fill in the host, port, username, and password to the settings for IP360
			iii. For the following fields use these settings:
				 Database Type: PostgreSQL
				 Transaction Isolation Level: DATABASE_SETTING
				 Database: ice
				 Read only: checked
				 Validate Database Connection: checked
			iv. "Name" can be anything as long as it matches what will be entered on the Tripwire IP360 "Set up" screen.  "ice" is the default and recommended name.
			     Avoid using spaces in this field.
			v. Click Save
4. Uninstall Old Tripwire IP360 Add-on for Splunk
	a. If version 2.0 of the Tripwire IP360 Add-on for Splunk or lower is installed, the old version MUST be uninstalled before upgrading the Add-on.
	b. Remove "TA_tripwire_IP360" from the $SPLUNK_HOME/etc/apps/ directory and restart Splunk Enterprise
 5. Install Tripwire IP360 Add-on for Splunk 
	a. In Splunk Enterprise, Navigate to "Manage Apps" then "Install app from file"
	b. Select the ".spl" file containing the Tripwire IP360 Add-on for Splunk and click upload
	c. Restart Splunk Enterprise as prompted
 6. Configure Tripwire IP360 Add-on for Splunk 
		a. Upon the first time opening the Tripwire IP360 Add-on for Splunk, you will be automatically directed to set up the app.  This can also
		   be found by manually navigating to "Manage Apps", "Tripwire IP360 Add-on for Splunk", then "Set up".
		b. Enter the name for the database connection that was set up in Splunk DB Connect.  This must match what was entered in the "Name" field.(e.g. "ice")
		c. Enter the number of days desired to import IP360 historical data
		d. Upon clicking "Save" these parameters will save and the data will begin indexing

#DISTRIBUTED ENVIRONMENT CONSIDERATIONS
1. The Tripwire IP360 Add-on for Splunk and Splunk DB Connect must be installed together when deploying on a heavy forwarder or dedicated search head.
   This installation performs all of the data importation from the IP360 VnE source.
		a. The TA should not be configured to import data in a search head pool as each search head will keep track of the last value of the queries and
 		   cause data duplication. See step 3 below for more information.
			i. The Tripwire IP360 App for Splunk can be installed in a search head pool for visualizations, the Tripwire IP360 TA should not be installed in a search head pool.
		b. It is not recommended to deploy either the Splunk DB Connect app or the Tripwire IP360 TA that is configured to import data 
                   due to additional complexities.
			i.  Issues with this include requiring pre-configuration of the apps as well as synchronization of the Splunk secret keys.
			ii. Outside of this one instance all other Splunk instances may utilize the Splunk deployment server.
        	c. If following the recommended approach of a manual install for a heavy forwarder or dedicated search head importing the data, follow the
        	   above installation instructions.
		d. The actual forwarding of this data will need to be directed by additional Splunk configurations.
2. Install the TA, "Tripwire IP360 Add-on for Splunk"  to the indexers through your preferred approach of using the deployment server, the cluster manager,
   or manually.  No configurations need to be done within this TA.
3. For all other search heads, outside of the one potentially used for importing Tripwire IP360 data, deploy the Tripwire IP360 Add-on for Splunk
   including those in search head pooling configurations.  This step prepares a deployable version of the TA by changing one setting.
		a. These search heads are not required to have DB Connect installed.
		b. The setup screen used for the Tripwire IP360 TA for Splunk Enterprise pulling in data does not apply to these search heads.  To handle this,
                   when deploying the TA edit the "app.conf" within the "local" folder of TA-tripwire_IP360.  Modify the value for is_configured to be 1 as 
		   shown here:
 			[install]
			is_configured = 0
4. If properly configured, the data should be searchable from any search head.

