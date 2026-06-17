ConfigurationSync is a simple application to keep an offline search head in sync with one active search head. It is important that the offline search head is not running Splunk, and reasonable effort is made to ensure that the remote instance is not active.

Search head pooling in Splunk 4.2 and newer is vastly superior and should be used if at all possible. This script is only appropriate for installations where only one search head can be used, and the backup server is running without splunkweb, or not at all.

To use:
1. Make sure the user running Splunk can ssh to the destination machine without a password.
2. Edit DEST_SERVER in local/dest.conf.
3. Enable the app through Splunk's admin interface or by editing local/app.conf.

Output of the script is captured in Splunk in sourcetype=ConfigurationSync

Cheers,
Vincent
vbumgarner@splunk.com
