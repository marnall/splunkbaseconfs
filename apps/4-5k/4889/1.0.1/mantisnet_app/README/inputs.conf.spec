#
# inputs.conf.spec for Mantisnet App Kafka Modular Input
#
# January 2020
#
# Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Mantisnet ( www.mantisnet.com )
#

[mantisnet_kafka://name]


#----------------------------
# Kafka Connection Properties
#----------------------------

# Single value or Comma delimited list of topics ie: foo,goo,zoo

topic_name = <value>

# Single value or Comma delimited list of servers ie: somehost:9092,anotherhost:9092

bootstrap_server = <value>

# Fully qualified classname of Key Deserializer ie: org.apache.kafka.common.serialization.StringDeserializer

key_deserializer = <value>

# Fully qualified classname of Value Deserializer ie: org.apache.kafka.common.serialization.StringDeserializer

value_deserializer = <value>

# Group ID ie: mantisnet_kafka

group_id = <value>


# By default , enable.auto.commit is set to true , so offsets are committed automatically with this milliseconds frequency value

auto_commit_interval_ms = <value>

#defaults to "earliest"

auto_offset_reset = <value>

# Defaults to 60000 ms

session_timeout_ms = <value>

# the password for this username is encrypted via the app's setup page

username = <value>

# defaults to SASL_SSL

security_protocol = <value>

# defaults to SCRAM-SHA-256

sasl_mechanism = <value>

# Additional Kafka consumer configuration properties string in format 'key1=value1,key2=value2,key3=value3'

additional_consumer_properties = <value>


#-----------------------
# Custom Message Handler
#-----------------------

# customer message handler class

message_handler_impl = <value>

# Properties string in format 'sysprop1=value1,sysprop2=value2,sysprop3=value3'

message_handler_params = <value>

#----------------------
# JVM System properties
#----------------------

# JVM properties string in format 'sysprop1=value1,sysprop2=value2,sysprop3=value3'

additional_jvm_propertys = <value>

#------------
# Logging
#------------

# log level  : OFF,FATAL,ERROR,WARN,INFO,DEBUG,TRACE,ALL

log_level = <value>

#------------
# Data output
#------------

# One of [stdout | hec ]. Defaults to stdout.
output_type = <value>

# For hec(HTTP Event Collector) output
hec_port = <value>

# Defaults to 1
hec_poolsize = <value>

#your HEC token
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
