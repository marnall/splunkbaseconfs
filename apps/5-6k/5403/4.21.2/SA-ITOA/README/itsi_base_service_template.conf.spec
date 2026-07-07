# This file contains possible settings you can use to upload sample
# base service templates to the KV store.
#
# There is an itsi_base_service_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. To set custom
# configurations, place an itsi_base_service_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/local.
# You must restart ITSI to enable new configurations.
#
# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

[<name>]
title = <string>
* The title of the service template.

description = <string>
* A description of the service template.

_owner = <string>
* The owner of the service template.
* Default: itsi

_immutable = <boolean>
* Whether the service template can be edited or deleted.
* If "true", the service template cannot be edited or deleted.
* If "false", the service template can be edited or deleted.
* Default: false

entity_rules = <json>
* A list of entity rules (rules specification) used to associate entities
  to services created from this service template.
* This setting is the same as the 'entity_rules' setting in itsi_service.conf.spec.
* Example:
	[\
    	{\
        	"rule_condition": "AND", \
        	"rule_items": [\
            	{\
                	"field": "app_title", \
                	"field_type": "alias", \
                	"rule_type": "not", \
                	"value": ""\
            	}, \
            	{\
                	"field": "itsi_role", \
                	"field_type": "info", \
                	"rule_type": "matches", \
                	"value": "apm"\
            	}, \
            	{\
                	"field": "type", \
                	"field_type": "info", \
                	"rule_type": "matches", \
                	"value": "application"\
            	}\
        	]\
    	}\
	]

kpis = <json>
* A JSON blob that specifies the array of KPI definitions.
* For an example, see itsi_base_service_template.conf.