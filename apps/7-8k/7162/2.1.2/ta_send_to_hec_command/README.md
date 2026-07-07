> :warning: **This Splunk Solution is still in Alpha**. Should you encounter any issues or bug, we encourage you to fill out [this form](https://docs.google.com/forms/d/1OJnpZ2vORox3HcTXuOH82kKuKfzZ0MXzpGq59LWKxy4/edit?ts=657144f1).

# sendtohec Custom Search Command

A custom SPL Search Command that allows you to forward results of a Splunk Search to a Second Splunk indexer via HTTP Event Collector (HEC). A GUI is provided to configure the Search Command.

### Syntax

    <SPL Search> | sendtohec traget=<Target Name>

where *target* is the configured Splunk indexer that serves as the destination.


## Usage

### Prerequisites
- One Splunk instance acting as the sender
- Another Splunk instance acting as the receiver, from now on referred to as "target"

### Setup
1. On the sending Splunk Instance, install the *sendtohec Custom Search Command* app.
2. Set up a HTTP Event Collector on the target instance. Instructions can be found [here](https://docs.splunk.com/Documentation/Splunk/latest/Data/UsetheHTTPEventCollector) for Splunk Enterprise, and [here](https://docs.splunk.com/Documentation/SplunkCloud/latest/Data/UsetheHTTPEventCollector) for Splunk Cloud.
3. On the sending Splunk Instance, open the *sendtohec Custom Search Command* app. You will be redirected to the *Configuration* page, where you can configure one or multiple targets.
![image](./img/configuration_page.png)
4. Click on the **Add** button to configure a new target.
![image](./img/configure_target.png) Specify a name for the target. This name will be invoked with the Search Command. For the *Receiving Instance Base URl* field, provide the full URL of the target instance including preceeding *http* or *https*, but without port. You can specify a port in the next field, if this is omitted, the default value of 8088 is used. Next provide the HEC token. If you with to preserve some internal fields when sending events, you can specify them in the *Fields to Include* field.
5. Change to the *Search* page in the app, or to the default *Search & Reporting* app, and use the configured target according to the syntax described above. ![image](./img/example.png)
