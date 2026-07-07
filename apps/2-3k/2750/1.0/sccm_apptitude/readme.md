SCCM App for Spunk
===================

----------

### OVERVIEW

#### About the SCCM App for Spunk
Created for the Splunk® ChallengePost contest, this app primarily addresses common pain points for System Center Configuration Manager administrators and users.

|  |  |
| --- | --- |
| Author | Christopher Summers |
| App Version | 1.0 |
| Create an index | True |
| Implements summarization | False |

#### Key Features

- Status messages with descriptions
- Change Reporting: Insight into what SCCM admins are doing
- Discovery Events: Watch for abnormal patterns
- Endpoint Protection: Get a quick overview of malware events
- Client Health Reporting: Installs, uninstalls, repairs
- Software Installation Tracking: Installs and removals
- Collection Filtering

#### CIM Compliance ####
If using Endpoint Protection, the Malware Attack model will be used.
There's currently partial support for Audit Change for certain status messaages.

#### Index Information ####
This app uses 2 index files. The sccm_status index includes all status messages. Depending on the size of your SCCM environment you may need to tweak the configuration of this index. The sccm index includes all other inventory and discovery information.

#### Requirements ###
Built using:
 - Splunk® Enterprise 6.2.1
 - DB Connect App 1.1.6
 - Configuration Manager 2012 R2 (RTM should work)

### INSTALLATION
> Note:
> Depending on the size and age of your SCCM environment you may choose to change the frequency of default intervals, enable tail.follow.only in the db-tail input, disable unwanted event collections, or modify the sccm_status retention. Know your SCCM table sizes and Splunk® Enterprise licensing limits before proceeding.

1. Install the App for SCCM app and restart Splunk®
2. Assign the sccm_user role to the appropriate users
3. Add the database connection to the app
 1. Open the app and navigate to Settings | External Databases
 2. Click New
 3. On the Add New screen, set the name to sccm, fill in the sccm database connection information, and click Save. User a service account with read only permissions on the SCCM database.
4. Append the contents of inputs.conf into dbx\local\inputs.conf file
5. Modify the db-tail database input intervals if needed.
6. Restart Splunk® to start collecting data
7. To immediately start using all features of the app, manually run the included collection saved reports

### SUPPORT ###
#### Author ####
You can email me directly at christopher.summers+splunk@gmail.com. Be gentle, I'm new to Splunk.

#### Community ####
Splunk: http://answers.splunk.com/
SCCM: http://myitforum.com/

### License ###
This work is licensed under a Creative Commons Attribution-NonCommercial 4.0 International License.

http://creativecommons.org/licenses/by-nc/4.0/