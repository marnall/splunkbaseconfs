## Rapid7 InsightIDR for Splunk

###http://www.rapid7.com


## Using this Application:
   
### Setup:

Please see [Splunk's official documentation](http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall) for the initial installation of the add-on.
   
After installation, you should be prompted to set up the application. The configuration screen may also be accessed by clicking the "Configuration" link within the app's navigation bar or by selecting the 'Set up' action for the add-on within the App Management screen.
   
On this screen, enter the hostname or IP address of each of your InsightIDR collectors (e.g. collector.mynetwork.com).
    
Any change to these initial details can performed from the "Configuration" screen (accessible from the dashboard under the 'Rapid7 InsightIDR for Splunk' application).

Module details:
---------------------------------------

### Log Advancers: 

The term 'log advancer' used within the app refers to what is essentially a port forwarder. The log advancers solely forward data from Splunk to a remote server on a specific port. 

Note that the log advancers within the app are distinct from a Splunk Forwarder and do not comply with any of the expectations which come with using a Splunk Forwarder.

### Log Advancers Screen:

This screen displays all available log advancers. You have the option to create, edit or delete log advancers based on the data source.

To enable a log forwarder for a data source, click the corresponding "Enable" link. This will bring you to the "Configure a Log Advancer" screen (which is detailed below).

When a log advancer has been configured, clicking the "Edit" button will bring you back to this page so details may be amended. Alternatively, clicking the "Delete" button will remove the associated settings for that data source.

Please note that if you make any changes to the log advancers, you must restart the Splunk server for them to take effect. 

### Log Advancer Configuration Screen:

This screen allows you to select data to send to InsightIDR, as well as where to send it.

**Data source** - Host, source, or sourcetype. 

* **Host** - The name of the machine from which the data originates.
* **Source** - The source of data from the machine (such as tcp:1234 or /var/log/firewall.log)
* **Sourcetype** - The sourcetype with which Splunk has tagged the data. 

**Regex** - *Optional* - Regular expression for further data filtering. Only if the regex matches the whole payload will the      data be forwarded.

**Collector** - The host (presumably of one of your collectors) to which data will be sent. Make sure the selected collector has the corresponding event source set up to receive these events. The dropdown is filled with the collectors specified on the "Configuration" screen.

**Protocol** - The protocol to use when sending the data.

**Port** - The port on the collector machine to which data will be sent.

Note: This application must be installed on the Splunk node indexing the data that you want to forward to InsightIDR. Further to this it is preferable that the **raw** data should be passed to InsightIDR i.e. the untransformed data from the socket rather than the transformed data with a sourcetype.


### Receivers Screen:

Under the Receivers section, there is an entry for each port on which Splunk is listening for data.

To create a new receiver, enter the collector, protocol and port and click the "Create" button.

To delete a receiver, click the corresponding "Delete" link. 

Note that only a single receiver may have the same combination of collector, protocol and port.

Also, in order to have multiple receivers listen to the same protocol and port combination, they must each have a unique collector specified. It is not possible to have a receiver _without_ a collector and a receiver _with_ a collector for the same protocol and port combination.

* **Collector** - *Optional* - If selected, only data coming from the specified host will be handled by this receiver. The dropdown is filled with the collectors specified on the "Configuration" screen.
* **Protocol** - The protocol to use to listen for events.
* **Port** - The port on which to listen.
* **Sourcetype** - The sourcetype Splunk will apply to the data matching this receiver.
   
## Debugging:
Two log files are available to help debug issues contained within <splunk_home>/var/log/splunk/:

* splunkd.log - Splunk general log
* rapid7idr.log - Log for the Rapid7 Technology Add-on

Also, each page logs to the web console. Please refer to the documentation for your browser of choice for details regarding how to capture the log.

Please contact support@rapid7.com for help, including all relevant files.

## Changelog:
1.0 // Initial release.