Requirements
============

The VMRay Analyzer addon for Splunk® requires the VMRay REST API. To enable the
REST API go to the "System Configuration" on the VMRay Analyzer Server. Under
"System", choose "System Settings". Under "API" enable the
checkbox labeled "Enable REST API". Additionally, you'll need an API Token
of a valid user.


Installation
============
Extract the folder into "$SPLUNK_HOME/etc/apps" (this should create the folder
"$SPLUNK_HOME/etc/apps/TA-vmray-analyzer") and restart Splunk. Alternatively,
you should be able to install the zip file via the Splunk UI ("Manage Apps"
-> "Install app from file" -> choose the appropriate file and click upload).
You might need to restart Splunk.


Usage / Configuration
=====================

After the app is installed you can use the VMRay Analyzer like any other data
source.
To add a new VMRay Analyzer server go to "Settings" -> "Data inputs" and
select "VMRay Analyzer". The page shows currently added servers. To add a new
server click on "New". The new dialog requires you to provide several
configuration parameters which are described in detail in the next paragraph:

Required Fields:
    Name -  The name of the new input. This name can be used to search for
            events only emitted by this source. Example: if we set the name to
            "myserver" we can limit the search via
                "source=vmray_analyzer://myserver"

    Server IP Address - The IP address of the VMRay Analyzer server.
                        This IP must be reachable from Splunk.

    API Key -   The REST API key of an VMRay Analyzer user.

                To get the API key go to "System Configuration". Under
                "User" select "API keys". Then "Create new API key", select
                the appropriate user and click "Save". Copy the API key to
                the "API key" text box in the Splunk configuration. If the user
                already has an API key you can use the existing API key.

    Disable Certificate Verification - 
                            Disables the SSL/TLS certificate verification when
                            contacting the VMRay Server.

                            CAUTION: Enabling this setting could leave you
                            vulnerable to man-in-the-middle attacks. Disable
                            only if you know what you are doing.

    HTTP Proxy -    The full URL (e.g. http://10.10.1.10:8888) of the proxy
                    to use. You can also use HTTP basic Auth
                    e.g. http://user:pass@10.10.1.10:1234/

Enable Imports per Analysis:
    Start Analysis ID - 
                        The add-on will only import analyses with an
                        analysis_id larger or equal to the given integer. The
                        integer must be larger than zero. If the field is left
                        empty or is set to 0 the addon will import all
                        analyses. Use this field if you do not want to import
                        all analyses.

                        CAUTION: Once this field is set it should not be
                        modified. Modification of this field can lead to
                        duplicate events in the index.

    Analysis Properties -    Enables the import of the actual analysis
                             results. You probably want to enable this.
                                
    VTI Matches -    Imports the triggered VTI rules of analyses as
                     an event.

    YARA Matches -      This enables the import of information, which shows
                        which YARA rules have been triggered by an analysis.

    Local AV Matches -   Local AV matches for this analysis
    
    Reputation Lookups - Reputation lookups for this analysis
    
    WHOIS Lookups -      WHOIS lookups for this analysis
    
    MITRE ATT&CK -      The MITRE ATT&CK (TM) techniques that were seen 
                         during analysis
    
    Artifacts -          IOCs that were seen during the analysis

    Artifact Operations -   All IOC related operations with references to
                            files, gfncalls and processes 
    
    Extracted Files -       All IOC related operations with references to 
                            files, gfncalls and processes 

    Static Analysis Data -  The static data for file artifacts from the 
                            static engine 
    
    Processes -             Information about processes that were monitored 
                            during the analysis
                            
    Network Activity -      Information about network activity
                            
    VM and Analyzer -       Information about the VM used to analyze the sample,
                            including product and engine versions, application 
                            versions, as well as wear-and-tear artifacts that 
                            were used to create the VM
                            
    Remarks -               Analysis remarks, e.g. ramdisk run full, system
                            was rebooted, sleep truncated, ...

    Extracted Strings -     Information about the strings extracted from the 
                            dynamic behavior of the processes

Enable Imports per Submission

    Start Submission ID -   The starting submission_id. Submissions with a
                            lower id will not be imported into Splunk. If not
                            specified all analyses are imported. This field
                            can not be edited after creation!

    Submission Properties -  Enables the import of submission information.

    Sample Properties -  Enables the import of sample information.

More Settings:

    Max time to wait for a Submission to finish -
            ours to wait before an unfinished submission is imported to
            Splunk. Negative values indicate infinite timeout. Defaults to 4
            hours. If your queues tend to be long and a submission is not fully
            analyzed within 4 hours increase the time.

    Maximum number of items requested -   This field defines the upper bound of
                                analyses requested per interval. Change only
                                if you know what you are doing.

    Enable backup of exported CSV files -
                            Saves the CSV files exported to ES. Do not enable
                            unless you know what you are doing.

    Enable Glog Import -    WARNING: THE GLOG.XML FILES ARE _HUGE_. ENABLING
                            THIS SETTING WILL ALMOST CERTAINLY EXHAUST YOUR
                            QUOTA. IF YOU WANT TO ENABLE THIS SETTING MAKE SURE
                            TO SET A LIMIT ON YOUR LICENSE POOL. ALTERNATIVELY,
                            BUY A BIGGER LICENSE :)

                            Imports the _WHOLE_ glog.xml of the analyses as an
                            event.

    Enable Stix Import -    Imports the _WHOLE_ Stix/Cybox XML of the analyses
                            as an event.

                            CAUTION: The Stix/Cybox files can be quite large.
                            Hence, this setting could exhaust your daily quota
                            quite fast. Therefore, only enable if you know
                            what you are doing.

    Enable Timing Import -  Imports timing information. This is for debugging
                            purposes only.

    Enable Size Import -    Imports size information. This is for debugging
                            purposes only.

    Log Level -     Sets the default log level of the plugin. Defaults to 
                    Warning
                   
    Enable Summary Import -  Imports information from the summary.json. Results
                             are written into two events vmray:artifacts and
                             vmray:extracted_files. This is a legacy setting.

    Interval -      Time between executions of this plugin.

    Index -         Destination index of this input.




