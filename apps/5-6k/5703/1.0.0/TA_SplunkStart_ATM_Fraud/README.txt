Author: Miranda Montroy

This Add-On Requires the user to download and install the SplunkStart App
from Splunkbase, which can be found at:

https://splunkbase.splunk.com/app/3577/

After installing SplunkStart (version 1.4 or higher), you will be able to use this TA.

Installing the TA

Unpack the downloaded TA to any directory on your search head. Then from the
command line, cd into the SplunkStart/bin directory, which is located in
$SPLUNK_HOME/etc/apps/SplunkStart/bin.

Run the script:

./create_content.sh <path to directory of this TA>

Example:

./create_content.sh /opt/tmp/TA_SplunkStart_ATM_Fraud

This will append the necessary files from the TA to the local directory of
SplunkStart as well as append the default.meta in the TA to SplunkStart's
metadata/local.meta directory.

Once the above script has run successfully, you may restart Splunk. 

To enable built-in examples

Create an Index called 'FS' and 'atm_fraud'

Using the sample data located in /$SPLUNK_HOME/etc/apps/TA_SplunkStart_ATM_Fraud/sampledata

Load in the following 2 files into the FS index

1) ATM_Transactions.csv 
	Sourcetype name: incident_data
2) ATMIncidentData.csv
	Sourcetype name: atm_transactions

Using the sample data located in /$SPLUNK_HOME/etc/apps/TA_SplunkStart_ATM/sampledata

Load in the following file into the atm_fraud index

1) atm_fraud.csv
	Sourcetype name: fraud

** Data sources and macros made and compiled by Haider Al-Seaidy **

Usage:

Go into the the SplunkStart App from SplunkWeb. Click on Configure Splunk
Start App->Modify Dashboard Macros and click on the ATM Overview Tab. There are macros you can modify to leverage the searches and dashboards in SplunkStart with your own data. You will also find dashboards for ATM Fraud Effects, ATM Incidents Overview, ATM suspicious activity, and ATM verified fraud. 

Examples of common parameters to be entered are your index name, your sourcetype,
earliest time (-15m, -1d, -2Y, etc) and latest time (now) for the search window.