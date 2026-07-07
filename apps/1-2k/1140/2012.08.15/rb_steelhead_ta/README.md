iu-splunk-riverbed-steelhead-fwd
================================

Splunk for Riverbed Steelhead - Technology Add-On

--[ Introduction ]--

This is a self-contained Splunk application which parses log information for the interesting fields returned by the Riverbed Steelhead equipment.  Specifically, it looks for log lines which roughly match the following:

process(optional [processID]): [component.LOGLEVEL]

Log lines that match this expression are assigned a sourcetype of "riverbed_steelhead".

The forwarding component is a separate entity which needs to be installed on every Splunk instance that is taking input from a Riverbed device.  This is designed to be lightweight and simple for those folks who have deployed heavy forwarders.


--[ Installation ]--

Install the rb_steelhead_fwd directory on your input instances:

$SPLUNK_HOME\etc\apps

If you are using a Deployment server, place it here:

$SPLUNK_HOME\etc\deployment_apps


--[ Configuration ]--

A small collection of Steelhead devices logging on an INFO level will generate a metric ton of traffic.  This can very easily clog the Main index, and cripple performance for the userbase as a whole.

Do not neglect the possible performance impact on both the Steelhead and the network with this level of logging.  If may be beneficial to deploy universal forwarders at sites with remote units so that compression and reliable TCP transmission are available.

If this idea is appealing to you, it is advisable to create another index "riverbed_info" to keep these indexes.  Retention time is up to the administrator.  However, general usage scenarios (i.e. no reported problems with optimization) suggest that the indexes can be cleaned up and discarded after 7-14 days.

Please refer to the Admin Manual which discusses how to set up the index as well as its rate of decay.

As an option, local\props.conf.md can be copied to local\props.conf if you would like to forward INFO logs to a separate, more rapidly-decaying index.


--[ Acknowledgements ]--

Application icon by flakshak - http://flakshack.deviantart.com