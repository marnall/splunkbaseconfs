from __future__ import absolute_import, division, print_function, unicode_literals

import sys, time, os, json, traceback, base64, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))

from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli

from fints.client import FinTS3PinTanClient, NeedTANResponse, NeedRetryResponse
from fints.utils import minimal_interactive_cli_bootstrap


@Configuration(requires_preop=True)
class fintsauthenticateresponseCommand(ReportingCommand):
    tan_input = Option(require=True)
    account = Option(require=True)


    # Get TAN challenge
    def ask_for_tan(response):
        if getattr(response, 'challenge_hhduc', None):
            try:
                return terminal_flicker_unix(response.challenge_hhduc)
            except KeyboardInterrupt:
                pass

        if getattr(response, 'challenge_matrix', None):
            try:
                return response.challenge_matrix[1]
            except KeyboardInterrupt:
                pass
        return None

    @Configuration()
    def map(self, records):
        return records

    @Configuration()
    def reduce(self, records):
        # Get configs
        cfg = self.service.confs['fints_accounts'][self.account]
        cfg_blz = cfg['blz'] if 'blz' in cfg else None
        cfg_user = cfg['user'] if 'user' in cfg else None
        cfg_endpoint = cfg['endpoint'] if 'endpoint' in cfg else None
        cfg_iban = cfg['iban'] if 'iban' in cfg else None

        passwords = self.service.storage_passwords
        for password in passwords:
            username = str(password.content.username)
            if username == self.account:
                cfg_pin = password.content.clear_password

        client_args = (cfg_blz,cfg_user,cfg_pin,cfg_endpoint)

        # Establish connection from paused client
        for record in records:
            try:
                tan_request = NeedRetryResponse.from_data(base64.decodebytes(record['tan_data'].encode()))
                client = FinTS3PinTanClient(*client_args, from_data=base64.decodebytes(record['client_data'].encode()))

                # Resume client dialog
                with client.resume_dialog(base64.decodebytes(record['dialog_data'].encode())):

                    # Send TAN Answer
                    response = client.send_tan(tan_request, self.tan_input)
                    text = re.findall("text='([^\']+)'", str(response))

                yield {'response_code':'200', 'response_status' : response.status, 'response' : str("\n".join(text)), 'original' : str(response)}
            except Exception as e:
                self.logger.error("FinTS Logging - Error during TAN Authentication. Message: " + traceback(e))
                yield {'response_code' : '400','response' : traceback(e)}
                return

dispatch(fintsauthenticateresponseCommand, sys.argv, sys.stdin, sys.stdout, __name__)
