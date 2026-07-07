import import_declare_test

import os
import os.path as op
import sys
import time
import datetime
import json

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi

import os
import sys
import time
import datetime
import json

import import_declare_test

from splunklib import modularinput as smi


import input_module_cve as input_module

bin_dir = os.path.basename(__file__)

"""
"""


class ModInputcve(base_mi.BaseModInput):

  def __init__(self):
    if "use_single_instance_mode" in dir(input_module):
      use_single_instance = input_module.use_single_instance_mode()
    else:
      use_single_instance = False
    super(ModInputcve, self).__init__("ta_gti_app", "cve", use_single_instance)
    self.global_checkbox_fields = None

  def get_scheme(self):
    """overloaded splunklib modularinput method"""
    scheme = super(ModInputcve, self).get_scheme()
    scheme.title = "CVE"
    scheme.description = "Go to the add-on's configuration UI and configure modular inputs under the Inputs menu."
    scheme.use_external_validation = True
    scheme.streaming_mode_xml = True

    scheme.add_argument(
        smi.Argument(
            "name", title="Name", description="", required_on_create=True
        )
    )

    """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
    scheme.add_argument(
        smi.Argument(
            "risk_rating",
            title="Risk Rating",
            description="",
            required_on_create=False,
            required_on_edit=False,
        )
    )
    scheme.add_argument(
        smi.Argument(
            "exploitation_state",
            title="Exploitation State",
            description="",
            required_on_create=False,
            required_on_edit=False,
        )
    )
    return scheme

  def get_app_name(self):
    return "TA-gti-app"

  def validate_input(self, definition):
    """validate the input stanza"""
    input_module.validate_input(self, definition)

  def collect_events(self, ew):
    """write out the events"""
    input_module.collect_events(self, ew)

  def get_account_fields(self):
    account_fields = []
    return account_fields

  def get_checkbox_fields(self):
    checkbox_fields = []
    return checkbox_fields

  def get_global_checkbox_fields(self):
    if self.global_checkbox_fields is None:
      checkbox_name_file = os.path.join(bin_dir, "global_checkbox_param.json")
      try:
        if os.path.isfile(checkbox_name_file):
          with open(checkbox_name_file, "r") as fp:
            self.global_checkbox_fields = json.load(fp)
        else:
          self.global_checkbox_fields = []
      except Exception as e:
        self.log_error(
            "Get exception when loading global checkbox parameter names. "
            + str(e)
        )
        self.global_checkbox_fields = []
    return self.global_checkbox_fields


if __name__ == "__main__":
  exitcode = ModInputcve().run(sys.argv)
  sys.exit(exitcode)
