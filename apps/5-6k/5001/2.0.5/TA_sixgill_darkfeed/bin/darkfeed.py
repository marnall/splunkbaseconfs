import import_declare_test

from os import path
from sys import argv, exit
from json import load


from splunklib import modularinput as smi
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi


import input_module_darkfeed as input_module

bin_dir = path.dirname(__file__)

class ModInputdarkfeed(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputdarkfeed, self).__init__("ta_sixgill_darkfeed", "darkfeed", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputdarkfeed, self).get_scheme()
        scheme.title = ("Darkfeed")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        scheme.add_argument(smi.Argument("client_id", title="Client ID",
                                         description="Sixgill API Client ID",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("client_secret", title="Client Secret",
                                         description="Sixgill API Client Secret",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("confidence", title="Minimum Confidence",
                                         description="Minimum STIX indicator confidence level (e.g., 60 or 'all')",
                                         required_on_create=False,
                                         required_on_edit=False))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("splunk_host", title="Splunk Host",
                                         description="Splunk Enterprise Security Host",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("splunk_port", title="Splunk Port",
                                         description="Splunk Enterprise Security Port",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_sixgill_darkfeed"

    def validate_input(self, definition):
        """validate the input stanza"""
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        """write out the events"""
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        return ["global_account"]

    def get_checkbox_fields(self):
        return []

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

if __name__ == "__main__":
    exitcode = ModInputdarkfeed().run(argv)
    exit(exitcode)
