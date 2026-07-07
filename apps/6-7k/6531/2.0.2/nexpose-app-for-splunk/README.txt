1. Welcome to the Nexpose Dashboard App

The App will give you an Insight of the Rapid7 Nexpose Data.

2. About
Author: Avotrix
App Version: 1.0.0
App Build: 1

2.1 Release Notes

Version 1.0.0: Initial Release

2.2 Diagnostics Generation

Please include a support diagnostic file when creating a support ticket. Use the following command to generate the file based on which Splunk app or add-on is installed. Send the resulting file to support.
•	$SPLUNK_HOME/bin/splunk diag --collect=app:  Nexpose_App_for_Splunk

3 Installation

3.1: Software requirements
		Splunk Enterprise system requirements
			This App runs on Splunk Enterprise hence all of the Splunk Enterprise system requirements apply.

3.2: Deployment Guide
		3.2.1: In Single Environment:
				1.Download the add-on from Splunkbase.
				2.Then Navigate to Apps>Manage App
				3.Click Install app from file.
				4.Locate the downloaded file and click Upload.
		
		3.2.2: Distributed Environment:
	                        Install the App on the Search Head.
	
4. Populating Dashboard
	To Populate the Dashboard kindly specify the index and sourcetype in below macros:
		For Vulnerability Input: `nexpose-vulnerability-index-and-sourcetype`
		For Asset Input: `nexpose-asset-index-and-sourcetype`
		For Scan Input: `nexpose-scan-index-and-sourcetype` -- Kindly refer to section 5 mentioned below to know how to  onboard the data of this  input.
						 
	
	


# Binary File Declaration
# Binary File Declaration
