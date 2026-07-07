#!/usr/bin/env python
import sys
import json
import os
import logging
import six
from logging.handlers import RotatingFileHandler

# Import confluent_kafka lib

python_version = sys.version_info
if python_version.major == 3 and python_version.minor >= 9:
    current_confluent_kafka = os.path.join(os.path.dirname(__file__), "..", "lib", "confluent_kafka_python39")
else:
    current_confluent_kafka = os.path.join(os.path.dirname(__file__), "..", "lib", "confluent_kafka_python374")
sys.path.append(current_confluent_kafka)
from confluent_kafka import Consumer, KafkaException
# Import Splunk Lib - http://dev.splunk.com/python
current_splunklib = os.path.join(os.path.dirname(__file__), "..", "lib", "splunklib_2.1.0")
sys.path.append(current_splunklib)
from splunklib.modularinput import Script, Scheme, Argument, Event

# Define debug logfile
if "SPLUNK_HOME" in os.environ:
    logfile = os.path.join(str(os.environ['SPLUNK_HOME']),"var/log/splunk/splunk_citrix_analytics_add_on_debug_connection.log")
else:
    logfile = os.path.join(str(os.path.dirname(__file__)),"splunk_citrix_analytics_add_on_debug_connection.log")

# Define debug logger, maximum 5 files 25 MB each
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(logfile, mode='a', maxBytes=25*1024*1024, backupCount=5, encoding=None, delay=0)
handler.setFormatter(logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s'))
logger.addHandler(handler)

class CasSiemConsumer(Script):
    # Define some global variables
    MASK = "<nothing to see here>"
    USERNAME = None
    CLEAR_PASSWORD = None
    def get_scheme(self):
        scheme = Scheme("Citrix Analytics Add-on")
        scheme.description = "Enable data inputs for Citrix Analytics"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        cas_siem_host = Argument("cas_siem_host")
        cas_siem_host.title = "Host(s)"
        cas_siem_host.data_type = Argument.data_type_string
        cas_siem_host.description = "Combination of three host name ports (comma separated) provided in the Citrix Analytics configuration file."
        cas_siem_host.required_on_create = True
        scheme.add_argument(cas_siem_host)

        cas_siem_user_name = Argument("cas_siem_user_name")
        cas_siem_user_name.title = "User Name"
        cas_siem_user_name.data_type = Argument.data_type_string
        cas_siem_user_name.description = "User name provided during Citrix Analytics configuration."
        cas_siem_user_name.required_on_create = True
        cas_siem_user_name.required_on_edit = True
        scheme.add_argument(cas_siem_user_name)

        cas_siem_user_password = Argument("cas_siem_user_password")
        cas_siem_user_password.title = "Password"
        cas_siem_user_password.data_type = Argument.data_type_string
        cas_siem_user_password.description = "Password provided during Citrix Analytics configuration."
        cas_siem_user_password.required_on_create = True
        cas_siem_user_password.required_on_edit = True
        scheme.add_argument(cas_siem_user_password)

        cas_siem_topic = Argument("cas_siem_topic")
        cas_siem_topic.title = "Topic name"
        cas_siem_topic.data_type = Argument.data_type_string
        cas_siem_topic.description = "Topic name provided in the Citrix Analytics configuration file."
        cas_siem_topic.required_on_create = True
        cas_siem_topic.required_on_edit = True
        scheme.add_argument(cas_siem_topic)

        cas_siem_group_id = Argument("cas_siem_group_id")
        cas_siem_group_id.title = "Group name"
        cas_siem_group_id.data_type = Argument.data_type_string
        cas_siem_group_id.description = "Group name provided in the Citrix Analytics configuration file."
        cas_siem_group_id.required_on_create = True
        cas_siem_group_id.required_on_edit = True
        scheme.add_argument(cas_siem_group_id)

        cas_siem_debug = Argument("cas_siem_debug")
        cas_siem_debug.title = "Debug mode"
        cas_siem_debug.data_type = Argument.data_type_boolean
        cas_siem_debug.description = "Enable/Disable debug mode for modular input"
        cas_siem_debug.required_on_create = True
        cas_siem_debug.required_on_edit = True
        scheme.add_argument(cas_siem_debug)

        return scheme

    def encrypt_password(self, username, password):
        service = self.service

        try:
            # If the credential already exists, delte it.
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
                    break

            # Create the credential.
            service.storage_passwords.create(password, username)

        except Exception as e:
            raise Exception("An error occurred updating credentials. Please ensure your user account has "
                            "admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

    def mask_password(self, username, cas_siem_topic, cas_siem_group_id, cas_siem_debug):
        try:
            service = self.service
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {
                "cas_siem_user_name": username,
                "cas_siem_user_password": self.MASK,
                "cas_siem_topic": cas_siem_topic,
                "cas_siem_group_id": cas_siem_group_id,
                "cas_siem_debug": cas_siem_debug
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_password(self, username):
        service = self.service
        # Retrieve the password from the storage/passwords endpoint
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password

    def debug_logging(self, ew, cas_siem_debug, log_level, log_message):
        try:
            if cas_siem_debug:
                ew.log(log_level, log_message)
        except Exception as e:
            raise Exception("Error creating debug log: %s" % str(e))

    def ca_cert_region_detection(self, cas_siem_host):
        if cas_siem_host.startswith("casnb-aps"):
            ca_cert_region = "APS"
        elif cas_siem_host.startswith("casnb-eu"):
            ca_cert_region = "EU"
        else:
            ca_cert_region = "US"
        return(ca_cert_region)

    def kafka_consumer(self, cas_siem_debug, conf, logger):
        if cas_siem_debug:
            logger.setLevel(logging.DEBUG)
            conf['debug'] = 'all'
            c = Consumer(conf, logger=logger)
        else:
            c = Consumer(conf)
        return c

    def kafka_message_debug_details(self, cas_siem_debug, msg,kafka_message):
        if cas_siem_debug:
            kafka_details = {"partition": msg.partition(), "offset": msg.offset(), "enqueued_timestamp": msg.timestamp()[1]}
            kafka_message.update({"cas_consumer_debug_details": kafka_details})
        return kafka_message

    def kafka_event_processing(self, c, ew, cas_siem_debug, event_counter, partitions_count, input_name):
        no_message_count = 0
        none_message_count = 0
        while True:
            msg = c.poll(timeout=1.0)
            if msg is None:
                none_message_count += 1
                if none_message_count >= 20:
                    self.debug_logging(ew, cas_siem_debug, "INFO", "No (more) data available. Stop script")
                    break
                continue
            if msg.error() and msg.value() == "Broker: No more messages":
                no_message_count += 1
                # Log debug output
                self.debug_logging(ew, cas_siem_debug, "INFO",
                                   str(msg.value()) + " available on partition " + str(msg.partition()))
                if no_message_count == partitions_count:
                    # Log debug output
                    self.debug_logging(ew, cas_siem_debug, "INFO", str(event_counter) + " events received")
                    self.debug_logging(ew, cas_siem_debug, "INFO",
                                       str(msg.value()) + " available on all partitions. Stop script")
                    return 0
            elif msg.error():
                raise KafkaException(msg.error())
            elif msg.value() is None:
                continue
            else:
                # Proper message
                kafka_message = msg.value()
                try:
                    # Check IF valid JSON and load into dict for further processing
                    kafka_message = json.loads(kafka_message)
                    # Add Kafka offset + partition if debug mode enabled
                    kafka_message = self.kafka_message_debug_details(cas_siem_debug, msg, kafka_message)
                    kafka_message = json.dumps(kafka_message, sort_keys=True)
                    # Build event object and send to Splunk
                    splunk_event = Event()
                    splunk_event.stanza = input_name
                    splunk_event.data = kafka_message
                    # Send event to Splunk
                    ew.write_event(splunk_event)
                    event_counter += 1
                    # Log debug output (event details send to Splunk)
                    self.debug_logging(ew, cas_siem_debug, "INFO", "SEND EVENT" + str(kafka_message))
                except Exception as error:
                    ew.log("WARN", "Invalid message received. Partition: " + str(msg.partition()) +
                           " Offset: " + str(msg.offset()) + " Error message: " + str(error))
    # pylint: disable=too-many-arguments
    def stream_events(self, inputs, ew):
        for input_name, input_item in six.iteritems(inputs.inputs):
            self.input_name = input_name
            self.input_items = input_item
            # read input variables
            cas_siem_host = str(input_item["cas_siem_host"])
            cas_siem_user_name = str(input_item["cas_siem_user_name"])
            self.USERNAME = cas_siem_user_name
            cas_siem_user_password = str(input_item["cas_siem_user_password"])
            cas_siem_topic = str(input_item["cas_siem_topic"])
            cas_siem_group_id = str(input_item["cas_siem_group_id"])
            cas_siem_debug = int(input_item["cas_siem_debug"])
            topics = [cas_siem_topic]
            script_path = os.path.dirname(__file__)
            ca_location_cert_name = "CARoot.pem"
            ca_cert_region = self.ca_cert_region_detection(cas_siem_host)
            ca_location = os.path.join(script_path, "certificates", ca_cert_region, ca_location_cert_name)
            event_counter = 0

            try:
                # If the password is not masked, mask it.
                if cas_siem_user_password != self.MASK:
                    self.encrypt_password(cas_siem_user_name, cas_siem_user_password)
                    self.mask_password(cas_siem_user_name, cas_siem_topic, cas_siem_group_id, cas_siem_debug)
                self.CLEAR_PASSWORD = self.get_password(cas_siem_user_name)
            except Exception as e:
                ew.log("ERROR", "Error: %s" % str(e))

            # Consumer configuration
            # See https://github.com/edenhill/librdkafka/blob/master/CONFIGURATION.md
            conf = {'bootstrap.servers': cas_siem_host,
                    'client.id': cas_siem_topic,
                    'group.id': cas_siem_group_id,
                    'session.timeout.ms': 60000,
                    'auto.offset.reset': 'earliest',
                    'security.protocol': 'SASL_SSL',
                    'sasl.mechanisms': 'SCRAM-SHA-256',
                    'sasl.username': cas_siem_user_name,
                    'sasl.password': self.CLEAR_PASSWORD,
                    'ssl.ca.location': ca_location
            }
            # See https://stackoverflow.com/questions/76678569/confluent-kafka-python-certificate-verification
            if python_version.major == 3 and python_version.minor >= 9:
                conf['ssl.endpoint.identification.algorithm'] = 'none'

            try:
                # Start Log debug output
                self.debug_logging(ew, cas_siem_debug, "INFO", "Start script")
                # Create Consumer instance
                c = self.kafka_consumer(cas_siem_debug,conf,logger)

                # Log debug output
                self.debug_logging(ew, cas_siem_debug, "INFO", "Connected to host(s)")

                # check if topic is available and exit script if not
                topic_check = c.list_topics(cas_siem_topic, timeout=5)

                if "Broker: Unknown topic or partition" in str(topic_check.topics):
                    ew.log("ERROR", "Unknown topic or partition. Please check config and fix settings")
                    c.close()
                    return 0

                # Check number of partitions for used topic
                partitions = topic_check.topics[cas_siem_topic].partitions
                partitions_count = len(partitions.keys())

                # Subscribe to topics
                c.subscribe(topics)
                # Log debug output
                self.debug_logging(ew, cas_siem_debug, "INFO", "Subscribed to topic")
                # Log debug output
                self.debug_logging(ew, cas_siem_debug, "INFO", "Start consuming events")
                # Read messages from Kafka and send to Splunk
                self.kafka_event_processing(c, ew, cas_siem_debug, event_counter, partitions_count, input_name)
            except Exception as error:
                ew.log("ERROR", 'INPUT NAME ' + input_name + ' Script ended with error: ' + str(error))
            except KeyboardInterrupt:
                ew.log("INFO", "Aborted by Splunk")
            finally:
                # Log debug output
                self.debug_logging(ew, cas_siem_debug, "INFO", "Script finished")
                c.close()
    # pylint: enable=too-many-arguments

if __name__ == "__main__":
    sys.exit(CasSiemConsumer().run(sys.argv))
