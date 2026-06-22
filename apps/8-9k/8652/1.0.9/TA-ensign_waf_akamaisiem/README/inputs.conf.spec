[akamai_siem_source://<name>]
akamai_account = Select the Akamai account to use. Accounts must be configured in Configuration > Akamai Accounts.
config_id = The Akamai security configuration ID to fetch SIEM events from (e.g., 12345).
index = Select the destination Splunk index for Akamai SIEM events. (Default: main)
interval = Data collection interval in seconds. (Default: 60)
limit_num = Maximum number of events to fetch per API request. (Default: 600000)
proxy_server = Optionally select a proxy server for this input.
custom_sourcetype = Override the default sourcetype for ingested events. (Default: ensign_akamaisiem)