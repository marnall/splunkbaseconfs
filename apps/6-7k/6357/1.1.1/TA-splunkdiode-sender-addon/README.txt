This Add-On works together with the Diode Receiver Add-on Splunk.

It is designed to send data between Splunk servers that can pass through a Data Diode, while preserving the Splunk metadata.

The sender will encapsulate Splunk metadata like sourcetype, source, host, _time into the _raw message which can then be forwarded over UDP or TCP. The receiver will unpack this and populate the metadata fields as well and restore the _raw to its original state.