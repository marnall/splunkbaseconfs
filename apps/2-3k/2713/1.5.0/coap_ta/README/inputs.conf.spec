[coap://name]

* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* uri = {encrypted:somekey}

# You require an activation key to use this App. Visit http://www.baboonbones.com/#activation  to obtain a non-expiring key
activation_key = <value>

#connection URI for the COAP Server
uri = <value>

#Sets the timeout for how long synchronous method calls and pings will wait until they give up and return. 
#The value 0 is equal to infinity.Defaults to 2000
ack_timeout = <value>

#GET(default) or OBSERVE
polling_type = <value>

#defaults to 30 secs
get_frequency = <value>

#confirmable (default) or non-confirmable
request_type = <value>

#default is late negotiation (block size 0)
negotiation_block_size = <value>

#message handler

message_handler_impl = <value>
message_handler_params = <value>

#additional startup settings

additional_jvm_propertys = <value>

# data output

# One of [stdout | hec ]. Defaults to stdout.
output_type = <value>

# For hec(HTTP Event Collector) output
hec_port = <value>
# if you want to overdide the default "localhost"
hec_host = <value>
# raw | event
hec_endpoint = <value>
# Defaults to 1
hec_poolsize = <value>
hec_token = <value>
# 1 | 0
hec_https = <value>
# 1 | 0
hec_batch_mode = <value>
# numeric value
hec_max_batch_size_bytes = <value>
# numeric value
hec_max_batch_size_events = <value>
#in milliseconds
hec_max_inactive_time_before_batch_flush = <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/coapmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>
