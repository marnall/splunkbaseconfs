# This file contains possible attributes and values for adding  
# and removing icons from the glass table icon library.
#
# There is a glasstable_icon_library.conf in $SPLUNK_HOME/etc/apps/itsi/default/.
# To set custom configurations, place a glasstable_icon_library.conf in
# $SPLUNK_HOME/etc/apps/itsi/local/. You must restart Splunk to enable
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

[default]
iconThumbnailSrc = <string>
* The file path of the icon. 
* Required.

[<stanza name>]
iconId = <string>
* An internal unique identifier for the icon.
* Required.

iconLabel = <string>
* The name or label for the icon that appears in the UI.

iconThumbnailSrc = <string>
* The file path of the icon. 
* Required.

iconCategory = ['Application'|'Splunk'|'Network'|'General']
* The assigned category for the icon.
* Required.

svgPath = <string>
* The SVG path for the icon. 
* The same path used for the icon library thumbnail.

defaultWidth = <positive integer>
* The initial width of the icon.

defaultHeight = <positive integer>
* The initial height of the icon.
