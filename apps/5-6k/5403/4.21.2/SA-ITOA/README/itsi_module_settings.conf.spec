# This file contains a setting for determining whether a module is editable 
# in the module lister page.
#
# There is an itsi_module_settings.conf in each individual module directory (for example, 
# $SPLUNK_HOME/etc/apps/DA-ITSI-OS/default for the Operating System module). To change this 
# setting for a specific module, place an itsi_module_settings.conf in $SPLUNK_HOME/etc/apps/<module>/local. 
# You must restart Splunk software to enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

[settings://<app>]
* "app" is the ID for the app that contains this configuration file.

is_read_only = <boolean>
* Whether the module shows as editable in the module lister page.
* If "1", the module is not editable in the module lister page.
* If "0", the module is editable in the module lister page.
* Default: 1
