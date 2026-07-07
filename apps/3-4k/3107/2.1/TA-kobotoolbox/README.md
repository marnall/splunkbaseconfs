# TA-kobotoolbox

Splunk Technology Add-on (TA) for KoBoToolbox

NOTE: The TA has been completely redesigned to function as a modular input, any configuration from version 1.0 is no longer applicable

## Installation instructions

1. Install App tgz file via Splunk web or manually untar in $SPLUNK_HOME/etc/apps and restart Splunk
2. Go to Settings -> Data Inputs and choose option to add new input for type KoboToolbox
3. Enter a unique input name as well as your KoBoToolbox username and password and click save 

### Usage instructions

Survey data can be accessed using search: index=kobotoolbox sourcetype=kobotoolbox

Enjoy! If you have any questions or recommendations on how this TA could be improved, please contact me at lance@datageek.org
