Overview
--------

The Splunk for AVAYA CALL app provides field extractions for SMDR IP OFFICE and makes possible in a quick sight the telephonic performance and abnormalities in using the telephone exchange by yours employees.
https://splunkbase.splunk.com/app/1889/#/details

Use AVAYA CALL to monitor :

- Users' Performance
- Saturation of the External Lines 
- Expensive Special Numbers and DTMF Codes
- International Numbers
- Calls Duration
- Calls Lost
- Forwarded Calls Externally
 
Installation
------------

The AVAYA IP OFFICE control unit can send SMDR / CDR (Station Message Detail Reporting – Call Detail Record) records to a specified IP address and port.

Enabling AVAYA IP OFFICE SMDR
-----------------------------

* Receive the configuration from the system - Select System and then select the SMDR/CDR tab
* Use the Output drop down box to select SMDR only
* In the SMDR settings, enter the required SPLUNK IP Address and TCP Port 6969
* Send the configuration to the system  

Limitations
-----------

Phone settings for local and international call prefixes, call charges, special numbers, and emergency call numbers are specific to each country. That’s why the application is set up for two countries: the USA and France.      

The application is set up by default with these parameters:

* No outgoing prefix for local calls
* International call screening is based on the outgoing prefix 00 
* Screening special numbers or emergency numbers is specific to France. Costs indications for France will be available on January 1st 2015. To change phone numbers for the USA, modifications must be brought to the file AVAYA_Special_Call_Number_US.csv

Splunk Implementation
---------------------

* To change source and index name, modify macro sourcelog :

source=""

Contact and Support
-------------------

This app is maintained by Jean-Louis SABAUT : suggestions, help and bug reports are appreciated.
Support for this application is done by email : jlsabaut@gmail.com
