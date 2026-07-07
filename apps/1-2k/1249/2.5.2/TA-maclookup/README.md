===maclookup Technology Add-on===

   Author: MuS

   Supported product(s):
   CIM src_mac field or any other specified field with nic MAC's in it

   Source type(s):

   Input requirements:
   The standard IEEE 802 MAC-48 address format is required.
   The server where the search is running, must be able to connect to the internet, 
   since this lookup can happen on an internet DB ;)
   The nic MAC must be in the following format
   - 00:11:22:33:44:55
   - AB-CD-12-34-EF-A1
   - 0123.4567.89ab

   The online result will be the following new fields:

   startHex	The start of the MAC address range the vendor owns in hexadecimal format
   endHex	The end of the MAC address range the vendor owns in hexadecimal format
   startDec	The start of the MAC address range the vendor owns in decimal format
   endDec	The end of the MAC address range the vendor owns in decimal format
   company	Company name of the vendor or manufacturer
   addressL1	First line of the address the company provided to IEEE
   addressL2	Second line of the address the company provided to IEEE
   addressL3	Third line of the address the company provided to IEEE
   country	Country the company is located in
   type		There are 3 different IEEE databases: oui24, oui36, and iab
   MAC		The MAC used for the lookup

===Using this Technology Add-on===

   Setup:
   Install TA and restart Splunk. If it is not working, enable debugging in the
   maclookup.py script. After that you will have a log file in
   $SPLUNK_HOME/var/log/splunk/ and get UI errors. Remember to disable the
   debugging after that.  
   Sometimes Splunk needs for what ever reason two restarts to get this working.

   Configuration:
   Automatic

   Usage:
   example1 = | maclookup
   Offline lookup NIC MAC in field 'src_mac' using netaddr module

   example2 = | maclookup field=foo
   Offline lookup NIC MAC in field 'foo' using the online internet lookup

   example3 = | maclookup online=yes field=foo
   Online lookup NIC MAC in field 'foo' using the online internet lookup

===Support===
This is an open source project, no support provided, but you can ask questions
on answers.splunk.com and I will most likely answer it.
Github repository: https://github.com/M-u-S/TA-maclookup

I validate all my apps with appinspect and the log can be found in the README
folder of each app.

===Versions===
Version/Date: 1.0 / October 2012
Version/Date: 1.1 / October 2013 - added App icon, Splunk 6 support
Version/Date: 1.2 / May 2014 - changed MAC regex match
Version/Date: 1.3 / August 2014 - changed MAC regex match
Version/Date: 2.0 / September 2014 - complete re-write
Version/Date: 2.1 / September 2014 - added debugging
Version/Date: 2.2 / September 2014 - added dummy fields for unknown MAC's
Version/Date: 2.3 / January 2018 - bug fixes
Version/Date: 2.4 / February 2018 - Bug fixes
Version/Date: 2.5 / February 2018 - Added offline and field option
Version/Date: 2.5.2 / February 2019 - Added new online service
