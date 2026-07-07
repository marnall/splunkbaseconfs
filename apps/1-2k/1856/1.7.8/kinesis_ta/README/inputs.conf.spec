[kinesis://name]

#connection settings

app_name = <value>
stream_name = <value>
kinesis_endpoint = <value>

#LATEST or TRIM_HORIZON
initial_stream_position = <value>

aws_access_key_id = <value>
# ensure that you have also setup the secret key for this aws_access_key_id on the "Setup Credentials" page in the App

#message reader settings

backoff_time_millis = <value>
num_retries = <value>
checkpoint_interval_millis = <value>

# message handler

message_handler_impl = <value>
message_handler_params = <value>

# additional startup settings

additional_jvm_propertys = <value>


* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/kinesismodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>
