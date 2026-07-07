# IntSights Splunk Technology Add-on
# Version 1.1.5

Splunk TA that pulls down IntSights' IoCs and adds to Splunk csv / kvstore lookup.IntSights' all-in-one External Threat Intelligence & Protection Suite equips enterprise security teams with unparalleled capabilities to detect, investigate, and neutralize external threats across the clear, deep, and dark web.

When fused with Splunk, IntSights' contextualized, external threat data acts as a powerful enrichment and correlation source for faster, more comprehensive security operations. SOC analysts minimize time wasted on false-positives while simultaneously unlocking deeper threat correlation and analysis-all from the ease and familiarity of the Splunk tools and workflows they already rely on day-in and day-out.

Installation

    A valid IntSights Account ID and API key are required.  For more information visit www.intsights.com.
    
    To configure this add-on:

    1. Install the app from Splunkbase
    2. Restart Splunk if prompted
    3. Navigate to the app's setup page and add your Account ID and API key.
    4. Click save after filling the required fields in the setup page.
    
    To troubleshoot this add-on:
    
    1.  Review logs files (%SPLUNK_HOME%/var/log/intsights/intsights.log, %SPLUNK_HOME%/var/log/splunk/splunkd.log)
    2.  Review REST storage/passwords (|rest splunk_server=local "/servicesNS/nobody/TA-intsights/storage/passwords")
    3.  Review REST TA-intsights/intsights/config_endpoint (| rest splunk_server=local "/servicesNS/nobody/TA-intsights/intsights/config_endpoint")
    
    storage/passwords REST can show up to 3 entries for 6 possibilities
        1 if tenant only
        1 if ispp only
        2 if ispp and tenant
        2 if ispp and proxy
        2 if tenant and proxy
        3 if tenant and ispp and proxy
    
    TA-intsights/intsights/config_endpoint shows 3 entries (one for each "function" [thread-command, tip, intsights-config])
        is_ingest_alert saved on thread-command
        serverities, types, weeks, sources filters saved on tip
        intsights-HTTPS_PROXY_ADDRESS on intsights-config
        proxy creds saved (but removed when posted to storage/passwords) on intsights-config
        intsights creds saved (but removed when posted to storage/passwords) on intsights-config
    
    
    
    
    
    
