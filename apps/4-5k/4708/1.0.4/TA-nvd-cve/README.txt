The App uses bash script to download the data from nvd database. The script needs to be modified for using a proxy, if applicable, and set up download location for the data feed.

The inputs needs to be created to read the file downloaded by the script and inest in splunk.

You can use normal input and manage the downloaded files via cron jobs or use a batch input read followed by deletion of file after splunk has read.

The scripted input can be formalized to change the run schedule. Current schedule is set to run every Sunday.

Created by Akshat Jain
Contact: akshat2101@gmail.com
