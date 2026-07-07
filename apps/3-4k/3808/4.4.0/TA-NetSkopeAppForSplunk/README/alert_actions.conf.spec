[netskope_file_hash]
param.file_hash_list_name =<string> Name of the list which will be updated with hashes. Default is "splunk_file_hash_list".
param.global_account = <string> Netskope Account on which action should be performed.
param.index = <string> Index where results are written for Incident Review dahsboard in Enterprice Security.
param.action = <string> Action to take with the hashes.
param.column_name = <string> Field containing single hash (MD5 or SHA256) to perform Action upon. Default is "file_hash".
param._cam = <string> CIM Actions / Adaptive Response Requirement.
python.version = Select which Python version to use. {default|python|python2|python3}

[netskope_url]
param.url_list_name = <string> Name of the list which will be updated with URLs. Default is "splunk_url_list"
param.global_account = <string> Netskope Account on which action should be performed.
param.index = <string> Index where results are written for Incident Review dahsboard in Enterprice Security.
param.action = <string> Action to take with the URLs.
param.column_name = <string> Field containing single URL to perform Action upon. Default is "url".
param._cam = <string> CIM Actions / Adaptive Response Requirement.
python.version = Select which Python version to use. {default|python|python2|python3}

[netskope_quarantine_file]
python.version = python3
param.storage_account = <string> Micrtosoft Storage Account on which action should be performed.