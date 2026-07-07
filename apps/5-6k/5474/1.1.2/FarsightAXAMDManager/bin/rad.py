import logging
import requests
import sys
from splunk.clilib import cli_common as cli
from axamd.client import Client, Anomaly
from axamd.client.exceptions import ProblemDetails
from splunklib.modularinput import Argument
from splunklib.modularinput import Script
from splunklib.modularinput import Event
from splunklib.modularinput import Scheme
import common


def make_error_message(s, sessionKey):
    headers = {'Authorization': 'Splunk %s' % sessionKey}
    uri = "https://localhost:8089/services/messages/new"
    requests.post(uri, headers=headers,
                  data={'name': 'Farsight SRA Input', 'value': s, 'severity': 'error'},
                  verify=False)


class RADInput(Script):
    """ RAD modular input"""

    def get_scheme(self):
        scheme = Scheme("Farsight RAD")
        scheme.description = "Pulls data from RAD channel"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        name_arg = Argument(
            name="name",
            title="Input name",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(name_arg)

        channels_arg = Argument(
            name="module",
            title="RAD module",
            description="Module documentation available here: [placeholder]",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True,
        )
        scheme.add_argument(channels_arg)

        watches_arg = Argument(
            name="watches",
            title="Watches (comma delimited)",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(watches_arg)

        options_arg = Argument(
            name="options",
            title="Options for selected module",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(options_arg)

        timeout_arg = Argument(
            name="timeout",
            title="Socket timeout in seconds",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(timeout_arg)

        sample_rate_arg = Argument(
            name="sample_rate",
            title="Channel sampling rate (percent)",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(sample_rate_arg)

        rate_limit_arg = Argument(
            name="rate_limit",
            title="Maximum packets per second",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(rate_limit_arg)

        report_interval_arg = Argument(
            name="report_interval",
            title="Seconds between emission of server accounting messages (packet statistics)",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(report_interval_arg)
        return scheme

    def validate_input(self, definition):
        """ Input validation. Stubbed out """
        return

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            global_config = cli.getConfStanza('axamd', 'axamd')
            proxy = global_config["proxy"]

            server = "https://%s" % global_config.get("server")
            module = str(input_item["module"])
            options = str(input_item.get("options", ""))
            watches = [str(x.strip()) for x in input_item["watches"].split(',')]

            kwargs = {}
            if "timeout" in input_item:
                kwargs["timeout"] = input_item["timeout"]
            if "sample_rate" in input_item:
                kwargs["sample_rate"] = float(input_item["sample_rate"]) / 100
            if "rate_limit" in input_item:
                kwargs["rate_limit"] = int(input_item["rate_limit"])
            if "report_interval" in input_item:
                kwargs["report_interval"] = input_item["report_interval"]

            sessionKey = self._input_definition.metadata['session_key']
            apikey = common.get_credentials(sessionKey)
            if proxy != "":
                c = Client(server, apikey, proxy=proxy)
            else:
                c = Client(server, apikey)
            try:
                for line in c.rad(anomalies=[Anomaly(module, watches, options)], **kwargs):
                    event = Event(sourcetype="rad")
                    event.stanza = input_name
                    event.data = line.lstrip("\x1e")
                    ew.write_event(event)
            except ProblemDetails as e:
                raise e
                if "detail" in e:
                    detail = e["detail"]
                else:
                    detail = "No additional details"
                logging.error("Caught AXAMD exception: %s - %s - Logid: %s" % (
                    e['title'], detail, e['logid']))
                make_error_message(
                    "Error in RAD input %s: %s - Logid: %s" % (input_name, detail, e['logid']),
                    sessionKey)


if __name__ == "__main__":
    try:
        RADInput().run(sys.argv)
    except Exception as e:  # pylint disable=broad-except
        logger.error("RAD error: " + str(e))
