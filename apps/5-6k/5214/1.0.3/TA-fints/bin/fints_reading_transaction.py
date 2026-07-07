import sys, time, os, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli

from fints.client import FinTS3PinTanClient, NeedTANResponse
from fints.utils import minimal_interactive_cli_bootstrap

@Configuration()
class fints_transactionCommand(GeneratingCommand):
    account = Option(require=True)
    startdate = Option(require=False)
    enddate = Option(require=False)

    def generate(self):
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

        # Set time frame -30d@d until today if none is given
        if not self.startdate:
            self.startdate = str(datetime.date.today() - datetime.timedelta(days=30))
        if not self.enddate:
            self.enddate = str(datetime.date.today())

        # Establish connection
        f = FinTS3PinTanClient(*client_args)
        minimal_interactive_cli_bootstrap(f)

        # Select iban account, take first if none is given
        accounts = f.get_sepa_accounts()

        if len(accounts) == 1:
            account = accounts[0]
        else:
            if cfg_iban is not None:
                for i, mm in enumerate(accounts):
                    if mm.iban == cfg_iban:
                        account = accounts[i]
                        break

        with f:
            try:
                # Retrieve transactions for given time frame
                res = f.get_transactions(account, datetime.datetime.strptime(self.startdate, '%Y-%m-%d'), datetime.datetime.strptime(self.enddate, '%Y-%m-%d'))
                while isinstance(res, NeedTANResponse):
                    raise Exception

                # Iterate over transaction results
                for r in res:
                    data = {}
                    for key in r.data:
                        data[key] = str(r.data[key])
                    event = {'_raw' : data}
                    event.update(data)

                    # forward each transaction to resultset
                    yield event

            except Exception as e:
                self.logger.error("FinTS Logging - Transaction Request Failed: " + str(e))


dispatch(fints_transactionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
