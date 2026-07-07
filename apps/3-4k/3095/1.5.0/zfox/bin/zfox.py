#!/usr/bin/env python
from __future__ import absolute_import
import sys

from zfsplunk.zfox_modinput import ZFoxModInput
from zfsplunk.zfcapi import ZFClient
from zfsplunk import __version__
from splunklib.modularinput import *
from splunklib import six
from splunklib.six.moves.urllib import parse

class ZFox(Script):
    """All modular inputs should inherit from the abstract base class Script
    from splunklib.modularinput.script.
    They must override the get_scheme and stream_events functions, and,
    if the scheme returned by get_scheme has Scheme.use_external_validation
    set to True, the validate_input function.
    """
    def get_scheme(self):
        """When Splunk starts, it looks for all the modular inputs defined by
        its configuration, and tries to run them with the argument --scheme.
        Splunkd expects the modular inputs to print a description of the
        input in XML on stdout. The modular input framework takes care of all
        the details of formatting XML and printing it. The user need only
        override get_scheme and return a new Scheme object.

        :return: scheme, a Scheme object
        """
        scheme = Scheme("ZeroFOX")
        scheme.description = ("Get alerts and stats from ZeroFOX.")
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
            name="zf_api_token",
            title="ZeroFOX API Token",
            description="ZeroFOX API Token",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(token_arg)

        proxy_username_arg = Argument(
            name="zf_api_proxy_username",
            title="Optional Proxy Username",
            description="The optional username to use if proxying is configured",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_username_arg)

        proxy_password_arg = Argument(
            name="zf_api_proxy_password",
            title="Optional Proxy Password",
            description="The optional password to use if proxying is configured",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_password_arg)

        proxy_host_arg = Argument(
            name="zf_api_proxy_host",
            title="Optional Proxy Host",
            description="The host to use if proxying is configured",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_host_arg)

        proxy_port_arg = Argument(
            name="zf_api_proxy_port",
            title="Optional Proxy Port",
            description="The port to use if proxying is configured",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_port_arg)

        expand_metadata_arg = Argument(
            name="expand_metadata",
            title="Metadata expansion",
            description="Enable Alert metadata expansion",
            data_type=Argument.data_type_boolean,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(expand_metadata_arg)

        return scheme

    def validate_input(self, validation_definition):
        """In this example we are using external validation to verify that min is
        less than max. If validate_input does not raise an Exception, the input is
        assumed to be valid. Otherwise it prints the exception as an error message
        when telling splunkd that the configuration is invalid.

        When using external validation, after splunkd calls the modular input with
        --scheme to get a scheme, it calls it again with --validate-arguments for
        each instance of the modular input in its configuration files, feeding XML
        on stdin to the modular input to do validation. It is called the same way
        whenever a modular input's configuration is edited.

        :param validation_definition: a ValidationDefinition object
        """
        ew = EventWriter()
        ew.log(EventWriter.DEBUG,"Entering validate_input...")
        ew.log(EventWriter.DEBUG,"validation_definition = %s" % validation_definition.__dict__)
        #raise Exception("validation_definition = %s" % validation_definition.__dict__)
        config = {}
        config["zf_api_token"] = validation_definition.parameters["zf_api_token"]
        #if config["zf_api_token"] == self.MASK:
        #    return # Can't validate token if it isn't an actual value. This can happen when the input is being saved again in mask_password. So, just skip the check.

        config["session_key"] = validation_definition.metadata["session_key"]
        config["checkpoint_dir"] = validation_definition.metadata["checkpoint_dir"]
        config["stanza"] = validation_definition.metadata["name"]
        config["zf_api_proxy_username"] = validation_definition.parameters["zf_api_proxy_username"] if not validation_definition.parameters["zf_api_proxy_username"]=="None" else None
        config["zf_api_proxy_password"] = validation_definition.parameters["zf_api_proxy_password"] if not validation_definition.parameters["zf_api_proxy_password"]=="None" else None
        config["zf_api_proxy_host"] = validation_definition.parameters["zf_api_proxy_host"] if not validation_definition.parameters["zf_api_proxy_host"]=="None" else None
        config["zf_api_proxy_port"] = validation_definition.parameters["zf_api_proxy_port"] if not validation_definition.parameters["zf_api_proxy_port"]=="None" else None
        config["expand_metadata"] = validation_definition.parameters["expand_metadata"]
        #raise Exception(config["zf_api_proxy_username"])

        self._config = config
        self._zfox = ZFClient()
        self._zfox.config.client = "ZeroFOX for Splunk/" + __version__
        self._zfox.config.client_id = config["stanza"].split("://")[-1]

        try:
            proxies = {}
            if config["zf_api_proxy_host"] and config["zf_api_proxy_port"]:
                if config["zf_api_proxy_username"] and config["zf_api_proxy_password"]:
                    proxies = {
                        "https": "https://{}:{}@{}:{}".format(config["zf_api_proxy_username"], parse.quote_plus(config["zf_api_proxy_password"]), config["zf_api_proxy_host"], config["zf_api_proxy_port"]),
                    }
                else:
                    proxies = {
                        "https": "https://{}:{}".format(config["zf_api_proxy_host"], config["zf_api_proxy_port"]),
                    }
            if not self._zfox.start_session(config["zf_api_token"], proxies=proxies):
                ew.log(EventWriter.ERROR,"API Token validation failed [{}]".format(self._zfox.last_error))
                raise ValueError("API Token validation failed [{}]".format(self._zfox.last_error))

            zf_store = self._zfox.storage()
            zf_store.set_home(self._config["checkpoint_dir"], self._zfox.config.client_id)
            self._zfox.save_session()

        except ValueError as e:
            raise e
        except Exception as e:
            ew.log(EventWriter.ERROR,str(e))
            raise Exception("Something did not go right: %s" % str(e))

        ew.log(EventWriter.DEBUG,"Exiting validate_input.")


    def stream_events(self, inputs, ew):
        """This function handles all the action: splunk calls this modular input
        without arguments, streams XML describing the inputs to stdin, and waits
        for XML on stdout describing events.

        If you set use_single_instance to True on the scheme in get_scheme, it
        will pass all the instances of this input to a single instance of this
        script.

        :param inputs: an InputDefinition object
        :param ew: an EventWriter object
        """

        ew.log(EventWriter.DEBUG,"in stream_events")
        self.ew = ew # save it so other classes can use it

        try:
            # Go through each input for this modular input
            for input_name, input_item in six.iteritems(inputs.inputs):
                ew.log(EventWriter.DEBUG,"input_item = %s" % input_item)

                config = {}
                config["session_key"] = inputs.metadata.get("session_key")
                config["checkpoint_dir"] = inputs.metadata.get("checkpoint_dir")
                config["zf_api_token"] = input_item.get("zf_api_token")
                config["zf_api_proxy_host"] = input_item.get("zf_api_proxy_host")
                config["zf_api_proxy_port"] = input_item.get("zf_api_proxy_port")
                config["zf_api_proxy_username"] = input_item.get("zf_api_proxy_username")
                config["zf_api_proxy_password"] = input_item.get("zf_api_proxy_password")
                config["expand_metadata"] = input_item.get("expand_metadata")
                config["host"] = input_item.get("host")
                config["index"] = input_item.get("index")
                config["stanza"] = input_name
                stanza = config["stanza"].split("://")[-1]
                ew.log(EventWriter.DEBUG,"config = %s " % config)
                self._config = config

                # Instantiate the worker class and call it to retrieve and output the ZFOX events
                mod_input = ZFoxModInput(config, self.ew)
                ew.log(EventWriter.DEBUG, "Calling print_alerts()...")
                mod_input.print_alerts()

        except Exception as e:
            ew.log(EventWriter.ERROR, "Error: %s" % str(e))

        ew.log(EventWriter.DEBUG,"done with stream_events")

if __name__ == "__main__":
    sys.exit(ZFox().run(sys.argv))
