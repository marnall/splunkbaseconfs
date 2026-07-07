Tiny FTP App

This App Monitors the Logs of a FileZilla FTP Server.

This App has 4 Views plus the standard “Search View”. The “TinyFTP Main Dashboard” gives you a quick overview what’s going on on your ftp server. The Dashboard shows the total connections, failed logon attempts, timeouts and how many banns occurred in your selected time range.

The “Commands and Code Statistics” shows a count of events by code groups (100-199,200-299,300-399,400-499), ftp commands and ftp codes in a pie chart and a table of the occurrence of each command or code in the selected time range.

In “Files and Directories” are 6 detailed tables which shows created, removed and renamed files and directories (old name => new name). Downloaded, uploaded files and failed uploads.

In the dashboard "user and computers” are tables which shows how long a user was logged on or which user comes from which IP, witch source uses witch account and from witch IP comes the failed login. There is also a table witch shows the banned IPs.

Now Goemapping Dash is added. The app also has a lookup file for private ip ranges. The file is located at...\Splunk\etc\apps\tFTP\lookups\locIP.csv. To add your ip ranges just add the range to the csv. Then open google maps in your browser and go to the location of your local LAN. 
Now click right and choose "what is here?”.  Copy and paste the coordinates shown in in the google search bar.

Installation

Create an index and name it “ftp”. Install the app in %splunkhome%/etc/apps. Sourcetype and fieldextractions comes with the app. 

Logon the FileZilla FTP server and enable logging into a single file.

Select the method of your choice:

If you want the read the logfile directly into splunk then choose input as file. Set the sourcetyp to “FileZilla_FTP” and the index to “ftp”.

If you use a forwarder add to the inputs.conf :
(Make sure that the path and name points to the location of your logfile!!!)


[monitor://C:\Program Files (x86)\FileZilla Server\Logs\FileZilla Server.log]
index=ftp
sourcetype=FileZilla_FTP



In this Version two searches "ftp renamed files" and "ftp renamed Dirs" where fixed.  The views “Files and Directories” and “Users and Computers” now auto refresh every  240 sec.



There is no warranty or guaranty for this app even for any information shown by this app. The author is not responsible for passible damage cause by using this app. This app has no support.  