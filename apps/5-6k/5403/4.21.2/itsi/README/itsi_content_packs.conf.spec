# This file contains possible attributes and values for uploading
# content packs to ITSI. A single content pack is represented by a unique
# stanza in this file. For more information about content packs, see
# https://docs.splunk.com/Documentation/ITSICP/current/Config/About.
#
# There is an itsi_content_packs.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To upload a content pack to ITSI, place an itsi_content_packs.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local/. You must restart Splunk to upload
# the content pack and enable configurations.
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
* Each stanza represents a unique content pack.

version = <string>
* The current version of the content pack. When you create a new version, update
  the field here rather than creating a new stanza. The Splunk App for Content Packs
  automatically picks up the specified version. It's possible for a system to
  have multiple versions of a content pack available for installation.
* The first version must be 1.0.0. For subsequent releases, use major versions
  (2.0.0, 3.0.0, etc.) for significant changes like the addition of a correlation search
  or KPI base search. Use minor versions (1.0.1, 1.0.2, etc.) for small fixes or changes.
* Required.

title = <string>
* The title of the content pack displayed in the UI. All content packs must
  follow this naming convention: "Content Pack for ___".
  For example, "Content Pack for Monitoring and Alerting. For more examples of
  content pack names, follow the link to the content packs manual at
  the top of this file.
* The name must be in title case (major words capitalized).
* Required.

description = <string>
* A short description of the content pack.
* For longer descriptions, consider placing an overview file in
* $SPLUNK_HOME/etc/apps/<app_name>/appserver/static/content_pack/<content_pack_name>/overview.md
* Limit: 255 characters
* Optional.

isCustom = [1|0]
* Specifies whether the content pack is customized by users.
* Default: 0 (false).
