TA_Nut-UPS v0.0.1
----------------

NEW IN THIS VERSION
-------------------
Initial Release


GETTING UPS DATA IN
----------------------
It is assumed you have installed and configured NUT on a Linux box and this is all functioning OK.

For detailed information on using NUT, please check the official site documentation : https://networkupstools.org/documentation.html.

For data to get in to Splunk you need to perform the following:

The default setting is to send data to an index called "nut".  If this isn't suitable for your environment: 

1. Create a "local" directory in the TA and copy inputs.conf from the "default" directory to the new "local" directory.
2. Edit the inputs.conf in the local directory and specify your own index in the script stanza.

The data is pulled in via a BASH script in the bin directory.  The script makes use of the "upsc" command and it is assumed the user account running the Splunk Universal Forwarder instance has access to run the executable.  

This script needs to know the name of your UPS so edit the script in the bin directory and edit the variable UPSNAME to match your UPS.  You can confirm you have it correct by running "upsc myups" ("myups" is the name of your UPS :D) and check the output.  You should see statistics of the UPS.  If not check out upsd.conf for the name of your UPS.

The script is disabled by default.  To enable it, perform the first step listed above if not done already and change "disabled = 1" to "disabled = 0".  You only need to enable the script on the host collecting the data.  Do not enable it on indexers as you will just get a lot of pointless errors in your index.

WHERE TO INSTALL THIS TA
------------------------
After making any modifications you need to for your environment, install this TA on a Universal Forwarder to collect the data and on indexers and search heads to parse the data.

NOTES ON NUT DATA
-----------------
Be aware that you may well get different data from your UPS to what I got.  The default configuration is to perform the line breaks before the battery.charge field.  If the first field in your data is different you may need to change this.

Example of the fields I receive from a PowerWalker 2200 VI LCD:

battery.charge:  
battery.runtime:  
battery.type:  
battery.voltage:  
device.mfr:  
device.model:  
device.serial:  
device.type:  
driver.name:  
driver.parameter.pollfreq:  
driver.parameter.pollinterval:  
driver.parameter.port:  
driver.parameter.productid:  
driver.parameter.synchronous:  
driver.parameter.vendorid:  
driver.version:  
driver.version.data:  
driver.version.internal:  
ups.load:  
ups.mfr:  
ups.model:  
ups.productid:  
ups.serial:  
ups.status:  
ups.vendorid:  



BUILD NOTES
-----------
This add-on was built on Splunk Enterprise v9.0.2  
This add-on was tested on Rocky Linux 8.6 and CentOS 7.9.2009.  Other distros haven't been tested.
