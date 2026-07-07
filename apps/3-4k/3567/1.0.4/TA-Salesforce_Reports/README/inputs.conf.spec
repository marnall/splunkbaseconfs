[salesforce_report://<name>]
username = Salesforce login username or email.
password = Salesforce login password.
security_token = User's security token (see Salesforce documentation).
report_id = https://na1.salesforce.com/[REPORT_ID]
enable_indexing = Write records to specified index.
enable_kvstore = Write records to specified kvstore.
enable_lookup_configuration = Creates and updates a lookup (knowledge object) and updates fields if "Enable KVStore" is enabled. Defaults to input name if undefined. (Requires Enable KVStore)
kvstore = If enabled, kvstore name to write returned records. Defaults to input name if undefined.  (CAUTION: Using same kvstore in multiple inputs may inadvertently corrupt data.)
kvstore_key = Fieldname in returned results to be used to as unique record identifier (_key). Defaults to 'none', which may result in duplicate records if not purge not enabled. (Requires Enable KVStore)
enable_purge = Choose option to purge all contents of the specified kvstore (default), purge records created by this input (multiple inputs may write to same kvstore), or  disable purge for this input.