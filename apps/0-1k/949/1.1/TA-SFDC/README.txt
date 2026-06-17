Author: Paul Stout
Version: 1.1
________________________

This Technology Add-on is based upon an internal POC of SalesForce object synchronization by Alex Raitz.  It has since
been extended to dynamically create SOQL queries from the SFDC Enterprise WSDL and control objects via sfdc.conf
configuration file.

Includes the SalesForce Python Toolkit: http://code.google.com/p/salesforce-python-toolkit/

Installation:

Extract the tarball into $SPLUNK_HOME/etc/apps.  Once extracted, edit TA-SFDC/local/sfdc.conf with your SFDC username,
password, and authentication token.  Download your enterprise WSDL from SFDC to TA-SFDC/local/sfdc.enterprise.wsdl.
If you change the WSDL file name, you must update sfdc.conf to look for the new file in local/.

You may add additional SFDC objects by adding the object name to sfdc.conf and adding an input to inputs.conf.  Please
use the existing inputs as examples. You may also create lookup tables in a similar manner to the default objects.

Of course, if you're completely stuck please reach out to Paul Stout <pstout@splunk.com>.  This connector has many
moving parts :)

Once configured, enable the sourcetypes you wish to Splunk in TA-SFDC/local/inputs.conf.  Next, enable the lookup searches
in TA-SFDC/local/savedsearches.conf. 
