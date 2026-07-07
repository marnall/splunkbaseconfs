##Readme for the Tripwire Enterprise Add-on for Splunk
##Author: Tripwire, Inc
##Version: 3.2.2

#PREREQUISITES:
* Splunk 8.0.0 or above
* Tripwire Enterprise 8.8.x or above

#CHANGES AND NEW FEATURES VERSION 3.2.1

Security Enhancements 

- The Tripwire Splunk add-on app has been updated to use Splunk's Secure Secret Storage for managing credentials for Tripwire Enterprise authentication. To ensure proper decryption of the encrypted secret by all components in a distributed Splunk environment, it is important to either use a consistent Splunk.secret value across all instances in the deployment or recreate the secure storage on all Heavy Forwarders. 

Changes to Tripwire Enterprise Splunk Technology Add-on

- The Python warnings have been resolved to ensure compatibility with recent releases of Splunk.
- The add-on app has been updated to support a custom Splunk Management Port number in addition to the default port 8089.
- The add-on app now allows the creation of a timestamp file to indicate the last successful SCM data pull. This update mirrors the functionality of previous versions with FIM data. The timestamp file enables retrieval of policy test results from the last successful pull even if several data pulling iterations are missed due to Splunk or Tripwire Enterprise outages.
- The add-on app is now capable of retrieving the value of the "Actual Values" field in a policy test result from Tripwire Enterprise.
- A defect has been resolved in the add-on app where data loss could occur during the initial pull.

#Features
	- The Tripwire Enterprise Add-On for Splunk enables a Tripwire Enterprise administrator to collect FIM, SCM, and audit events from Tripwire Enterprise, map them to the Splunk Common Information Model (CIM), and input the data into Splunk. This data can be visualized through other Splunk Apps, such as the Splunk App for Enterprise Security
	- The Tripwire Enterprise Add-On for Splunk works on single installation as well as distributed environments
	- Multiple Tripwire Enterprise consoles are also supported for use with this Add-On

#Documentation
	- For detailed documentation, including installation and configuration instructions, please see the included "TripwireEnterpriseSplunk.pdf" file
