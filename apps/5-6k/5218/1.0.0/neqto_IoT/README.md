# neqto: IoT Data for Splunk

Using the [neqto.js Snippet for Splunk](https://docs.neqto.com/docs/en/snippets/splunk), visualize the quantity of data incoming from a neqto: device.

## neqto: Cloud and device preparation

The neqto: IoT Data for Splunk app requires the use of `sourcetype` for differentiating neqto: devices.

```
var payload = {
    "index": "neqto",
    "event": {
      "sensor_reading" : "123"
    },
    "sourcetype": "neqtoDevice_1"
}:
```

For multiple devices, adjust the `sourcetype` for each device. This can be easily accomplished by including an Environment Variable for the `sourcetype` value in a script. See below for reference. For more information regarding Environment Variables in scripts see [here](https://docs.neqto.com/docs/en/console/scripts#environment-variable).

```
    "sourcetype": ENV['SOURCE_TYPE']
```

Then set an Environment Variable key for each device Node with the same key as the `sourcetype` set in the script (i.e. SOURCE_TYPE). For each node's Environment Variable value, input the desired unique device ID or sourcetype. See below for reference. For more information regarding Environment Variables in Nodes, see [here](https://docs.neqto.com/docs/en/console/device-management#nodes).

```
Key: SOURCE_TYPE
Value: neqtoDevice_3
```

## Using the neqto: IoT Data for Splunk App

> Prepare the event index `neqto` before using the neqto: IoT Data for Splunk App with the neqto.js Snippet for Splunk. For more information regarding index creation, see [here](https://docs.splunk.com/Documentation/Splunk/8.0.5/Indexer/Setupmultipleindexes#Create_events_indexes_2)
>
> Select "Allowed Indexes" for the desired HTTP Event Collector Token to include the `neqto` event index. For more information regarding the use of an HTTP Event Collector Tokens, see [here](https://docs.splunk.com/Documentation/Splunk/8.0.5/Data/UsetheHTTPEventCollector).

After the neqto: devices have been prepared using the neqto: Snippet for Splunk, begin device operation. Using the neqto app's default `IoT_Data` tab on the Splunk Instance, visualize the quantity of data coming from each device as an individual line on the graph. The graph will visualize the incoming data quantity in real-time.
