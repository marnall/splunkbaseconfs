The SpyCloud Investigations App for Splunk allows customers to query the SpyCloud API from within a Splunk Dashboard using custom search commands.

# Splunk Version Support: #
- Splunk 8.0, 8.1, 8.2, 9.0

# Installation: #
1. Valid Installation location: Search Head
2. When opening the app, you will be redirected to the "SpyCloud Configurations" view. If this doesn't happen, click "SpyCloud Configuration" on the app's navigation bar.
3. Enter the appropriate configurations.
4. Click "Save Configurations" and wait for setup to complete. 


# Setup Page: #
- Be sure to enter a valid SpyCloud Investigations API Key and appropriate API Results Quota Limit. 
- The quota results limit applies every time a query is made through the custom search commands.
- Proxy:
    - Proxy Url must use the <scheme><IP>:<port> format. Ex. https://10.10.10.10:8080
    - If you wish to use authentication, ensure you provide a username and password, otherwise leave the username field empty to disable authentication. 


# Features: #
- Check Query Count: A button on the dashboard provides the number of records that will be returned based on the query created in the dashboard without retrieving all the results. 
- Breach Catalog: A copy of the breach catalog is created as a lookup on initial app setup. After the initial creation you have the option to manually update this catalog via the "Update Breach Catalog" button. 


# SpyCloud Investigations App for Splunk Dashboard #
The dashboard allows customers to query a value for a particular endpoint and includes the features mentioned above.

# Search Commands: #
- scinvget : Generating command used by the dashboard 
    Parameter Breakdown:
        endpoint (required) - string value of endpoint that is predetermined by the dashboard dropdown (accepted values in note below)
        field (required) - string to query for given endpoint (ex: "test@example.org") 
        fuzzy (required) - boolean to determine fuzzy search (ex: False)  
        source_id (optional) - integer indicating a specific breach source ID to query (ex: 1234)
        severity (required) - a comma delimited list of severities to use for the query, this is prescribed by the dashboard checkboxes (ex:"25,20,5,2")
        quota_check (optional) - boolean to determine if the query will return the record and queries required to retrieve all results (ex: False) 
            Note: A "result" field is returned when this option is "True"
- scinvsearch : Streaming command to apply against splunk events.
    Parameter Breakdown:
        endpoint (required) - string value of endpoint that is predetermined by the dashboard dropdown (accepted values in note below)
        field (required) - field name in the Splunk results to use as the query value (ex: email_address) 
        fuzzy (required) - boolean to determine fuzzy search (ex: False)  
        source_id (optional) - integer indicating a specific breach source ID to query (ex: 1234)
        severity (required) - a comma delimited list of severities to use for the query, this is prescribed by the dashboard checkboxes (ex:"25,20,5,2")

NOTE: Accepted "endpoint" parameter values are: "domain","email","username","ip","password","machine_id","phone_number","email_username","social_handle","cc_number","bank_number","drivers_license","national_id","passport","ssn"


# Saved searches: #
- SpyCloud_Catalog_Create
    This search is used to create the breach catalog lookup on initial setup. In the event that this initial setup process fails, this search can be 
    ran to create the lookup file.  
- SpyCloud_Catalog_Update
    This search provides updates to the breach catalog lookup and is dispatched by the "Update Breach Catalog" button in the dashboard.
    If you would like to periodically update the breach catalog, you can scheduled this search. 
    IMPORTANT NOTE: When scheduling, ensure the time range remains at "All Time" to retrieve the entire breach catalog.
- sc_check_latest_breach_update
    This search looks for the latest "_time" field value in the breach catalog lookup to determine the last time it was updated.
    This is called when the dashboard is loaded and after the "Update Breach Catalog" button is done processing the update. 


# Lookups: #
- sc_breach_catalog
    This lookup file is created on initial setup and can be updated manually with a button in the dashboard.
    Contains enrichment information pertaining to specific breaches.

# Release Notes: #
v. 1.0.0
- Initial release

# Troubleshooting #
 - If necessary, change the logging level in the "SpyCloud Configuration" page.
 - The commands log to the _internal index. To search the logs you can use the following search "index=_internal sourcetype="sc:investigations:log""

# Support: #
 - Support for this app is provided during weekday business hours (US, Central Time).
 - Please open a support case through the SpyCloud customer portal at https://portal.spycloud.com/.


The following license applies to all parts of this software except as
documented below:

====

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
