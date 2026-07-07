Overview
--------
 
Alcatel OXO CDR makes possible Call Detail Record with RS232 to Ethernet Converter.

Use Alcatel OXO CDR to monitor :

- Users' Performance
- Saturation of the External Lines 
- Expensive Special Numbers
- International Numbers
- Calls Duration
- Calls Lost
- Forwarded Calls Externally    

Installation
------------

The ALCATEL Omnipcx control unit can send Call Detail Record to a specified serial port (Serial port DB24Option card 4083 ASM or Serial Port DB9 Option card 4093 ASY-CTI).

* Technical architecture : https://splunkbase.splunk.com/app/2718/#/details
* Enabling Ominipcx CDR : activate the call detail module --> Counting
* Configure the RS232 to Ethernet Converter (CSE-H53N - Industrial RS232 to Ethernet Converter) for send Omnipcx call detail over TCP port 6970.
* Install the Splunk package

Limitations
-----------

Phone settings for local and international call prefixes, call charges, special numbers, and emergency call numbers are specific to each country. That’s why the application is set up for two countries: the USA and France.      

The application is set up by default with these parameters:

* International call screening is based on the outgoing prefix 00 
* Screening special numbers or emergency numbers is specific to France. Costs indications for France will be available on January 1st 2015. To change phone numbers for the USA, modifications must be brought to the file OXO_Special_Call_Number_US.csv

Splunk Implementation
---------------------

To change source and index name, modify macro sourcelog :

1) Modify macro sourcelog :
sourcetype=OXO

Contact and Support
-------------------

This app is maintained by Jean-Louis SABAUT : suggestions, help and bug reports are appreciated.
Support for this application is done by email : jlsabaut@gmail.com


