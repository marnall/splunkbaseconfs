# This file contains possible attributes and values you can use to upload sample
# Service Sandboxes to the KV store.
#
# There is an itsi_sandbox.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an itsi_sandbox.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

[<name>]
title = <string>
* Required
* Title of the sandbox.

description = <string>
* Description of the sandbox.

_immutable = <boolean>
* Required
* Whether you can edit or delete the sandbox.
* If "true", you can't edit or delete the sandbox.
* If "false", you can edit or delete the sandbox.
* Default: false

creator = <string>
* Required
* User who created the service sandbox