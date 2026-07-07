# This file contains attributes and values for configuring the cleanup of long-running episode summarization jobs.
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

[itsi_episode_summarization]
summarization_limit = <integer>
* The maximum number of summarizations allowed per quarter
* Default: 30000

throttling_limit = <integer>
* Throttling limit
* Default: 20

timeout = <integer>
* The number of seconds before episode summarization requests time out
* Default: 600

show_action_in_episode_view = <integer>
* Whether to show episode summarization action in episode view to allow adhoc summaries
* Default: 0
