Netwrix (STEALTHbits) File Activity Monitoring App for Splunk

Netwrix (STEALTHbits') file activity monitoring solutions enable organizations to 
successfully, efficiently, and affordably monitor file access and permission 
changes across Windows and NAS file systems in real-time, without any reliance on 
native logging.


--------------------------------------------------------------------------------
Version Support
--------------------------------------------------------------------------------

    v.2.0.0
        - Add app compatibility with Splunk Cloud environments
        - Netwrix rebranding
        - Add usage of Splunk "stealthData" macro
        - Update extractions to handle both "StealthINTERCEPT" and "STEALTHbits" 
            source types
        - Modified the eventtype names to replace any spaces with "_"
        - Added extra CIM compliance fields
        - Added a mapping for "Rename" events to the modified action
        - Removed "success" and "failure" as possible values in "action" field.
            These are now part of the "status" field
        - Changed the "Activity" and "Top Users" panels in the "Permission Changes"
            dashboard, to break down the count by permission change type 
        - Changed the "latest events" panel in the "Dashboard" dashboard into a 
            sortable table

    v.1.0.0
        - Improved query efficiency
        - Added CIM compliance

    v.1.0.0
        - Initial Release of App

--------------------------------------------------------------------------------
System Requirements
--------------------------------------------------------------------------------

    Splunk Console
    StealthINTERCEPT

--------------------------------------------------------------------------------
Installation
--------------------------------------------------------------------------------

    1. Log in to Splunk Web and navigate to Apps > Manage Apps.
    2. Click Install App from file.
    3. Upload the file and click Upload.
    4. Restart Splunk Web.

--------------------------------------------------------------------------------
Collecting Data
--------------------------------------------------------------------------------
    
    Configure the StealthINTERCEPT server to send data to Splunk via Syslog.
    
    You may choose to use SC4S, a Syslog server with a Universal Forwarder or
    direct Heavy Forwarder ingest.
    
    In all cases, you should configure your favoured approach to ingest the data
    with the sourcetype "StealhINTERCEPT" 
    
    You may also choose to create a dedicated index. You should recall the 
    specified index name for the next step

--------------------------------------------------------------------------------
Configuration
--------------------------------------------------------------------------------

    To expedite search performance configure the "stalthData" macro.
    
    This can be configured by going to
    Settings -> Advanced Search -> Search macros:
        - stealthData. 
        
    This is used to improve search performance and should be appropriately 
    modified to specify the index(es) you defined in the previous step.
    
    E.g.
         index=[yourStealDataIndex] (sourcetype=STEALTHbits OR sourcetype=
                 StealthINTERCEPT)
    
    If left unmodified, this defaults to searching across all indexes in the 
    Splunk environment.

--------------------------------------------------------------------------------
Troubleshooting
--------------------------------------------------------------------------------

    Data does not show up in the dashboard pages.
        - Make sure that StealthINTERCEPT is configured to send data to Splunk.
        - Make sure that StealthINTERCEPT as a UDP log source in Splunk and has
            the correct sourcetype and index definition.

--------------------------------------------------------------------------------
Support
--------------------------------------------------------------------------------

    Netwrix (STEALTHbits) Support:
    splunk@netwrix.com# Binary File Declaration
