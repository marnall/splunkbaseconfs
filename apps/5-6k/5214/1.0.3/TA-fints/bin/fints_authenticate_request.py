import sys, time, os, json, base64, traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli

from fints.client import FinTS3PinTanClient, NeedTANResponse, NeedRetryResponse
from fints.utils import minimal_interactive_cli_bootstrap

from decimal import Decimal

@Configuration()
class fintsauthenticaterequestCommand(GeneratingCommand):
    account = Option(require=True)


    # Get TAN challenge
    def ask_for_tan(self, response):
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

    # Try to retrieve a TAN
    def get_data_objects(self, f):
        needResponse = False
        tan_mechanism = f.get_current_tan_mechanism()
        with f:
            if f.init_tan_response:
                tan_content = self.ask_for_tan(f.init_tan_response)
                if tan_content is not None:
                   tan_content = base64.encodebytes(self.ask_for_tan(f.init_tan_response)).decode()
                else:
                   tan_content = ""

                needResponse = True
            dialog_data = base64.encodebytes(f.pause_dialog()).decode()


        # Got TAN challenge, need to forward TAN data
        if needResponse:
            client_data = base64.encodebytes(f.deconstruct(including_private=True)).decode()
            tan_data = base64.encodestring(f.init_tan_response.get_data()).decode()
            tan_challenge = NeedRetryResponse.from_data(f.init_tan_response.get_data()).challenge
            return {'response' : None, 'response_code' : '200', 'tan_challenge' : tan_challenge, 'tan_content' : tan_content, 'tan_data' : tan_data, 'client_data' : client_data, 'dialog_data' : dialog_data, 'tan_mechanism' : tan_mechanism}   
        else:
            return {'response' : 'No TAN required.', 'response_code' : '100', 'tan_challenge' : 'No TAN required.'}


    def generate(self):
        # Get configs
        cfg = self.service.confs['fints_accounts'][self.account]
        cfg_blz = cfg['blz'] if 'blz' in cfg else None
        cfg_user = cfg['user'] if 'user' in cfg else None
        cfg_endpoint = cfg['endpoint'] if 'endpoint' in cfg else None

        passwords = self.service.storage_passwords
        for password in passwords:
            username = str(password.content.username)
            if username == self.account:
                cfg_pin = password.content.clear_password

        client_args = (cfg_blz,cfg_user,cfg_pin,cfg_endpoint)

        # Establish connection and retrieve TAN challenge if required
        try:
            f = FinTS3PinTanClient(*client_args)
            minimal_interactive_cli_bootstrap(f)
             # Select first iban if not given
            yield self.get_data_objects(f)

        except Exception as e:
            self.logger.error("FinTS Logging - TAN Request Failed" + str(e))
            yield {'response' : 'Error: ' + str(e), 'response_code': '400'}
            pass


dispatch(fintsauthenticaterequestCommand, sys.argv, sys.stdin, sys.stdout, __name__)
