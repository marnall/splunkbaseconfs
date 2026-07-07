#########################
# zFTPServer for Splunk #
#########################


I.	Overview
II.	Server App Setup
III.	Client App Setup



I.	Overview

		This Splunk application is designed to provide dashboards of typical operations to maintain and manage your zFTPServer instance.  zFTPServer can be found at http://www.zftpserver.com/.  zFTPServer allows file transfers via FTP, FTPS, SFTP, TFTP, and HTTPS.


II.	Server App Setup
		
		1.	Install Through Command Line
				# splunk install app /location/zftpserver.spl
		2.	Extract and Install
				a.	Extact the zftpserver.spl file to $SPLUNK_HOME/etc/apps/
				b.	restart Splunk
		3.	Install through Splunk Web
				a.	Go to App - Manage Apps
				b1.	Install app from file	
				b2.	Browse more apps
		4.	This application creates an index called zftpserver. To change the index name or location, copy the $SPLUNK_HOME/etc/apps/zftpserver/default/indexes.conf to $SPLUNK_HOME/etc/apps/zftpserver/local/indexes.conf


III.	Client App Setup

		1.	Copy the folder $SPLUNK_HOME/etc/apps/zftpserver/appserver/addons/zftpserver_client from the server
		2.	Place folder on the zFTPServer Server in $SPLUNK_HOME/etc/apps/
		3.	If the location of the logs folder is not C:\Program Files\zFTPServer\log, copy the $SPLUNK_HOME/etc/apps/zftpserver/default/inputs.conf file to $SPLUNK_HOME/etc/apps/zftpserver/local/inputs.conf and adjust the location to the logs folder.