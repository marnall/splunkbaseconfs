import import_declare_test

import json
import logging
import sys
import time
import os
import re

import threading
from solnlib import conf_manager, log
from splunklib import modularinput as smi
import splunklib.client as client
from webserver import WebServer

ADDON_NAME = "splunk_connect_for_zoom"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_cipher_suite(session_key: str):
    cfm = conf_manager.ConfManager(
        session_key,
        app='system',
        owner='nobody',
    )
    server_conf_file = cfm.get_conf("server")
    ssl_config_stanza = server_conf_file.get("sslConfig")
    if ssl_config_stanza:
        cipher_suite = ssl_config_stanza.get("cipherSuite")
        if not cipher_suite:
            return None
        else:
            return cipher_suite


def get_secret_key(session_key: str, secret_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-splunk_connect_for_zoom_secret",
    )
    account_conf_file = cfm.get_conf("splunk_connect_for_zoom_secret")
    return account_conf_file.get(secret_name).get("secret_token")

class Input(smi.Script, smi.EventWriter):
    def __init__(self):
        smi.Script.__init__(self)
        smi.EventWriter.__init__(self, output = sys.stdout, error = sys.stderr)

    def get_scheme(self):
        scheme = smi.Scheme("zoom_input")
        scheme.description = "Zoom input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "secret", title="Secret to use", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "port", title="The port to run the input on", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "cert_file", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "key_file", required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                "dump_requests", required_on_create=True
            )
        )
        return scheme

    def validate_input(self, _: smi.ValidationDefinition):
        return

    def _validate_input(self, input_item):
        key_file=input_item.get("key_file","/opt/splunk/etc/auth/splunkweb/privkey.pem")
        if not os.path.exists(key_file):
            raise Exception("Key file does not exist: {}".format(key_file))
        
        cert_file=input_item.get("cert_file","/opt/splunk/etc/auth/splunkweb/cert.pem")
        if not os.path.exists(cert_file):
            raise Exception("Certificate file does not exist: {}".format(key_file))

    def stream_events(self, inputs: smi.InputDefinition, _: smi.EventWriter):
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = logger_for_input(normalized_input_name)
            try:
                self._validate_input(input_item)
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name=f"{ADDON_NAME}_settings",
                )
                logger.setLevel(log_level)
                log.modular_input_start(logger, normalized_input_name)
                secret_token = get_secret_key(session_key, input_item.get("secret"))

                try:
                    cipher_suite = get_cipher_suite(session_key)
                    logger.info("Cipher suite: {}".format(cipher_suite))
                except Exception:
                    cipher_suite = None

                def output_results(payload, clientip):
                    self.write_event(smi.Event(
                            data=json.dumps(payload),
                            time="%.3f" % time.time(),
                            index=input_item.get("index"),
                            host=clientip,
                            source=input_item.get("host"),
                            sourcetype="zoom:webhook",
                            done=True,
                            unbroken=True
                        )
                    )
                port=int(input_item.get("port", "4443"))
                key_file=input_item.get("key_file","/opt/splunk/etc/auth/splunkweb/privkey.pem")
                cert_file=input_item.get("cert_file","/opt/splunk/etc/auth/splunkweb/cert.pem")
                disable_verification=input_item.get("disable_verification", "0") == "1"
                disable_redaction=input_item.get("disable_redaction", "0") == "1"
                dump_requests=input_item.get("dump_requests", "0") == "1"
                webserver = WebServer(
                    output_results=output_results, 
                    port=port,
                    key_file=key_file,
                    cert_file=cert_file,
                    disable_verification=disable_verification,
                    disable_redaction=disable_redaction,
                    dump_requests=dump_requests,
                    zoom_secret=secret_token,
                    logger=logger,
                    cipher_suite=cipher_suite,
                )
                logger.info("Starting web server for {} on port {}".format(normalized_input_name, port))
                threading.Thread(target=webserver.start_serving).start()
            except Exception as e:
                log.log_exception(logger, e, msg_before="Exception raised while ingesting data for {}: ".format(normalized_input_name))


if __name__ == "__main__":
    input = Input()
    exit_code = input.run(sys.argv)
    sys.exit(exit_code)
