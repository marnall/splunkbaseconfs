############################################################################
# OVERVIEW
############################################################################
# This is experimental.
# this is where objects are defined, and which field defines them as a guid
# simple:
#   | stats list(origDeviceName) as origDeviceName by call_id
# shouldn't the 'initial' and 'terminating' be replaced by some... generic way of doing it to any field?
#   | stats first(callingPartyNumber) as initialCallingPartyNumber
# chained, with temporary fields:
#	| stats  min(_time) as earliestTime max(_time) as latestTime by call_id
#   | eval duration_elapsed=latestTime-earliestTime
#   | fields - earliestTime latestTime
[<name>]
#required
groupby = <field name>

# it may make more sense to NOT have this key
# but instead to have primary_object=call on the 'secondary' objects.
#.this would enable multiple layers ..
# list departments --> find users in this department  --> find sessions from this user.
#is_primary = <boolean>

#optional
appears_as = <comma separated string>

#optional. If omitted the stanza name will be used.
singular = <name>
plural = <name>

default_stats_function = <function>


indexes = <comma separated string>
#optional.   If defined, this SPL syntax is run before to the SPL extracting any fields
# and also before any search filtering
required_streaming_spl = <search syntax>

#optional. Determines what fields should be selected by default in any user interfaces
default_selected_fields = <comma separated string>

[<name>::<field>]


#required.  <field> is the stats/chart function that will be called on the values of <field>
function = <name>  # eg list, values, dc, sum

#required.   can be comma separated if the values come from more than one sourcetype.
sourcetype = <name>



# optional.  extra SPL required in the streaming portion to create/normalize this particular field properly.
# implicitly, this is for things that for whatever reason can't be done inside calc fields or ingest_eval
# a typical example would be if there is a custom streaming search command that does some manipulation to create the field.
required_streaming_spl = <name>

#optional.   if defined, you get   list(source_field) as field
source_field  = <name>

# optional, defaults to false. Causes the field to be deleted at the end of the SPL.
temporary = true

