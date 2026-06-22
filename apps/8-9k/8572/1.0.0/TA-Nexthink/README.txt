Nexthink NQL Add-on for Splunk
==============================

This Technical Add-on (TA) collects data from Nexthink using the NQL API v2.

OVERVIEW
--------
This add-on connects to Nexthink's cloud API to execute saved NQL queries and 
ingest the results into Splunk. It uses OAuth2 authentication and the NQL API v2
execute endpoint for data collection.

INSTALLATION
------------
1. Install this add-on on your Splunk instance:
   - Search Head for searches only
   - Heavy Forwarder for data collection in distributed environments
   - Standalone Splunk for single-instance deployments

2. Navigate to the add-on's Configuration page
3. Add your Nexthink account credentials
4. Create an input to start collecting data

PREREQUISITES
-------------
1. A Nexthink account with API access
2. OAuth2 API credentials (Client ID and Client Secret) from Nexthink
3. At least one saved NQL query in Nexthink with a Query ID
4. Network access from Splunk to Nexthink cloud APIs:
   - Token endpoint: https://{instance}-login.{region}.nexthink.cloud
   - API endpoint: https://{instance}.api.{region}.nexthink.cloud

CONFIGURATION
-------------

1. Account Setup (Configuration > Account tab):
   - Account Name: A unique identifier for this configuration
   - Instance Name: Your Nexthink instance name (e.g., 'company-prod')
   - Region: Your Nexthink cloud region:
     * us  - United States
     * eu  - Europe
     * pac - Asia Pacific
     * meta - Middle East
   - Client ID: OAuth2 Client ID from Nexthink
   - Client Secret: OAuth2 Client Secret from Nexthink

2. Input Setup (Inputs page):
   - Name: A unique name for this input
   - Account: Select the configured account
   - NQL Query ID: The saved query ID (e.g., '#inventory_query')
   - Interval: Collection frequency in seconds (minimum 60)
   - Index: Destination Splunk index
   - Sourcetype: Data sourcetype (default: nexthink:nql)

CREATING NQL QUERIES IN NEXTHINK
--------------------------------
1. Log into Nexthink Portal
2. Go to Investigations > NQL Editor
3. Write your NQL query
4. Save the query with a name (this becomes the Query ID)
5. The Query ID format is: #query_name (e.g., #inventory_query)

EXAMPLE NQL QUERY
-----------------
devices
| list
    device.collector.uid,
    device.name,
    device.entity,
    device.operating_system.platform,
    device.operating_system.name,
    device.hardware.type,
    device.hardware.manufacturer,
    device.hardware.model,
    device.last_seen
| sort device.last_seen desc

DATA FORMAT
-----------
Each record from the NQL query is ingested as a separate JSON event with:
- sourcetype: nexthink:nql (or custom value)
- source: nexthink:nql:#query_id
- index: as configured

TROUBLESHOOTING
---------------
1. Check the add-on's internal logs:
   index=_internal sourcetype=ta-nexthink-nql*

2. Common issues:
   - "Token request failed": Verify Client ID/Secret and network access
   - "Query not found": Ensure Query ID starts with # and exists in Nexthink
   - "403 Forbidden": Check API credentials have 'service:integration' scope

3. Enable DEBUG logging in Configuration > Logging for detailed troubleshooting

SUPPORT
-------
For issues, check the Splunk Community or contact your Splunk administrator.

LICENSE
-------
Apache License 2.0
