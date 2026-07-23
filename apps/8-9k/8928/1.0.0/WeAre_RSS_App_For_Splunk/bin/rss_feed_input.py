import import_declare_test

import sys

from splunklib import modularinput as smi
from rss_feed_input_helper import stream_events, validate_input


class RSS_FEED_INPUT(smi.Script):
    def __init__(self):
        super(RSS_FEED_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('rss_feed_input')
        scheme.description = 'RSS Feed Input'
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
                'url',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'verify_ssl',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'http_timeout',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'timestamp_mode',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'timestamp_field',
                required_on_create=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'strip_html_tags',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return validate_input(definition)

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        return stream_events(inputs, ew)


if __name__ == '__main__':
    exit_code = RSS_FEED_INPUT().run(sys.argv)
    sys.exit(exit_code)