NOTE:   If "Enable Stix Export", "Enable Analysis import",
        "Enable Stix Import", "Enable Glog Import",
        "Enable YARA import", "Enable Timing import",
        and "Enable vti_result Import" are disabled no data will be indexd. The
        "Enable Stix Export" will not index data directly but will supply data
        to Splunk Enterprise Security. Use the other settings with extreme
        CAUTION. Most likely you will only need "Enable Analysis Import". Read
        the previous paragraph for more details.

Once you have entered the settings click "Next". After this you will find a
new row in "Settings" -> "Data inputs" -> "VMRay Analyzer" which corresponds
to the new data source you just added. By default, the new sources are added
as disabled. Recheck the settings and once you are certain everything is OK,
enable the new source.

The new source will now start to populate Splunk with the analyses from the
VMRay Server.


Configure Adaptive Response
===========================
To configure Adaptive Response, navigate to the Splunk App Manager. Find the
Add-on (VMRay) in the list and on the right side click Set up.

    IP or hostname - The IP address of the VMRay Analyzer server.
                     This IP must be reachable from Splunk.

    REST API Key -   The REST API key of an VMRay Analyzer user.

                     To get the API key go to "System Configuration". Under
                     "User" select "API keys". Then "Create new API key", select
                     the appropriate user and click "Save". Copy the API key to
                     the "API key" text box in the Splunk configuration. If the user
                     already has an API key you can use the existing API key.

    Disable Certificate Verification - 
                     Disables the SSL/TLS certificate verification when
                     contacting the VMRay Server.

                     CAUTION: Enabling this setting could leave you
                     vulnerable to man-in-the-middle attacks. Disable
                     only if you know what you are doing.

    HTTP Proxy -     The full URL of the proxy to use. You can also use HTTP basic 
                     Auth.

    Enable ES Lookup generation -
            Enables export of file information to Splunk Enterprise Security
            (ES) Threat intel thread. This is done in CSV format. An export
            occurs if the VTI score is larger or equal than the score
            specified in the savedsearch VMRay ES Threatintel generation.

            NOTE:
            If this is enabled, the addon will create a
            CSV file and places it in
            "$SPLUNK_HOME/etc/apps/TA-vmray-analyser/lookups/vmray_es_threat_export.csv"
            where it can be consumed by Splunk Enterprise Security.
            http://docs.splunk.com/Documentation/ES/5.0.1/Admin/Addthreatintel 
    
    Adaptive Response target index -
            The index for the AR events.



Additional Information
======================
For every event which can be imported via this plugin a sourcetype is
specified in the props.conf (e.g. "vmray:analysis"). This sourcetypes are used
to define eventtypes for the different events. The definition of these
eventtypes can be found in eventtypes.conf.
Eventtypes.conf also specifies in which index to search for these events.
If you changed the index in the configuration step you must change it in
eventtypes.conf as well, if you wish to use the predefined eventtypes.


Known Issues / Bugs
===================
    - Editing the set "Start Analysis ID" can cause duplicate events. In
    particular, decreasing this will value can cause this issue.

    - Export to ES is experimental!
    IF YOU MODIFIED THE DEFAULT SETTINGS (THE PATH WHERE ES LOOKS FOR
    FILES TO INGEST), IT WILL MOST LIKELY NOT WORK.

    - The addon uses the Splunk REST API via splunklib to create a config with
    stanzas according to the created inputs. These stanzas hold the
    last_analysis_id and other information. This approach seems appropriate
    but could not be tested with more complicated Splunk setups.


Troubleshoot / Debug
====================
By default, the add-on will not write logging info except WARNINGs and above.
To change this edit vmray_analyzer.py "logging.root.setLevel(logging.WARNING)"
to "logging.root.setLevel(logging.INFO)" or
"logging.root.setLevel(logging.DEBUG)". Alternatively, you can edit the log
level in the input's settings under "Log level" (see 'Usage/Configuration')
The log will be written to splunkd.log and the "_internal" index (only INFO
or higher in the default Splunk configuration).
You can find the messages in Splunk using this search:
    index=_internal execprocessor " VMRAY "


The last_analysis_id is saved in a stanza in
$SPLUNK_HOME/etc/apps/TA-vmray-analyzer/local/vmray_analyzer.conf
Every input has its stanza which holds the last_analysis_id which is used by
the addon to save its last downloaded analyses.
Manual editing of this config is neither supported nor encouraged.
However, if you need to change this setting
make sure to stop Splunk before you edit the file.


Acknowledgements and Contributors
=================================
We would like to extend our thanks to Dominik Oestreicher of doIT Solutions 
for his time spent graciously providing his suggestions and feedback on this
application.
