# This file contains attributes and values that ITSI Smart Mode uses to correlate
# notable events.
#
# There is a notable_event_correlation.conf in $SPLUNK_HOME/etc/apps/SA-ITOA/default/.
# To set custom configurations, place a notable_event_correlation.conf in
# $SPLUNK_HOME/etc/apps/SA-ITOA/local. You must restart Splunk software to enable
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

[<smart_mode_correlation_engine>]
* The settings under this stanza determine how ITSI Smart Mode analyzes notable
  event fields to determine whether they contain textual or categorical content.
* Smart Mode uses machine learning to compare event field values and group
  events that are related to each other.
* CAUTION: This configuration file does not support adding any additional stanzas.
  Do not add, remove, or change any of the settings or stanzas in this file unless
  specifically instructed to by a Splunk support specialist.

####
# BLACKLIST FIELDS
####
black_list_fields = <comma-separated list>
* A list of field names in a notable event whose values to discard
  from consideration for Smart Mode event correlation.

####
# TEXTUAL FIELDS
####
text_field_names = <comma-separated list>
* A list of field names in a notable event that usually
  represent textual content.
* A text field is a data structure that holds alphanumeric data,
  such as name and address.
* Defaults: comment,description,summoary,review,message

ignore_fields_that_contain = <comma-separated list>
* A list of field names to implicitly ignore because they are not useful
  for event correlation.
* ITSI ignores field names that contain any of the words in this list.
* For example, with the default "time", ITSI ignores fields that represent
  time, like alert_triggertime, alerttriggertime, lasttimeup, etc.
* Default: time

threshold_event_coverage_perc = <int>
* A threshold value for considering a notable event field
  as a text field.
* If the count (total number of occurrences) of a field divided by
  the total number of events processed in the time frame is less
  than the percentage specified in 'threshold_event_coverage_perc',
  then the notable event field is a text field.
* Default: 10

####
# CATEGORICAL FIELDS
####
threshold_distinct_value_perc = <int>
* A threshold value for considering a notable event field
  as a categorical field.
* If the distinct_count (count of distinct values) of a field
  divided by the count (total number of occurrences) of the field is
  less than the percentage specified, then the notable event field
  is a categorical field.
* Categorical fields have a distinct value, such as a status field,
  as opposed to textual data, descriptions, numerical values, and comments.
* If this setting determines that a field is NOT a categorical field, ITSI uses
  the two settings below ('min_distinct_value_perc' and 'max_count_perc')
  in a second calculation to check whether the field is a categorical field.
* Default: 35

min_distinct_value_perc = <int>
* Helps confirm whether a notable event field is a categorical field.
* Sets the minimum distinctive value percentage that a notable event field must
  be to be considered a categorical field.
* If the cumulative sum of ‘min_distinct_value_perc’ of distinct_count (count
  of unique values) of a field is at least ‘max_count_perc’ of the count
  (total number of occurrences) of the field, then the notable event field is
  considered a categorical field.
* For example, consider the following field:value pairs:
  {field:value1 count:34},{field:value2 count:31}, {field:value3 count:5},
  {field:value4 count:5} , ..., {field:value18 count:1} {field:value19 count:1},
  {field:value20 count:1}
  There are 20 different values listed for this field, so distinct_count = 20.
  ITSI sums the counts of all the values, so count = 80.
  80% of count = 64
  10% of distinct_count = 2, so you add the counts of the first two values above (34 + 31).
  {field:value1 count:34} + {field:value2 count:31} = 34 + 31 = 65 > 64
  Because 65 is at least 64, "field" is a categorical field.
* Default: 10

max_count_perc = <int>
* Helps confirm whether a notable event field is a categorical field.
* Sets the maximum count percentage that a notable event field must
  be to be considered a categorical field.
* If the cumulative sum of ‘min_distinct_value_perc’ of distinct_count (count
  of unique values) of a field is at least ‘max_count_perc’ of the count
  (total number of occurrences) of the field, then the notable event field is
  considered a categorical field.
* See the example for the 'min_distinct_value_perc' setting to understand
  how this setting works.
* Default: 80
