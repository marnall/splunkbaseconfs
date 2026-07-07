#!/usr/bin/env python
#
# Copyright 2013 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import random
import sys
import os
import time
import datetime
import json
import ssl
import logging
import logging.handlers
import splunklib.client as client
from splunklib.modularinput import *
from paho.mqtt import client as mqtt_client
import threading
import queue
import re

loc = __file__.split(os.sep)[-3]
logger = logging.getLogger(loc)
logger.propagate = False # Prevent the log messages from being duplicated in the log file
logger.setLevel(logging.INFO)
file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + loc + '.log', maxBytes=25000000, backupCount=5)
formatter = logging.Formatter('%(asctime)s loglevel=%(levelname)s message=%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

lgr = logging.getLogger(loc + '_setup')
lgr.propagate = False # Prevent the log messages from being duplicated in the log file
lgr.setLevel(logging.INFO)
file_handler1 = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/' + loc + '_setup.log', maxBytes=25000000, backupCount=5)
formatter1 = logging.Formatter('%(asctime)s loglevel=%(levelname)s message=%(message)s')
file_handler1.setFormatter(formatter1)
lgr.addHandler(file_handler1)


class MQTT_modinput_Script(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """
    # Define some global variables
    MASK            = "<nothing to see here>"
    APP             = __file__.split(os.sep)[-3]
    MQTT_OHW_LFAG   = None
    MQTT_MODE_FLAGS = None    
    RC              = 0
    RC_REASON       = "no work"

    def __init__(self):
        super(MQTT_modinput_Script, self).__init__()
        self.message_queue = queue.Queue() # Thread-safe message queue

    def on_connect(self,client, userdata, flags, rc, properties=None):
        self.RC = rc

    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        scheme = Scheme("MQTT Topics Ingestor")

        scheme.description = "Streams events from topics on MQTT Brokers to Splunk"
        # If you set external validation to True, without overriding validate_input,
        # the script will accept anything as valid. Generally you only need external
        # validation if there are relationships you must maintain among the
        # parameters, or you need to check that some resource is reachable or valid.
        # Otherwise, Splunk lets you specify a validation string for each argument
        # and will run validation internally using that string.
        #
        # need some relationship evalutation to help user get things correct
        scheme.use_external_validation = True
        # this is a threaded modinput so no single
        scheme.use_single_instance = False

        # setup all the fields aka arguments in splunk speak
        mqtt_broker = Argument("mqtt_broker")
        mqtt_broker.title = "MQTT Broker"
        mqtt_broker.data_type = Argument.data_type_string
        mqtt_broker.description = "The name or IP of the MQTT Broker."
        mqtt_broker.required_on_create = True
        mqtt_broker.required_on_edit = True

        mqtt_port = Argument("mqtt_port")
        mqtt_port.title = "MQTT Port"
        mqtt_port.data_type = Argument.data_type_number
        mqtt_port.description = "The TCP port of the MQTT Broker."
        mqtt_port.required_on_create = True
        mqtt_port.required_on_edit=True

        mqtt_keepalive = Argument("mqtt_keepalive")
        mqtt_keepalive.title = "MQTT Keepalive"
        mqtt_keepalive.data_type = Argument.data_type_number
        mqtt_keepalive.description = "The keepalive value."
        mqtt_keepalive.required_on_create = True
        mqtt_keepalive.required_on_edit=True

        # add these to the scheme        
        scheme.add_argument(mqtt_keepalive)
        scheme.add_argument(mqtt_broker)
        scheme.add_argument(mqtt_port)


        #deal with username and password
        username_arg = Argument(name="username",title="User name",description="The username credential on MQTT Broker.",data_type=Argument.data_type_string,required_on_create=True,required_on_edit=True)
        scheme.add_argument(username_arg)
		
        password_arg = Argument(name="password",title="Password",description="The password credential on MQTT Broker.",data_type=Argument.data_type_string,	required_on_create=True,required_on_edit=True)
        scheme.add_argument(password_arg)

        # topic/s - i guess iot'ers know what to do here
        topic = Argument("topic")
        topic.title = "Topic"
        topic.data_type = Argument.data_type_string
        topic.description = "The name of Topic or list of Topics. (Comma seperated)"
        topic.required_on_create = True
        topic.required_on_edit=True
        scheme.add_argument(topic)
       
        # client name - used for ACL's, change for multiple connections etc
        client_name = Argument("client_name")
        client_name.title = "Client Name"
        client_name.data_type = Argument.data_type_string
        client_name.description = "The client name Splunk uses to connect to MQTT Broker"
        client_name.required_on_create = True
        client_name.required_on_edit=True
        scheme.add_argument(client_name)

        # use one way auth ssl - ca cert only
        use_ssl = Argument("use_ssl")
        use_ssl.title = "1-way SSL/TLS Auth"
        use_ssl.data_type = Argument.data_type_boolean
        use_ssl.description = "Use One-way authentication TLS/SSL secure communication."
        use_ssl.required_on_create = False
        scheme.add_argument(use_ssl)

        # use two way auth ssl - ca cert + cert + key - also includes just using 2 fields cert and key
        # most systems have ca_certs and will resolve at system level ie /etc/ssl/certs etc
        use_2_ssl = Argument("use_2_ssl")
        use_2_ssl.title = "2-way SSL/TLS Auth"
        use_2_ssl.data_type = Argument.data_type_boolean
        use_2_ssl.description = "Use One-way authentication TLS/SSL secure communication."
        use_2_ssl.required_on_create = False
        scheme.add_argument(use_2_ssl)
        

        # ca_cert - for serverless cloud providers - 1 way auth
        ca_cert = Argument("ca_cert")
        ca_cert.title = "CA Certificate"
        ca_cert.data_type = Argument.data_type_string
        ca_cert.description = "Full path and filename to the CA Certificate."
        ca_cert.required_on_create = False
        ca_cert.required_on_edit = False
        scheme.add_argument(ca_cert)

        # cert - for secure comms
        cert = Argument("cert")
        cert.title = "Certificate file"
        cert.data_type = Argument.data_type_string
        cert.description = "Full path and filename to the Certificate."
        cert.required_on_create = False
        cert.required_on_edit = False
        scheme.add_argument(cert)

        # cert_keyfile - for secure comms
        cert_key = Argument("cert_key")
        cert_key.title = "Certificate Key file"
        cert_key.data_type = Argument.data_type_string
        cert_key.description = "Full path and filename to the Certificate keyfile."
        cert_key.required_on_create = False
        cert_key.required_on_edit = False
        scheme.add_argument(cert_key)
        logger.info("Finished configuring scheme")
        return scheme


    def validate_input(self, validation_definition):

        kept_cred = self.get_password(validation_definition.metadata["session_key"],validation_definition.parameters["username"])
        # these are debug and not fit for distribution
        #lgr.info("Parameters: %s" % (str(validation_definition.parameters)))
        #lgr.info("Metadata: %s" % (str(validation_definition.metadata)))


        # regex for client
        pattern = re.compile('[^A-Za-z0-9-_ ]+') 
        # do validations
        try:
            checkport = int(validation_definition.parameters["mqtt_port"])
        except Exception as e:
            raise Exception("MQTT Port - must be numeric - %s" % str(e))

        if checkport <= 1024:
            raise ValueError(f"MQTT Port - thats a system range port; try 1883 / 8883")
        elif checkport >= 65536:
            raise ValueError(f"MQTT Port - thats a system range port; try 1883 / 8883")

        try:
            checkkeepalive = int(validation_definition.parameters["mqtt_keepalive"])
        except Exception as e:
            raise Exception("MQTT Keepalive - must be numeric - %s" % str(e))

        if checkport <= 0:
            raise ValueError(f"MQTT Keepalive - thats invalid numbers")
        elif checkport >= 65536:
            raise ValueError(f"MQTT Keepalive max issue - thats above the maximum value 65535")

        client_name = pattern.search(validation_definition.parameters["client_name"])
        if client_name:
            raise ValueError(f"Client name should not contain special characters, - and _ allowed")

        #try to connect to the broker with provided det's
        lgr.info("Validations passed")
        """Validate the configuration for the input, by attempting to connect to the broker."""
        # Extract parameters from the validation definition
        params = validation_definition.parameters
        mqtt_broker = params["mqtt_broker"]
        mqtt_port = int(params["mqtt_port"])
        mqtt_keepalive = int(params["mqtt_keepalive"])
        topics = params["topic"]
        client_name = params["client_name"]
        use_ssl = params.get("use_ssl")
        use_2_ssl = params.get("use_2_ssl")
        ca_cert = params.get("ca_cert")
        cert = params.get("cert")
        cert_key = params.get("cert_key")
        username = params.get("username", None)
        password = params.get("password", None)
        if password != self.MASK:
            kept_cred = password


        #some more checks for ssl - i cld bool this but it lives like this
        if (use_ssl=='1') and (use_2_ssl=='1'):
            raise ValueError(f"Cannot do both Auth methods of SSL - Choose only 1")

        if use_2_ssl=='1':
            if cert is None or cert_key is None:
                raise ValueError(f"If using SSL/TLS 2 way authentication use all 3 field together, or 2 for system CA Cert - See Documentation")

        if use_ssl=='1':
            if ca_cert is None:
                raise ValueError(f"If using SSL/TLS 1 way authentication CA Certificate field needs certificate - See Documentation")

        # loaded saved values
        lgr.info("MQTT broker test to %s for inputname: %s" % (mqtt_broker, validation_definition.metadata["name"]))
        lgr.info("use_ssl is: %s, use_2_ssl is: %s" % (use_ssl,use_2_ssl))
        if kept_cred:
            # Create MQTT client - use the client name provided - ACL's etc on cloud - use version 4 aka v3.1.1
            mqtt_protocol = mqtt_client.MQTTv311
            client_id = client_name
            #test_client = mqtt_client.Client(client_id=client_id)
            test_client = mqtt_client.Client(callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2, client_id=client_id,protocol=mqtt_protocol,clean_session=True)
            lgr.info("SETUP MQTT Client is %s" % (client_id))
            # SSL / TLS test
            if use_ssl=='1':
                if ca_cert is not None:
                    test_client.tls_set(ca_certs=ca_cert,tls_version=ssl.PROTOCOL_TLSv1_2)
                    lgr.info("SSL is via ca cert, 1 Way Auth")
            
            if use_2_ssl=='1':
                if ca_cert is None and cert is not None and cert_key is not None:
                    test_client.tls_set(certfile=cert, keyfile=cert_key, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
                    lgr.info("SSL is via certificate and key - using system ca root, 2 Way Auth")
                else:
                    test_client.tls_set(ca_certs=ca_cert, certfile=cert, keyfile=cert_key, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
                    lgr.info("SSL is via a defined ca certificate, certificate and key, 2 Way Auth")
       
            # websockets - not implemented

            # Set MQTT broker credentials if provided - required
            if username and kept_cred:
                test_client.username_pw_set(username, kept_cred)
            # used a global to handle this, callbacks are painful with splunklib
            test_client.on_connect = self.on_connect
            # Test connection to the broker
            try:
                #test_client.on_connect = self.on_connect
                test_client.connect(mqtt_broker, mqtt_port, keepalive=mqtt_keepalive)
                test_client.loop_start()
                test_client.loop_stop()
                test_client.disconnect()
                rc=self.RC
                
            except Exception as e:
                # If there is an error during connect log the exception
                # and raise an exception so Splunk knows the configuration is invalid
                raise ValueError(f"Failed to connect to MQTT Broker at {mqtt_broker}:{mqtt_port} reason: {str(e)}.")

            if rc != 0:
                raise ValueError(f"Failed to connect to MQTT Broker at {mqtt_broker}:{mqtt_port} reason: {rc}")
                lgr.info("Connection to the broker %s failed due to %s " %(mqtt_broker, rc))
                self.RC = 0
            else:
                self.RC = 0
                lgr.info("Connection to the broker %s success with return code %s" %(mqtt_broker, rc))
                

    def encrypt_password(self, username, password, session_key):
        app_name = self.APP
        args = {'token':session_key, 'app':app_name}
        service = client.connect(**args)

        try:
            # If the credential already exists, delete it.
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
                    break

            # Create the credential.
            service.storage_passwords.create(password, username)

        except Exception as e:
            raise Exception("An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))


    def mask_input(self, session_key, username, mqtt_broker, mqtt_port, mqtt_keepalive, topic, client_name):
        try:
            app_name = self.APP
            args = {'token':session_key, 'app':app_name}
            service = client.connect(**args)
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))
			
            kwargs = {
                "username": username,
                "password": self.MASK,
                "mqtt_broker": mqtt_broker,
                "mqtt_port": mqtt_port,
                "mqtt_keepalive": mqtt_keepalive,
                "topic": topic,
                "client_name": client_name
            }
            item.update(**kwargs).refresh()
		
        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_password(self, session_key, username):
        app_name = self.APP
        args = {'token':session_key,'app':app_name}
        service = client.connect(**args)

        # Retrieve the password from the storage/passwords endpoint	
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password

    #paho callbacks

    # Define on_message callback
    # decided not to use an on_connect callback as threading and various issues etc, use for setup only
    def on_message(self, client, userdata, message):
        self.message_queue.put(message) # Queue the received message

    # startup each streamed input etc
    def start_mqtt_client(self, broker, port, keep_alive, topics, client_conn_name, using_ssl_1way, using_ssl_2way, ca_cert_file,cert_file,cert_key_file):
        # not building it in for now - iam just going to hard set protocol and cleanstart false (to not use fishbucket)
        mqtt_protocol = mqtt_client.MQTTv311

        client_id = client_conn_name
        client = mqtt_client.Client(callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2, client_id=client_id,protocol=mqtt_protocol,clean_session=False)
        client.on_message = self.on_message
        client.username_pw_set(self.MQTT_OHW_LFAG, self.MQTT_MODE_FLAGS)
        try:
            if using_ssl_1way=='1' and ca_cert_file is not None:
                client.tls_set(ca_certs=ca_cert_file)

            if using_ssl_2way=='1' and cert_file is not None and cert_key_file is not None and ca_cert_file is None:
                client.tls_set(certfile=cert_file, keyfile=cert_key_file, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
            elif using_ssl_2way=='1' and cert_file is not None and cert_key_file is not None and ca_cert_file is not None:
                client.tls_set(ca_certs=ca_cert_file, certfile=cert_file, keyfile=cert_key_file, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        except Exception as e:
            raise logger.error("Error configuring SSL on client: %s was %s" % (client_id,str(e)))
        try:
            client.connect(broker, port, keepalive=keep_alive)
        except Exception as e:
            raise logger.error("Error conecting to broker: %s was %s for client %s" % (broker,str(e),client_id))

        logger.info("Successfully connected to broker: %s with pid:%s for client %s" % (broker,os.getpid(),client_id))
        values = topics.split(",")
        for topic in values:
            client.subscribe(topic, qos=1)
            # client.subscribe('/test')

        client.loop_start() # Start network loop in separate thread


    def stream_events(self, inputs, event_writer):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param event_writer: an EventWriter object
        """

        logger.info("Successfully started %s with pid %s" % (self.APP,os.getpid()))
        self.input_name, self.input_items = inputs.inputs.popitem()
        session_key = self._input_definition.metadata["session_key"]
        params = self.input_items
        username = self.input_items["username"]
        password   = self.input_items['password']
        mqtt_broker = self.input_items['mqtt_broker']
        mqtt_port = int(self.input_items['mqtt_port'])
        mqtt_keepalive = int(self.input_items['mqtt_keepalive'])
        topics = self.input_items['topic']
        client_conn_name = self.input_items['client_name']
        using_ssl_1way = params.get('use_ssl', False)
        using_ssl_2way = params.get('use_2_ssl', False)
        ca_cert_file = params.get('ca_cert', None)
        cert_file = params.get('cert',None)
        cert_key_file = params.get('cert_key',None)
        self.MQTT_OHW_LFAG = username

        # these are debug
        #logger.info("variable to check %s" % (str(params)))
        #logger.info("session_key %s" % (str(session_key)))

        try:
            # If the password is not masked, mask it.
            if password != self.MASK:
                try:
                    self.encrypt_password(username, password, session_key)
                    self.MQTT_MODE_FLAGS = self.get_password(session_key, username)
                    self.mask_input(session_key, username, mqtt_broker, mqtt_port, mqtt_keepalive, topics, client_conn_name)
                except Exception as e:
                    event_writer.log("ERROR", "Error: %s" % str(e))

         
            self.MQTT_MODE_FLAGS = self.get_password(session_key, username)
        except Exception as e:
            event_writer.log("ERROR", "Error: %s" % str(e))

        # threading
        mqtt_thread = threading.Thread(target=self.start_mqtt_client, args=(mqtt_broker, mqtt_port, mqtt_keepalive, topics, client_conn_name, using_ssl_1way,using_ssl_2way,ca_cert_file,cert_file,cert_key_file))
        mqtt_thread.start() # Start MQTT client on a separate thread

        # do json as much as possible - inject splunk metadata and mqtt fields
        try:
            while True:
                message = self.message_queue.get(block=True) # Block until message is available
                nowtime = datetime.datetime.now()

                try:
            # Decode the message payload from JSON format
                    json_data = json.loads(message.payload.decode())
                    json_data['mqtt_broker'] = mqtt_broker
                    json_data['mqtt_port'] = mqtt_port
                    json_data['topic'] = message.topic
                    json_data['time'] = str(nowtime)
                    working_data = json.dumps(json_data)

            # Handle the parsed JSON data (add it to the queue, etc.)
            # other operations with data...

                except json.JSONDecodeError as e:
                    working_data = f"time={nowtime} message={message.payload.decode()} topic={message.topic} mqtt_broker={mqtt_broker} mqtt_port={mqtt_port}"
                # for debug, not a good idea for prd
                #event_writer.log("INFO", "A message has been received")
                event = Event()
                event.stanza = self.input_name
                event.data = working_data
                event_writer.write_event(event)
                self.message_queue.task_done()
        except Exception as e:
            event_writer.log("ERROR", "Error: %s" % str(e))
        finally:
            mqtt_thread.join()


# kickoff
if __name__ == "__main__":
    sys.exit(MQTT_modinput_Script().run(sys.argv))
