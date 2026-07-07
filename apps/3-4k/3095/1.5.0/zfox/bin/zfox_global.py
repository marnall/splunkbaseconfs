from __future__ import absolute_import

import os
import sys
import urllib
from zfsplunk.tgapi import tgapi
import splunklib.client as client
from splunklib.modularinput import *
#from zfsplunk import __version__
#from zfsplunk.zfcapi import ZFClient
from zfsplunk.zfcapi.storage import ZFStorage
from zfsplunk.zfox_global_modinput import ZFoxGlobalModInput
from splunklib import six
from splunklib.six.moves.urllib import parse

class ZFoxGlobal(Script):

    def get_scheme(self):

        scheme = Scheme("ZeroFOX Threat Feed")
        scheme.description = ("Get global and targeted threat indicators from your alerts and Alpha Team.")
        scheme.use_external_validation = True
        scheme.streaming_mode = Scheme.streaming_mode_xml
        scheme.use_single_instance = False

        name_arg = Argument(
            name="name",
            title="ZeroFOX Account",
            description="Name this ZeroFOX Account",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(name_arg)

        token_arg = Argument(
            name="tg_api_key",
            title="Threadfeed API Key",
            description="API Key for ZeroFOX Alert Indicator Enrichment",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(token_arg)

        proxy_username_arg = Argument(
            name="tg_api_proxy_username",
            title="Optional Proxy Username",
            description="The optional username to use if proxying is configured",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_username_arg)

        proxy_password_arg = Argument(
            name="tg_api_proxy_password",
            title="Optional Proxy Password",
            description="The optional password to use if proxying is configured",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_password_arg)

        proxy_host_arg = Argument(
            name="tg_api_proxy_host",
            title="Optional Proxy Host",
            description="The host to use if proxying is configured",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_host_arg)

        proxy_port_arg = Argument(
            name="tg_api_proxy_port",
            title="Optional Proxy Port",
            description="The port to use if proxying is configured",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_port_arg)

        return scheme

    def validate_input(self, definition):
        ew = EventWriter()
        ew.log(EventWriter.DEBUG,"Entering validate_input...")

        config = {}
        config["tg_api_key"] = definition.parameters["tg_api_key"]
        config["session_key"] = definition.metadata["session_key"]
        config["checkpoint_dir"] = definition.metadata["checkpoint_dir"]
        config["stanza"] = definition.metadata["name"]
        config["tg_api_proxy_username"] = definition.parameters["tg_api_proxy_username"] if not definition.parameters["tg_api_proxy_username"]=="None" else None
        config["tg_api_proxy_password"] = definition.parameters["tg_api_proxy_password"] if not definition.parameters["tg_api_proxy_password"]=="None" else None
        config["tg_api_proxy_host"] = definition.parameters["tg_api_proxy_host"] if not definition.parameters["tg_api_proxy_host"]=="None" else None
        config["tg_api_proxy_port"] = definition.parameters["tg_api_proxy_port"] if not definition.parameters["tg_api_proxy_port"]=="None" else None

        self._config = config

        try:
            proxies = {}
            if config["tg_api_proxy_host"] and config["tg_api_proxy_port"]:
                if config["tg_api_proxy_username"] and config["tg_api_proxy_password"]:
                    proxies = {
                        "https": "https://{}:{}@{}:{}".format(config["tg_api_proxy_username"], parse.quote_plus(config["tg_api_proxy_password"]), config["tg_api_proxy_host"], config["tg_api_proxy_port"]),
                    }
                else:
                    proxies = {
                        "https": "https://{}:{}".format(config["tg_api_proxy_host"], config["tg_api_proxy_port"]),
                    }
            if not tgapi.validate_api_key(config["tg_api_key"], proxies):
                ew.log(EventWriter.ERROR,"Threat Feed API key not recognized. Please contact support@zerofox.com.")
                raise ValueError("Threat Feed API key not recognized. Please contact support@zerofox.com.")

            self.zf_store = ZFStorage()
            self.zf_store.set_home(self._config["checkpoint_dir"], config["stanza"].split("://")[-1])

        except ValueError as e:
            raise e
        except Exception as e:
            ew.log(EventWriter.ERROR,str(e))
            raise Exception("Something did not go right: %s" % str(e))

        ew.log(EventWriter.DEBUG,"Exiting validate_input.")

    def stream_events(self, inputs, ew):
        ew.log(EventWriter.DEBUG,"Entering stream_events...")
        self.ew = ew # save it

        try:
            for input_name, input_item in six.iteritems(inputs.inputs):
                ew.log(EventWriter.DEBUG,"input_items = %s" % input_item)
                config = {}
                config["session_key"] = inputs.metadata.get("session_key")
                config["checkpoint_dir"] = inputs.metadata.get("checkpoint_dir")
                config["tg_api_key"] = input_item.get("tg_api_key")
                config["tg_api_proxy_host"] = input_item.get("tg_api_proxy_host")
                config["tg_api_proxy_port"] = input_item.get("tg_api_proxy_port")
                config["tg_api_proxy_username"] = input_item.get("tg_api_proxy_username")
                config["tg_api_proxy_password"] = input_item.get("tg_api_proxy_password")
                config["stanza"] = input_name
                stanza = config["stanza"].split("://")[-1]

                self._config = config
                self.ew.log(EventWriter.DEBUG, "config = %s" % config)
                # Done with initialization

                mod_input = ZFoxGlobalModInput(config, self.ew)
                self.ew.log(EventWriter.DEBUG, "Calling print_indicators()...")
                mod_input.print_indicators()

        except Exception as e:
            ew.log(EventWriter.ERROR, "Error: %s" % str(e))

        #ew.log(EventWriter.INFO, "USERNAME:%s CLEAR_PASSWORD:%s" % (proxy_username, self.PROXY_PASSWORD))
        ew.log(EventWriter.DEBUG,"Exiting stream_events.")

if __name__ == "__main__":
    exitcode = ZFoxGlobal().run(sys.argv)
    sys.exit(exitcode)
