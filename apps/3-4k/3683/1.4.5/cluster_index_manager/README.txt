Overview
================================================

This app helps to create Splunk cluster indexes stanzas in $SPLUNK_HOME/etc/master-apps/_cluster/local/indexes.conf file.
App will use existing file or create new if it does not exist.
Values that will be saved to file:

[INDEX_NAME]
homePath = $SPLUNK_DB/INDEX_NAME_LOWERCASE/db
coldPath = $SPLUNK_DB/INDEX_NAME_LOWERCASE/colddb
thawedPath = $SPLUNK_DB/INDEX_NAME_LOWERCASE/thaweddb
maxTotalDataSizeMB = INDEX_SIZE_IN_MB
frozenTimePeriodInSecs = INDEX_LIFETIME_IN_SECONDS
enableTsidxReduction = true                                                 Optional
timePeriodInSecBeforeTsidxReduction = INDEX_REDUCTION_TIME_IN_SECONDS       Optional
repFactor = auto

Install app on Master node which have rights to deploy configuration to other peers.

If you need to modify or delete index configuration then do it manually in $SPLUNK_HOME/etc/master-apps/_cluster/local/indexes.conf file.

Changelog
================================================

1.4.5. Small app internal update. Add "python.required".
1.4.4. Add more index lifetime options. Update size and time display functions.
1.4.3. Add more size options.
1.4.2. Add table data filtering option.
1.4.0. App is compatible with Splunk new app framework.
1.3.1. Fixed compilation and compliance issues.
1.3.0. Make app compatible with Python 3. If you are using older Splunk server with Python 2, then use app version 1.2.1.
1.2.1. Removed local.meta file from metadata directory and some unused options in commands.conf.
1.2.0. Added an option to specify Tsidx reduction time (http://docs.splunk.com/Documentation/Splunk/6.6.3/Indexer/Reducetsidxdiskusage).
