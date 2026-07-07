[armis_alerts://<name>]
global_account = Select global account
python.version = {default|python|python2|python3}
armis_index = Select armis alerts index

[armis_api_alerts://<name>]
global_account = Select global account
python.version = {default|python|python2|python3}
lookback_days = Number of days from alert events will be fetched.

[armis_device://<name>]
global_account = Select global account
inventory = Please select checkbox for Fetch Application inventory
aql_query = Provide the AQL query
device_fields = Provide Fields
visibility_device = To enable all devices to be retrieved (Both Full and Limited visibility devices) uncheck the checkbox.
python.version = {default|python|python2|python3}

[armis_vulnerability://<name>]
global_account = Select global account
index_vuln_match_data = Ingest Vuln-Match data to index. Default it will be directly ingested into lookup.
vulnerabilities_chunk = Provided vulnerabilitiy ids will be passed in one call of vuln-match api.
python.version = {default|python|python2|python3}