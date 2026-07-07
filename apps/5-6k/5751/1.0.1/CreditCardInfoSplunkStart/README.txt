Author: Hunter Pavlovich

This Add-On Requires the user to download and install the SplunkStart App
from Splunkbase. It is at:

https://splunkbase.splunk.com/app/3577/

After installing SplunkStart, you can use this TA.

Installing the TA

Unpack the downloaded TA to any directory on your search head. Then from the
command line, cd to the SplunkStart/bin directory. It is located in
$SPLUNK_HOME/etc/apps/SplunkStart/bin.

Run the script:

./create_content.sh <path to directory of this TA>

Example:

./create_content.sh /opt/tmp/CreditCardInfoSplunkStart

This will append the necessary files from the TA to the local directory of
SplunkStart and append the default.meta in the TA to SplunkStart's
metadata/local.meta directory.

You may now restart Splunk.

Usage:

Go into the the SplunkStart App from SplunkWeb. Click on Configure Splunk
Start App->Modify Dashboard Macros and click on the Basic Security Essentials
Tab. There are two macros that you can modify to use your own data with the TA.
The common fields you would enter are your index name, your sourcetype,
earliest time (-15m, -1d, -2Y, etc) and latest time (now).

For the First Time Seen Macro, at the end, you'll need two tokens that
represent a pair that you want to know if is the first time seen as combination
within 1 day of the latest event. This could be username, dest_ip OR user, GIT
OR anything that has a subject accessing an asset. The pattern is a
stats ... split by token1,token2 pair.

For the Time Series Outlier Macro, the last two fields represent a numeric
field, which is used to find the outlier (number of logins, number of login
failures, etc) and a field representing a subject to split by such as username.
This will find outliers for the numeric field split by the subject. For
earliest time, use at least -1d, but earlier time could be used.

