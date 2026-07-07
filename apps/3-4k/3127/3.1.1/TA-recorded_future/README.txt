Splunk ES Add-on for Recorded Future

Overview:

  The Splunk Add-on for Recorded Future is designed specifically for
  Splunk Enterprise Security.

  This Add-on integrates with the Splunk ES Threat Intelligence
  Framework by adding a feed containing information security threat
  indicators from Recorded Future. With this added feature, defenders
  can automate the process of finding connections between internal
  incidents and external sources. This can work bidirectionally:
  searching Recorded Future for more context around internally
  observed indicators, or testing trending indicators from open source
  reporting against internal data sets.

  The Add-on also simplifies the workflow of analysts working within
  the ES environment by adding contextual actions to the Incident
  Review and event searching and reporting views. This includes
  information on IPs, domains, file hashes and CVEs.

  For more information on Recorded Future, visit www.recordedfuture.com.

Documentation:

 Requirements

  - Splunk ES must be installed on the Splunk system. In a clustered
    environment the app should be installed on one or more  search
    head. See Clusters.txt in README for more information about
    running in a clustered environment.
  - A valid Recorded Future API token is required.
  - The Splunk server running the app must be able to download a CSV
    file containing Recorded Future's IP risk list from
    https://api.recordedfuture.com/.

 Installation

  To install this Add-on, perform the following steps:

  1.      Download the latest TA release from Splunkbase (apps.splunk.com)
  2.      In Splunk, select "Manage Apps" from the drop-down menu next
  	  to the Splunk logo on the upper left of the screen
  3.      Select "Install app from file"
  4.      Browse to the location of the TA-recorded_future.spl file,
          select it and upload. Restart Splunk when prompted to do so.
  5.      Go back to "Manage Apps". Locate "Splunk ES Add-on for
          Recorded Future" in the list and run "Set up".
  6.      Go to Settings->Data inputs->Scripts. Enable the script 
          get-rf-threatlists.py that corresponds to your platform
          (Windows or *nix).
  7.      In the Enterprise Security menu bar,
          click Configure -> Incident Management -> Incident Review Settings.
  8.      Click the button 'Add new entry' in the "Incident Review -
  	  Event Attributes" section. Add the following Label and Field
	  combinations:
	  
        Label                            Field
        ---------------------            ----------------------
        RF Risk Score                    rf_a_risk_score
        RF Risk Score Threshold          rf_risk_score_threshold
        RF Triggered Rules               rf_b_risk_string
        RF Evidence Details              rf_evidence_details_0
        RF Evidence Details 2            rf_evidence_details_1
        RF Evidence Details 3            rf_evidence_details_2
        RF Evidence Details 4            rf_evidence_details_3
        RF Evidence Details 5            rf_evidence_details_4
        RF Evidence Details (remaining)  rf_evidence_details_rest

  9.      A restart of the Splunk instance will be required once the
  	  installation has completed.
 10.      If you haven't already done so, enable the Enterprise
  	  Security correlation search called "Threat Activity Detected"
          a. In the Enterprise Security menu bar,
	     click Configure -> Content Management
          b. In the filter bar, type "Threat Activity Detected"
          c. Click the link 'Enable' to enable the correlation search
 11.	  Optionally, make the logs from the app available in the Splunk
 	  GUI. Ex:
	  - Add an index _TA-recorded_future
	  - Setup a Data input that monitors
	  $SPLUNK_HOME/var/log/TA-recorded_future and insert these events
	  into the new index.

  Alternatively, you can download the Add-on using the Splunk Web
  interface's "Find more apps online" feature. Steps 5 and onwards
  above must still be completed.

 Upgrade from 2.x versions

  Due to the extent of the changes between version 2 and 3 of the app
  you must remove the app directory
  ($SPLUNK_HOME/etc/apps/TA-recorded_future) and make a fresh install
  of the app.

 Upgrade from 3.0.4 and earlier version

  The location of the app log have changed du to requirements from
  Splunk. The new location is in
  $SPLUNK_HOME/var/log/TA-recorded_future/TA-recorded_future.log.

 Setup

  After installation, you will need to set up the Add-on for Recorded
  Future to communicate with the Recorded Future API. The setup page
  will request your API token, and the Add-on will not import threat
  information without this. This is described in step 4 of the
  installation procedure above.

  The Setup view can also be used to enable debug logging if required
  and to enter proxy information is the Splunk server is required to
  use a proxy when downloading the risk lists from
  https://api.recordedfuture.com.

  The script which retrieves the lists of IP number etc will select a
  Risk Score Threshold which will produce a set number of entries in
  the list. By default this number is 25.000. This number can be
  changed by editing the file recorded_future.conf in the local
  directory in the app directory. Ex:

  [ip_risk_list]
  max_entries = 25000

  Be aware of that increasing this number will significantly increase
  the load on the server.

External data access and scripts

  The app uses a script to retrieve threat information from Recorded
  Future. This script is run (default every 5 minutes) from a stanza
  in inputs.conf. This threat information contains IP numbers, Domain
  names and Hashes which are considered suspicious or malicious by
  Recorded Future. Each entity has a Risk Score and evidence of why
  that is assigned to it. The data contains all entities with a Risk
  Score of 25 or more (100 being the maximum).

  During the execution one https call is made to
  https://api.recordedfuture.com/ to retrieve the information which is
  then processed and stored on the Splunk server for each type of
  data.

Cluster considerations

  If using a large risk lists (see the Setup section above) it may be
  advisable to avoid transferring it across cluster nodes. This will
  however force the lookups to be performed locally on the search
  head, putting additional strain on that node.

  If you want it to perform the search locally, then you can:
  - add the parameter local=true to the custom search,
  - you can blacklist the lookup file from the indexers:
    https://docs.splunk.com/Documentation/Splunk/6.4.3/Admin/Distsearchconf

  If the Knowledge bundle is too large it may be necessary to lower
  the max_entries values in recorded_future.conf.

More information

  For more information and to set up your trial or paid subscription,
  please contact splunk@recordedfuture.com (US east coast business
  hours).
