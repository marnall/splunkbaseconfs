Author: Alexia Perez

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

./create_content.sh /opt/tmp/TA_SplunkStart_WireTransferEssentials

This will append the necessary files from the TA to the local directory of
SplunkStart as well as append the default.meta in the TA to SplunkStart's
metadata/local.meta directory.

Once the above script has run successfully, you may restart Splunk. 

Sample Data Pre-Reqs:

First, cd into TA_SplunkStart_WireTransferEssentials/lookups and copy the "susplcious_ip.csv" 
ile into your local machine 

Terminal command: cp susplcious_ip.csv <your local directory here>

Next, cd into TA_SplunkStart_WireTransferEssentials/samples and copy the wire_transfer.csv file 
into your local machine by using the same method as described above. 

Once these 2 files are saved in your local machine, open Splunk Web. 
Click on "Settings > Add Data > Upload > Select File" and choose the wire_transfer.csv file. 
Follow the on-screen steps until the file has been successfully uploaded. 

Now, click on "Settings > Lookups > Lookup table files > Add New"
Select SplunkStart as your destination app, and select susplcious_ip.csv as your lookupfile.
Name the lookupfile and click save. 

Once the data and lookup files have been uploaded, you can begin exploring the Wire Transfer dashboards,
changing titles, and updating macros as you see fit. Once you become familiar with the searches and panels, 
feel free to add your own data!

** Data sources were taken from the Splunk Essentials for FSI app for Splunk **

Usage:

Go into the the SplunkStart App from SplunkWeb. 

Click on Configure SplunkStart App->Modify Dashboard Macros and then navigate to
One of the following 5 dashboard tabs: "Wire Transfer Overview," "Successful Wire Transfers,"
"Wire Transfer Errors," "Wire Transfer Maps," or "Wire Transfer Fraud Overview."
Each dashboard has 5-6 macros that you can modify to use your own data with the TA.