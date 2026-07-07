# This file contains attributes and values for uploading services to the KV store.
#
# There is an itsi_service.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place an itsi_service.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk to enable
# configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles

####
# GLOBAL SETTINGS
####
# Use the [default] stanza to define any global settings.
#  * You can also define global settings outside of any stanza, at the top
#    of the file.
#  * Each .conf file should have at most one default stanza. If there are
#    multiple default stanzas, attributes are combined. In the case of
#    multiple definitions of the same attribute, the last definition in the
#    file wins.
#  * If an attribute is defined at both the global level and in a specific
#    stanza, the value in the specific stanza takes precedence.

[<name>]
description = <string>
* A description of the service.

title = <string>
* The title of the service.

services_depends_on = <value>
* Any services that this service depends upon.

services_depending_on_me = <value>
* The fields to be represented in the entity.

_owner = <string>
* The owner of the service.

tags = <value>
* Some tags for the service.

kpis = <value>
* Entity rules for the service.

entity_rules = <value>
* A list of entity rules used to associate entities to a service.

identifying_name = <value>
* A field to contain the unique name for the service.

mod_source = <value>
* A field only used by logging, where the edit came from.

source_itsi_da = <value>
* The ITSI module which is the source defining this deep dive.
