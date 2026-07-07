== author ==
ThreatStream

== feedback ==
support@threatstream.com

== ThreatStream Splunk App ==

The ThreatStream Splunk App is available for download on Splunk Apps (http://apps.splunk.com) and is packaged as a standard Splunk application.  The primary goal of the application is to add threat intelligence context to existing customer event data based on common industry accepted Indicators of Compromise (IOC) keys such as file hash, domain, src/dest ip address, e-mail address, etc.

The ThreatStream Splunk App provides the following functionality that can be used in a standalone manner or integrated into existing customer workflows as a value add on top of existing business processes:

1.	Event Dashboard detailing recent customer event(s) containing an indicator match.
2.	Graphical Dashboard depicting various aspects of the customer event data containing an indicator match.
3.	Pre-defined real-time alerts which show up in the Triggered Alerts Splunk menu
4.	Graphical Dashboard providing a high-level overview of the local ThreatStream Indicator database.

== System Requirements ==
Splunk 7 or Splunk 8.

== Setup ==
These instructions are not a replacement for the Splunk ThreatStream App Admin Guide available from Anomali

1. Install this App onto a Splunk instance
2. Use the setup screen to configure the App settings
3. Configure constraints for the Datamodels within scope of the Splunk ThreatStream App
4. Follow post-deployment steps in the Admin Guide to get all features of the App working

== Documentation ==
https://ui.anomali.com/download

== Notes ==

*  Instructions on how to run through the initial configuration after registration are detailed in the above documentation
*  This App relies on the use of accelerated data models for performance.

== This App Includes ==

* Modular Input ts_ioc_ingest - For the downloading and ingestion of threat intelligence
* Setup Handler ts_setup_handler.py - For the setup of the app and proper handling of credentials
* Adaptive Response analyzeioc.py - For the feedback of threat intelligence from a Splunk instance to Anomali at the customer's discretion
* Custom Alert Action ts_my_attacks.py - For feedback of reduced outbound threat intlligence types to Anomali at the customer's discretion
* Custom Generating Search Command tssampleevents - For the creation of test logs within the App that act as positive matches
* Custom Search Command ts_match_match.py and ioc_metafilter.py - We recommend these are *not* used. Primarily  for advanced handling of duplicated Threat Intelligence

== For Splunk Cloud Vetting ==

*  This app uses multithreading to download threatmodels in a polling fashion, a maximum of 4 threads are used to conduct this download when the ts_ioc_ingest process is run
*  The Popen python module is used to run the btool command and get the Splunk management port from web.conf. We adapted this pattern from the Splunk Add-On Builder
*  After IOCs and ThreatModels are ingested into thr KVStore, the tssampleevents custom search command can be used to generate sample logs suitable for matching
