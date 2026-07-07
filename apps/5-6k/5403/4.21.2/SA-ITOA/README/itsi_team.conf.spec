# This file contains attributes and values for uploading ITSI teams 
# to the KV store. By default, only the Global team ships with ITSI.
#
# There is an itsi_team.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. 
# To set custom configurations, place an itsi_team.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk software to 
# enable configurations.
#
# To learn more about configuration files (including precedence) please see
# the documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles
#
# CAUTION: You can drastically affect your Splunk installation by changing these settings.  
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

[default_itsi_security_group]
title = <value>
* The name of the team.
* Duplicate team names are allowed, but be aware of other team names 
  and use naming conventions to avoid confusion.

description = <value>
* A meaningful description of the team.

_immutable = <boolean>
* Whether users can edit the team.
* If "1", the team cannot be edited.
* If "0", the team can be edited.
* Default: 0

acl = <dictionary>
* An Access Control List (ACL) associating ITOA roles with permissions
  within that team. 
* Assign read or write access to the listed ITOA roles as appropriate. 
  If a role has write permissions for a team, a user with this role can 
  create and modify services in the team. The user can't delete a service
  in the team unless the role has the delete capability for a service. 

[notable_event_review_security_group]
disabled = <boolean>
* Use this setting to turn off Role-Based Access Control (RBAC) for Episode
  Review only. 
* If you set this flag to "1", all users will be able to see all events 
  within Episode Review, regardless of their team. 
* If "1", RBAC is disabled for Episode Review.
* If "0", RBAC is enabled for Episode Review. 
* Default: 0
