import import_declare_test

import json
import sys

from splunklib import modularinput as smi


class INPUTS_BILLING(smi.Script):
    def __init__(self):
        super(INPUTS_BILLING, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('inputs_billing')
        scheme.description = 'Google Cloud BigQuery Billing'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'google_credentials_name',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'google_project',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'google_bq_dataset',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'google_bq_table',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'ingestion_start',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'polling_interval',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        event = smi.Event(
            data=json.dumps(input_items),
            sourcetype='inputs_billing',
        )
        ew.write_event(event)


if __name__ == '__main__':
    exit_code = INPUTS_BILLING().run(sys.argv)
    sys.exit(exit_code)