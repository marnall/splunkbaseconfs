[kafka://name]

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

# Group ID ie: my_kafka_group

group_id = <value>

# By default , enable.auto.commit is set to true , so offsets are committed automatically with this milliseconds frequency value

auto_commit_interval_ms = <value>

#defaults to "earliest"

auto_offset_reset = <value>

# Defaults to 60000 ms

session_timeout_ms = <value>

# credentials

kafka_username = <value>
# ensure that you have also setup the password for this username on the "Setup Credentials" page in the App

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

