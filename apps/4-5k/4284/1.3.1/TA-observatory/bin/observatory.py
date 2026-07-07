""" Observatory Modular Input for Splunk """

import sys
import json
import time
import requests
from splunklib.modularinput import Argument
from splunklib.modularinput import Script
from splunklib.modularinput import Event
from splunklib.modularinput import Scheme


def initiate_site_scan(domain):
    """ Initiate observatory scan """
    url = 'https://http-observatory.security.mozilla.org/api/v1/analyze'
    params = {'host': domain}
    data = {'rescan': 'true'}
    requests.post(url, params=params, data=data)
    return


def get_scan_results(domain):
    """ Get results of scan """
    # First, get high-level scan results (grade, score)
    # These come from a different endpoint than general scan results
    grade = None
    score = None
    scan_id = None
    attempt_count = 0
    while attempt_count < 10:
        url = 'https://http-observatory.security.mozilla.org/api/v1/analyze'
        params = {'host': domain}
        response = requests.get(url, params=params).json()
        if response['state'] != 'FINISHED':
            time.sleep(10)
            attempt_count += 1
        else:
            grade = response['grade']
            score = response['score']
            scan_id = response['scan_id']
            break

    # Next, grab detailed scan results
    url = 'https://http-observatory.security.mozilla.org/api/v1/getScanResults'
    params = {'scan': scan_id}
    response = requests.get(url, params=params).json()
    out = []
    for rule in response:
        result = {'site': domain,
                  'rule': rule,
                  'grade': grade,
                  'score': score,
                  'scan_id': scan_id,
                  'expectation': response[rule]['expectation'],
                  'pass': response[rule]['pass'],
                  'result': response[rule]['result'],
                  'score_description': response[rule]['score_description'],
                  'score_modifier': response[rule]['score_modifier'],
                  'output': response[rule]['output']}
        out.append(result)
    return out


def inspect_site(domain):
    """ Inspect a given domain """

    # Initiate scan
    initiate_site_scan(domain)
    time.sleep(0.5)
    out = get_scan_results(domain)
    return out


class ObservatoryInput(Script):
    """ Observatory modular input """

    def get_scheme(self):
        scheme = Scheme("Observatory Input")
        scheme.description = "Reports on a domain using Mozilla's Observatory tool "
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

        domain_arg = Argument(
            name="domain",
            title="Scan target domain",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(domain_arg)
        return scheme

    def validate_input(self, definition):
        """ Input validation. Stubbed out for now """
        return

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.items():
            domain = input_item["domain"]
            results = inspect_site(domain)
            for result in results:

                event = Event()
                event.stanza = input_name
                event.data = json.dumps(result)
                ew.write_event(event)


if __name__ == "__main__":
    exitcode = ObservatoryInput().run(sys.argv)
    sys.exit(exitcode)
