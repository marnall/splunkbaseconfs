## FYI, Recommend Setting Index to store only 7 days worth of VJM data ##
## The Setting frozenTimePeriodInSecs = 604800 to each index configuration below to apply this##
[vj_ex]
coldPath = $SPLUNK_DB/vj_ex/colddb
homePath = $SPLUNK_DB/vj_ex/db
thawedPath = $SPLUNK_DB/vj_ex/thaweddb
enableDataIntegrityControl = 0
enableTsidxReduction = 0
maxTotalDataSizeMB = 2048
frozenTimePeriodInSecs = 604800