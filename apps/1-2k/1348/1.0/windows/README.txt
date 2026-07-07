Splunk for Windows
----------------------------------------
This is the Windows app for Splunk 4.2.4. The Windows app provides a series of dashboards that report on:

 * Hardware usage (CPU, memory, disk, network)
 * Logins (successful and unsuccessful, excessively long sessions, etc.)
 * Patch installations (successful and unsuccessful)
 * Errors and warnings found via the event logs (as well as all the event logs from the given host)


What's New
----------------------------------------
Windows app 4.2.4 includes the following changes from the previous version:

 * Improved app setup
 * Improved knowledge layers
 * Several bug fixes 


Requirements
----------------------------------------
 * Splunk 4.2 or higher
 

Installation
----------------------------------------
The Windows app can be installed in one of two ways:

	1) Automatic installation from within Splunk 
	2) Manual installation 

1) Automatic installation from within Splunk  
The Windows app can be installed directly from within Splunk if you are using Splunk 4.2 or greater. To do so, open the Splunk web interface and click the "Manager" link in the top right of the interface. Next, click "Apps" and then press the "Find more apps online". Find the "Splunk for Windows" app in the list and press the install button (you can enter "Splunk for Windows" in the search box at the top right to find it easier). 

2) Manual installation 
Below are instructions for installing the Windows app manually. Skip to step 2.4 if the Windows is not installed or has not been configured.

	2.1) Verifying the Version of the Windows app (if upgrading)
	
	To determine the version of the Windows app that is installed, follow the directions below:
		 1: Open the manager by clicking the "Manager" link in the top right of Splunk's web interface
		 2: Open the apps list by clicking "Apps"
		 3: Click "Edit Properties" next to the windows app
		 4: The version of the app will is available in text box titled "Version"
		 
	No upgrade is necessary if the version of the application is equal to or greater than 4.2.0.
	
	2.2) Backup Local Configuration Files (if upgrading)
	
	Before upgrading, you'll need to copy out any of the files that you changed (and want to retain).
	
		 1: Open the local configuration directory for the Windows app $SPLUNK_HOME/etc/apps/windows/local (e.g. "C:\Program Files\Splunk\etc\apps\windows\local")
		 2: Copy the local directory to a temporary location (if it exists)

	Note that the instructions above only apply to the local configuration files. If you have edited other files (like the views) then you will need to identify and copy those files accordingly.

	2.3) Removing an Older Version of the Windows App
	
	Remove the older version of the Windows app by:
		 1: Stop splunk
		 2: Remove the Windows app directory at $SPLUNK_HOME/etc/apps/windows (e.g. "C:\Program Files\Splunk\etc\apps\windows")

	2.4) Installing the New Version of the Windows App
	
	Install the new version of the Windows app by unarchiving the archive into the apps directory under $SPLUNK_HOME/etc/apps (will probably be "C:\Program Files\Splunk\etc\apps").

	2.5) Restoring Local Configuration Files (if upgrading)
	
	Copy the local directory back to $SPLUNK_HOME/etc/apps/windows/local (e.g. "C:\Program Files\Splunk\etc\apps\windows\local")

	2.6) Start Splunk
	
	Start Splunk and open the Windows app from the launcher. Note that the app will open the setup page if you have not configured it yet.

Configuration
----------------------------------------
You'll need to configure the Splunk for Windows app once it is installed so that you can start importing data. When you first launch the app, it will ask you to perform setup. Enable the inputs you want to get data and the setup app will begin pulling in the data you requested. Note that it may take a few minutes before the data shows up in the reports.

You can always rerun the setup app if you want to make changes. To do so, click on "Setup" from the Windows app navigation bar.

Note that Windows XP does not perform security auditing by default, thus, Splunk will not import any security event logs by default. To enable security audit logging see the following site
    
    http://www.microsoft.com/resources/documentation/windows/xp/all/proddocs/en-us/els_start_security_log.mspx?mfr=true

Additionally, if you are installing the Windows app in a distributed environment, then you'll need to perform some additional configuration (see below for instructions).

Windows app on distributed search configuration
-----------------------------------------------
If you use Windows app on distributed search configuration, you need to enable distributed search according to http://www.splunk.com/base/Documentation/latest/admin/Configuredistributedsearch.

By default, the app has all the inputs enabled, so you will see data not only from your data collecting machines but from your search head also. If you would like to disable collecting data from your search head, then do the following:

	1) Create a local directory under the Windows app ($SPLUNK_HOME\etc\apps\windows\local).
	2) Copy inputs.conf and wmi.conf from $SPLUNK_HOME\etc\apps\windows\default directory to $SPLUNK_HOME\etc\apps\windows\local directory.
	3) Change all instances of "disabled = 0" to "disabled = 1" in $SPLUNK_HOME\etc\apps\windows\local\inputs.conf and $SPLUNK_HOME\etc\apps\windows\local\wmi.conf. 

Known Issues
----------------------------------------

None.

Getting Support
----------------------------------------
For support, please see the following:

 * General support: http://www.splunk.com/support
 * Questions and answers: http://answers.splunk.com
 * Questions and answers (Windows app specific): http://answers.splunk.com/questions/tagged/app-windows-splunk


Contributions
----------------------------------------
Splunk for Windows uses the Validation Engine Query plugin v2.0 per the MIT license (http://www.position-absolute.com/articles/jquery-form-validator-because-form-validation-is-a-mess/).

Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.