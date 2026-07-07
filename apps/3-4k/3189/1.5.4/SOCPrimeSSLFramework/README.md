
SOC Prime SSL Framework for Splunk
=================================

## Description ##

An analytical package that enables interactive dashboards and real-time e-mail
alerts on security status changes. Combining SSL Framework with Splunk allows you 
to keep up with all the information about SSL certificates in your company.

#### Latest Version ####

* Splunk Version: 6.x
* App Version: 1.5.4
* Last Modified: Jul 2016
* Authors:
    * Nikolay Trofimyuk
    * Oleksandr Bredikhin
    * Oleksandr Verbniak

#### Version Compatibility ####

Splunk 6.4 --  SOC Prime SSL Framework for Splunk 1.5.4

Requirements:
SSL Framework version 1.5.3 supports Splunk 6.3,6.4.
Python version 2.6.6 or higher, except versions 3.x.x.
Libraries for Python: requests, argparse. 
Network access to api.ssllabs.com port 443.

#### Support ####

Further documentation can be found at:  
https://socprime.com/en/ssl-framework-guide-en/

For fastest response to support, setup, help or feedback,
please please mail support@socprime.com

For bugs or feature requests, you can also mail support@socprime.com

## Quick Start Guide ##

SSL Framework for Splunk – an application developed specifically for Splunk. The 
application includes all necessary tools. If you are using Splunk you do not have to 
install the script and configuration files.

 
Install the app:

1. Verify that the server with Splunk on which you want to install SSL Framework App 
matches Requirements. Verify that all necessary python libraries are installed. For 
instructions on verification see Appendix A – Installing and Configuring Python).

2. In Splunk Console go to Apps / Manage Apps and press Install app from 
file. Choose file from zip SOCPrimeSSLFramework.spl and press Upload. After successful 
upload you should Restart Splunk.

3. After restarting Splunk you should configure SSL Framework App. Choose SSL Framework 
App from the list of Apps and press Continue to app setup page in the opened window.

4. Type in a field Domains List all your corporate domains that are using ssl certificate
(coma separated).

5. Type in a filed E-mail address for notifications your email(s) for notifications 
(coma separated). 

6. Press Save.

By default web servers are checked daily at 3 am. Script is running at that time. You 
can change schedule time in Data Inputs / Scripts / $SPLUNK_HOME/etc/apps/SOCPrimeSSLFram
ework/bin/ssl-framework-report.py.. .
Alerts configured as Saved Searches and are scheduled daily at 9 am. You can change 
schedule time in Alerts / Edit / Edit Alert Type and Trigger.

Successful configuring of SSL Framework and content in Splunk should make Dashboard 
SSL Framework show appropriate results.

How to uninstall the app:
Through command line $SPLUNK_HOME/bin/splunk remove app SOCPrimeSSLFramework
 
#### Installing and Configuring Python ####

1. Check if a required Python version is installed (in command line):

python -V

If required Python version is installed go to point 3. If not download Python here
https://www.python.org/downloads/source/ 
2. Install Python using this guide https://docs.python.org/2/using/unix.html 
3. Check if you have pip on the server:

pip -V

4. If there is no pip install using this guide https://pip.pypa.io/en/latest/installing.html:
-	download get-pip.py from https://bootstrap.pypa.io/get-pip.py 

wget https://bootstrap.pypa.io/get-pip.py

-	install pip: 

python get-pip.py

5. Check necessary libraries with command:

pip list

If libraries argparse and requests are missing install them:

pip install argparse
pip install requests


## What's new in this version ##

Use cases for SIEM in SSL Framework: 

1. Certificate expires in 60, 30, 7 and 1 day 
Automatic monitoring and comparing the expiration date of each certificate to the current
date. Email notification that the certificate expires in 60, 30, 7 and 1 days.

2. Certificate expired
Automatic monitoring and comparing the expiration date of each certificate to the current
date. Email notification that the certificate has expired.

3. Certificate was revoked
Automatic monitoring status of each certificate. Email notification that the certificate
has been revoked.

4. Overall rating changed	
Automatic monitoring of the overall rating of each web server and comparing with the 
previous rating. Email notification that the certificate’s overall rating has changed.



## Installing from SOC Prime portal ##

This app is available on Splunkbase portal  and SOC Prime web portal (https://my.socprime.com/en/sslframework). 

