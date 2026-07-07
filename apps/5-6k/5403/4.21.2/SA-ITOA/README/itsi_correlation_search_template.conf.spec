# This file contains correlation search templates to bring in events from common 
# data sources. Leverage these templates to create new correlation searches. These searches
# are available during correlation search creation, not on the correlation search
# lister page.

# There is an itsi_correlation_search_template.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default. 
# To set custom configurations, place an itsi_correlation_search_template.conf in 
# $SPLUNK_HOME/etc/apps/SA-ITOA/local. You must restart ITSI to enable new configurations.

# To learn more about configuration files (including precedence), see the
# documentation located at
# http://docs.splunk.com/Documentation/ITSI/latest/Configure/ListofITSIconfigurationfiles.

# search = <string>
# The actual search string for the correlation search.
# Modify this default search to fit your specific use case.
# NOTE: You must specify the search index when creating a correlation search from a template.

# description = <string>
# A short description of the correlation search template.

# group = <string>
# The data type or source that the search belongs to.
# This setting is used for grouping related searches together in the UI menu.
