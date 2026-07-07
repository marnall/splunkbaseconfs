Netwrix (STEALTHbits) Active Directory Monitoring App for Splunk

Netwrix (STEALTHbits')Threat Manager provides many valuable controls for your 
IT infrastructure, and has many ways to utilize that data including real-time 
blocking and alerting. But holistic data reporting requires a more broad 
reaching platform such as Splunk. This app helps provide insight into the most 
common activities happening around your Active Directory.

--------------------------------------------------------------------------------
Version Support
--------------------------------------------------------------------------------
    
    v.2.0.0
        - Add app compatibility with Splunk Cloud environments
        - Netwrix rebranding
        - Add usage of Splunk "stealthData" macro
        - Modify eventtype names to remove ':' character usage, and replaced
            spaces with "_"
        - Removed the "StealthINTERCEPT File System Activity" eventtype
        - Update extractions to handle both "StealthINTERCEPT" and "STEALTHbits" 
            source types
        - Added extra CIM compliance fields
        - Changed the mapping of "Windows File System Access Rights Change" from
            "modified" to "acl_modified" in the "action" field
        - Removed "success" and "failure" as possible values in "action" field.
            These are now part of the "status" field
        - Changed the AD active users panel on the overview dashboard, to
            break down the count by AD type

    v.1.1.1
        - Improved support for analytics on authentication attacks page

    v.1.1.0
        - Improved query efficiency
        - Added CIM compliance
        - Added LDAP monitoring page

    v.1.0.0
        - Initial Release of App

--------------------------------------------------------------------------------
System Requirements
--------------------------------------------------------------------------------

    Splunk Console
    StealthINTERCEPT
    Machine Learning Toolkit for Splunk

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
