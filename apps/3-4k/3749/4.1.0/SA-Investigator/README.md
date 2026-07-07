# sa-investigator
SA-Investigator 3.0.0
7 December 2021

This add-on for Enterprise Security is designed to provide a set of dashboard/views that allow analysts to search for activity by a user account or asset(s) (including MAC address, hostname, IP address, NT-Hostname) file/process name and file hash.

Various panels within these views require ES to be installed and if not, certain drill downs will fail and information such as notable events will not be viewable.

Searches leverage the accelerated data models and the default data models that are part of CIM and Enterprise Security.

This was originally built and tested on Splunk 7.2.0 and ES 5.2 but has since been updated to work with newer versions and with the newer Endpoint and Change datamodels. It should operate with earlier versions as well though Change Analysis and Application State datamodel views are commented out starting with version 2.1 and will be deprecated in future versions.

A few DNS panels leverage the Alexa - 1 Million, now deprecated and replaced by Cisco Umbrella - 1 Million List that comes with Enterprise Security. The URL Toolbox by Cedric Le Roux. https://splunkbase.splunk.com/app/2734/ is also used for domain and url parsing in the DNS and Web sections. For those panels to operate as designed, URL Toolbox needs to be installed.

