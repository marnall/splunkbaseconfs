Requirements
============

The VMRay Platform Add-On for Splunk® requires the VMRay REST API and summary JSON v2.
To enable the REST API, go to "System Settings" » "Global Configuration" on the
VMRay Platform Server. Under "API" enable the checkbox labeled "Enable REST API".
Additionally, you'll need an API Key of a valid user ("Analysis Settings" » "API Keys").
To verify that summary JSON v2 generation is enabled, go to "Analysis Settings" »
"Dynamic Configurations" and verify that the option "Create summary JSON v2" is
enabled in the root configuration of the respective analysis engines.


Installation
============
Extract the folder into "$SPLUNK_HOME/etc/apps" (this should create the folder
"$SPLUNK_HOME/etc/apps/TA_vmray_platform") and restart Splunk. Alternatively,
you should be able to install the zip file via the Splunk UI ("Manage Apps"
-> "Install app from file" -> choose the appropriate file and click upload).
You might need to restart Splunk.


Usage / Configuration
=====================

After the app is installed you can use the VMRay Platform like any other data
source.
To add a new VMRay Platform server go to "Settings" -> "Data inputs" and
select "VMRay Platform". The page shows currently added servers. To add a new
server click on "New". The new dialog requires you to provide several
configuration parameters which are described in detail in the next paragraph:

Required Fields:
    Name -  The name of the new input. This name can be used to search for
            events only emitted by this source. Example: if we set the name to
            "myserver" we can limit the search via
                "source=vmray_platform://myserver"

    Server IP Address - The hostname or IP address of the VMRay Platform server.
                        Must be reachable from Splunk.

    API Key -   The REST API key of an VMRay Platform user.

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
                        The add-on will only import analyses which finished
                        after the analysis with the given id. The
                        integer must be larger than zero. If the field is left
                        empty or is set to 0 the addon will import all
                        analyses. Use this field if you do not want to import
                        all analyses.

                        CAUTION: Once this field is set it should not be
                        modified. Modification of this field can lead to
                        duplicate events in the index.

    Analysis Properties -    Enables the import of the actual analysis
                             results. You probably want to enable this.
                             Sourcetype: vmray:analysis
                                
    VTI Matches -    Imports the triggered VTI rules.
                     Sourcetype: vmray:vti_match

    YARA Matches -      This enables the import of information, which shows
                        which YARA rules have been triggered by an analysis.
                        Sourcetype: vmray:yara_match

    Built-in AV Matches -   Built-in AV matches for this analysis.
                            Sourcetype: vmray:av_match
    
    Reputation Lookups - Reputation lookups for this analysis.
                         Sourcetype: vmray:reputation_lookup
    
    Artifacts -          Artifacts that were seen during the analysis.
                         Sourcetypes: vmray:domain_artifact,
                         vmray:email_address_artifact, vmray:email_artifact,
                         vmray:filename_artifact, vmray:file_artifact,
                         vmray:ip_address_artifact, vmray:mutex_artifact,
                         vmray:process_artifact, vmray:registry_record_artifact,
                         vmray:url_artifact

    IOCs only -   Only import Artifacts that were classified as an
                  Indicator of Compromise (IOC).

    Extracted Strings - Import strings extracted from the dynamic behavior
                        of the processes.
                        Warning: Can be a large amount of data.
                        Sourcetype: vmray:extracted_strings

    Network Activity - Import information about network activity observed
                       during analysis:
                       Sourcetypes: vmray:dns_query, vmray:http_request,
                       vmray:tcp_session, vmray:udp_stream

    Analysis Details - Import information about the VM used to analyze
                       the sample, including product and engine versions,
                       application versions etc.
                       Sourcetype: vmray:analysis_details

    Remarks - Import analysis remarks, e.g. system was rebooted.
              Sourcetype: vmray:remark

    Static Analysis Data -  The static data for file artifacts from the 
                            static engine.
                            Warning: Can be a large amount of data.
                            Sourcetype: vmray:static_data


Enable Imports per Submission

    Start Submission ID -   The starting submission_id. Only submissions which
                            finished later will be imported into Splunk. If not
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

    Enable Timing Import -  Imports timing information. This is for debugging
                            purposes only.

    Enable Size Import -    Imports size information. This is for debugging
                            purposes only.

    Log Level -     Sets the default log level of the plugin. Defaults to 
                    Warning

    Internal Restricted Import Mode -   Removes any Personally identifiable
                                        information from the imported data.

    Interval -      Time between executions of this plugin.

    Index -         Destination index of this input.


Once you have entered the settings click "Next". After this you will find a
new row in "Settings" -> "Data inputs" -> "VMRay Platform" which corresponds
to the new data source you just added.

The new source will now start to populate Splunk with the analyses from the
VMRay Server.


Configure Adaptive Response
===========================
To configure Adaptive Response, navigate to the Splunk App Manager. Find the
Add-On in the list and on the right side click "Set up".

    IP or hostname - The hostname or IP address of the VMRay Platform server.
                     This IP must be reachable from Splunk.

    REST API Key -   The REST API key of an VMRay Platform user.

    Disable Certificate Verification - 
                     Disables the SSL/TLS certificate verification when
                     contacting the VMRay Server.

                     CAUTION: Enabling this setting could leave you
                     vulnerable to man-in-the-middle attacks. Disable
                     only if you know what you are doing.

    HTTP Proxy -     The full URL of the proxy to use. You can also use HTTP basic 
                     Auth.

    Adaptive Response target index -
            The index for the AR events.

    Enable ES Lookup generation -
            Enables export of file information to Splunk Enterprise Security
            (ES) Threat intel thread. This is done in CSV format. An export
            occurs if the VTI score is larger or equal than the score
            specified in the savedsearch VMRay Platform ES Threatintel generation.

            NOTE:
            This option does not depend on the settings above.
            If this is enabled, the addon will create a
            CSV file and places it in
            "$SPLUNK_HOME/etc/apps/TA_vmray_platform/lookups/vmray_es_threat_export.csv"
            where it can be consumed by Splunk Enterprise Security.
            http://docs.splunk.com/Documentation/ES/5.0.1/Admin/Addthreatintel 


Known Issues / Bugs
===================
    - Editing the set "Start Submission ID" can cause duplicate events. In
    particular, decreasing this value will cause this issue.

    - The addon uses the Splunk REST API via splunklib to create a config with
    stanzas according to the created inputs. These stanzas hold the
    last_submission_id and other information. This approach seems appropriate
    but could not be tested with more complicated Splunk setups.


Troubleshoot / Debug
====================
By default, the add-on will not write logging info except WARNINGs and above.
To change this edit TA_vmray_platform.py "logging.root.setLevel(logging.WARNING)"
to "logging.root.setLevel(logging.INFO)" or
"logging.root.setLevel(logging.DEBUG)". Alternatively, you can edit the log
level in the input's settings under "Log level" (see 'Usage/Configuration')
The log will be written to splunkd.log and the "_internal" index (only INFO
or higher in the default Splunk configuration).
You can find the messages in Splunk using this search:
    index=_internal execprocessor " VMRAY "


The last_submission_id is saved in a stanza in
$SPLUNK_HOME/etc/apps/TA_vmray_platform/local/vmray_platform.conf
Every input has its stanza which holds the last_submission_id which is used by
the addon to save its last downloaded analyses.
Manual editing of this config is neither supported nor encouraged.
However, if you need to change this setting
make sure to stop Splunk before you edit the file.


Acknowledgements and Contributors
=================================
We would like to extend our thanks to Dominik Oestreicher of doIT Solutions 
for his time spent graciously providing his suggestions and feedback on this
application.
