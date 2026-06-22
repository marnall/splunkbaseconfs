# Spec for the custom modular input: layer7
[layer7]
* The Layer7 modular input collects API events and sends them to Splunk.
* This stanza defines the external scheme "layer7" provided by bin/layer7_modinput.py

api_base =
* Base URL, e.g., https://api.layer7.example
* required = true

api_key =
* API key or token; consider storing securely via passwords endpoint
* required = true

interval =
* Polling interval in seconds
* required = false
* default = 300

index =
* Target index for events
* required = false
