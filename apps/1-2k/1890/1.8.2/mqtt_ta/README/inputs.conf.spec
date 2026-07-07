[mqtt://name]

#connection settings

topic_name = <value>
broker_host = <value>
broker_port = <value>
use_ssl = <value>
use_websockets = <value>
custom_url = <value>

username = <value>
# ensure that you have also setup the password for this username on the "Setup Credentials" page in the App
client_id = <value>

qos = <value>
reliable_delivery_dir = <value>
clean_session = <value>
connection_timeout = <value>
keepalive_interval = <value>

# message handler

message_handler_impl = <value>
message_handler_params = <value>

# additional startup settings

additional_jvm_propertys = <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/mqttmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>
