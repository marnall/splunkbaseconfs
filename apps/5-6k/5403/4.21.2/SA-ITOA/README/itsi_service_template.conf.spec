# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
#
# This file contains attributes and values for creating and uploading modules
# in Splunk IT Service Intelligence (ITSI). 
#
# To set custom configurations, place an itsi_service_template.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk software to 
# enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# CAUTION:  You can drastically affect your Splunk installation by changing these settings.  
# Consult technical support (http://www.splunk.com/page/submit_issue) if you are not sure how 
# to configure this file.

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

[<stanza_name>]
title = <string>
* A title of the module.

description = <string>
* The full description of the module being created.

entity_rules = <json>
* A JSON blob of entity rules (rules specification) used to associate entities
  to services created from this module.
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

recommended_kpis = <json>
* A list of KPIs that are automatically added when a service 
  is created with this module.

optional_kpis = <json>
* A list of KPIs that are available with this module but 
  not added automatically when a service is created with it.
