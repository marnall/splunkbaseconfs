[amqp://name]

# name of the queue

queue_name = <value>

#fields for the AMQP URI

hostname = <value>
port = <value>
username = <value>
# ensure that you have also setup the password for this username on the "Setup Credentials" page in the App
virtual_host = <value>
use_ssl = <value>

#common settings for polling queues and topics

routing_key_pattern = <value>
exchange_name = <value>
ack_messages = <value>
basic_qos_limit = <value>

#message handler

message_handler_impl = <value>
message_handler_params = <value>

#optional parts of the message to index

index_message_envelope = <value>
index_message_propertys = <value>

#additional startup settings

additional_jvm_propertys = <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/amqpmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>
		
