############################################################################
# OVERVIEW
############################################################################
# this defines the configuration file format for Sideview's proprietary 
# "data types" concept.  A "data type" consists of one or more sourcetypes
# and various other config requires to make that data, when present in Splunk
# become navigable / usable / reportable,  in Sideview's commercial 
# "Cisco CDR Reporting and Analytics" app.

# If the given sourcetypes are present within the current timerange, 
# then the value in this stanza will be loaded as an option in the Data Types 
# pulldown in the Cisco CDR app.
[<data_type>]

#the label that you wish the data type to have in any lists or form elements.
label = "<string>"

#optional - detail view that can be linked to from Investigate pages when 
# appropriate
detail_view = <view name>

# required - this defines the sourcetypes of the data. Must have at least one 
# sourcetype.  Be aware that these will be used in both tstats expressions as 
# well as in raw data searches.
# as of this writing all sourcetypes are assumed to be in the index or indexes
# defined in the `custom_index` macro in the Cisco CDR app.
sourcetypes = <space-separated list of sourcetype names>


# This defines the guid field(s) or rollup field(s) if you will. 
# In other words one set of unique values of these is sufficient to reliably 
# identify, within these given sourcetypes, a single object or a single call
object_ids = <space-separated field list>

# optional.  This is SPL that should be inserted just prior to the stats command 
# (the stats command that rolls things up by object_id(s)) ,  that does some 
# necessary modification to the raw rows.  Typically this involves 
# eventstats/streamstats/eval.  See existing Sideview-published SA apps for 
# examples
streaming_extractions = <SPL, generally a macro expression that is exported to system>

