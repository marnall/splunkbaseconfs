MS Exchange Forwarding Rules Add-on for Splunk
Copyright (C) 2021 CyberSecThreat Corporation Limited. All Rights Reserved.

================================================
Overview
================================================

This app is designed for collecting MS Exchange Forwarding Rules and integrate it with Splunk. 

We provided the powershell script(s) to collect MS Exchange Forwarding Rules and extract the needed fields.

1. Depends on your needs, you can use one of the following methods:
a. Configure Splunk universal forwarder of MBX to run as Exchange Admin, enable the required stanza in inputs.conf, and let Splunk generate the csv, collect/parse csv file and cleanup those csv file. Ingest csv file will consume less Splunk license.
b. Configure Splunk universal forwarder of MBX to run as Exchange Admin, enable the required stanza in inputs.conf, and let Splunk directly collect/parse using PowerShell.
c. Leave Splunk universal forwarder of MBX user unchanged, manually configure a windows schedule to collect/cleanup Exchange Forwarding Rules using our PowerShell script, enable the required stanza in inputs.conf to collect the generate csv file.

================================================
Configuring Exchange Forwarding Rules
================================================

1. Depends on your needs, you can use one of the following methods:
a. Configure Splunk universal forwarder of MBX to run as Exchange Admin, enable the following 3 stanza in inputs.conf, and let Splunk generate the csv, collect/parse csv file and cleanup those csv file. Ingest csv file will consume less Splunk license.
i)   [powershell://generate_exchange_mailbox_forward_rules_csv]
ii)  [powershell://cleanup_mailbox_forward_rules_csv]
iii) [monitor://$SPLUNK_HOME\var\log\TA_MS_ExchangeForwardingRules_for_splunk\MSExchange_ForwardRule_*.csv]
b. Configure Splunk universal forwarder of MBX to run as Exchange Admin, enable the following stanza in inputs.conf, and let Splunk directly collect/parse using PowerShell.
i)   [script://.\bin\run_exchange_ps.cmd on_premises_exchange_mailbox_forward_rules.ps1]
c. Leave Splunk universal forwarder of MBX user unchanged, manually configure a windows schedule to collect/cleanup Exchange Forwarding Rules using our PowerShell script, enable the following stanza in inputs.conf to collect the generate csv file.
i)  You need to provide the correct csv_path and csv_file arguments to the powershell collection script, e.g.:
"C:\Program Files\SplunkUniversalForwarder\etc\apps\TA_MS_ExchangeForwardingRules_for_splunk\bin\powershell\on_premises_exchange_mailbox_forward_rules.ps1" -csv_path "C:\Splunk" -csv_file "MSExchange_ForwardRule"
ii)  You need to provide the correct csv_path, csv_file and age arguments to the powershell collection script, e.g.:
"C:\Program Files\SplunkUniversalForwarder\etc\apps\TA_MS_ExchangeForwardingRules_for_splunk\bin\powershell\cleanup_exchange_mailbox_forward_rules_csv.ps1" -csv_path "C:\Splunk" -csv_file "MSExchange_ForwardRule" -age "-3"
iii) Configure the correct path of generate csv for the following stanza:
[monitor://$SPLUNK_HOME\var\log\TA_MS_ExchangeForwardingRules_for_splunk\MSExchange_ForwardRule_*.csv]

Other considerations:
1. You may deploy this add-on to DR/standby Exchange servers.
2. If you are planning to run it on non-Exchange instance, you need to install Exchange Management tools.
3. For mininum permission to run the powershell script, please refer to following: 
https://docs.microsoft.com/en-us/powershell/exchange/find-exchange-cmdlet-permissions?view=exchange-ps

================================================
Configuring Splunk
================================================
This app need to install on Splunk Search Head and forwarder(MS Exchange Server), and installed on Indexer/Heavy Forwarder.

Install this app into Splunk by doing the following:

  1. Log in to Splunk Web and navigate to "Apps » Manage Apps" via the app dropdown at the top left of Splunk's user interface
  2. Click the "install app from file" button
  3. Upload the file by clicking "Choose file" and selecting the app
  4. Click upload
  5. Restart Splunk if a dialog asks you to

Configure the input sourcetype as msexchange:mailforward or msexchange:mailforward:csv depends on your needs.

================================================
Known Limitations
================================================

N/A



================================================
Getting Support
================================================

This is an open source project and no active support is provided. If there is any issues, email to info@cybersecthreat.com during weekday business hours (GMT+8).




================================================
Change History
================================================

+---------+------------------------------------------------------------------------------------------------------------------+
| Version |  Changes                                                                                                         |
+---------+------------------------------------------------------------------------------------------------------------------+
| 1.0.0   | Initial release                                                                                                  |
|---------|------------------------------------------------------------------------------------------------------------------|