Veeam Backup Monitor
Developed for Veeam 9
Tested on Splunk 6.3.2

Install Instructions for the Veeam Backup Monitor App
#1 Unzip the file and copy the contents to your Splunk Server in /opt/splunk/etc/apps directory.  The final directory should look like /opt/splunk/etc/apps/veeam_backup_monitor
#2 Restart Splunk.

Install Instructions for the Veeam Backup Monitor TA
#1 Copy the TA from the /opt/splunk/etc/apps/appserver/addons and place it on your forwarder where your Veeam VBR is installed.
#2 Run the VeeamTask.exe file, this will prompt you for a username and password.  Enter in a username and password that is allowed to connect to the Veeam server and execute powershell scripts.  This application will create a scheduled task that runs as this user.  This app also creates a folder called ‘working’ that is in the bin directory of the app.
#3 If you use a deployment server for the veeam_monitor_TA make sure you place this line in your serverclass.conf file under the class:app:veeam_monitor_TA to prevent the working directory from being wiped out.
excludeFromUpdate = $app_root$/bin/working
