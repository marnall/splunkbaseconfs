Netwrix (STEALTHbits) Threat Hunting App for Splunk

Netwrix (STEALTHbits') Threat Hunting solution enables organizations to target and hunt 
active cyber threats. Using the preconfigured Netwrix (STEALTHbits) Threat Hunting App for 
Splunk, users can quickly understand all Threat Hunting as an incident response 
tool, it enables analysts to investigate the scope, impact, and root cause of an 
incident efficiently by analyzing patterns of activity indicative of account 
compromise and file system activity.


--------------------------------------------------------------------------------
Version Support
--------------------------------------------------------------------------------
    
    v.2.0.0
        - Add app compatibility with Splunk Cloud environments
        - Netwrix rebranding
        - Add usage of Splunk "stealthData" macro
        - Modify eventtype names to remove ':' character usage, and replaced
            spaces with "_"
        - Update extractions to handle both "StealthINTERCEPT" and "STEALTHbits" 
            source types
        - Added extra CIM compliance fields

    v.1.0.0
        - Initial Release of App

--------------------------------------------------------------------------------
System Requirements
--------------------------------------------------------------------------------

    Splunk Console
    StealthINTERCEPT (Active Directory and File System) 
    Netwrix (STEALTHbits) Standalone File Activity Monitor (File System)

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
