
from splunklib import modularinput as smi

from addon_helper import AddonInput
from nessus_pro_api import NessusProAPI
from nessus_checkpoint import NessusScanCheckpoint


class VulnerabilityScanDetailsInput(AddonInput):
    def collect(self, account_details, http_scheme, verify_ssl, checkpointer):
        nessus_pro_api = NessusProAPI(self.logger, self, account_details, http_scheme, verify_ssl, self.proxy_settings)

        _start_date = self.input_item.get("start_date") if self.input_item.get("start_date") else "1999/01/01"

        nessus_base_url = f"{http_scheme}://{account_details.nessus_url}"

        ckpt = NessusScanCheckpoint(self.logger, checkpointer, nessus_base_url, _start_date)

        if ckpt.contents.get(nessus_base_url,{}).get("start_date") != _start_date:
            ckpt.delete()
            ckpt = NessusScanCheckpoint(self.logger, checkpointer, nessus_base_url, _start_date)

        nessus_pro_api.collect_scan_data(ckpt)



def validate_input(input_script: smi.Script, definition: smi.ValidationDefinition):
    return


def stream_events(input_script: smi.Script, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    session_key = input_script._input_definition.metadata["session_key"]

    for input_name, input_item in inputs.inputs.items():
        VulnerabilityScanDetailsInput(session_key, input_name, input_item, event_writer)

