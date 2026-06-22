

# If the given sourcetypes are present within the current timerange,
# then the value in this stanza will be loaded in the Data Types pulldown.
[<data_type>]

#optional - detail view that can be linked to from Investigate pages when appropriate
detail_view = <view name>

# space separated list of the sourcetypes that comprise this data type.
sourcetypes = <SPL expression>


# 1 or more fields, unique values of which are sufficient to reliably identify, within these given sourcetypes, a single object or a single call
object_ids = <comma separated field list>

# SPL that should be inserted just prior to the stats command that rolls things up by object_id,  that can
# do something to the raw rows that needs doing.  Typically this involves eventstats/streamstats/eval
streaming_extractions = <SPL, generally a macro expression that is exported to system>

