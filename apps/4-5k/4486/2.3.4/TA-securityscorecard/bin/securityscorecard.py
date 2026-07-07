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
import ta_securityscorecard_declare # noqa

import os
import sys
import json
from urllib.parse import quote

import import_declare_test

from splunklib import modularinput as smi
import input_module_securityscorecard as input_module

bin_dir = os.path.basename(__file__)

'''
'''

class BaseModinputWrapper(base_mi.BaseModInput):
    """Override the BaseModInput class to provide the support of special characters in proxy configuration."""
    def _get_proxy_uri(self):
        uri = None
        proxy = self.get_proxy()
        if proxy and proxy.get('proxy_url') and proxy.get('proxy_type'):
            uri = proxy['proxy_url']
            if proxy.get('proxy_port'):
                uri = '{0}:{1}'.format(uri, proxy.get('proxy_port'))
            if proxy.get('proxy_username') and proxy.get('proxy_password'):
                uri = '{0}://{1}:{2}@{3}/'.format(proxy['proxy_type'], quote(proxy[
                    'proxy_username'], safe=''), quote(proxy['proxy_password'], safe=''), uri)
            else:
                uri = '{0}://{1}'.format(proxy['proxy_type'], uri)
        return uri


class ModInputsecurityscorecard(BaseModinputWrapper):
    """Represents a ModInputsecurityscorecard object."""

    def __init__(self):
        """Initializes ModInputsecurityscorecard object."""
        use_single_instance = False
        super(ModInputsecurityscorecard, self).__init__(
            "ta_securityscorecard", "securityscorecard", use_single_instance
        )
        self.global_checkbox_fields = None

    def get_scheme(self):
        """Overloaded splunklib modularinput method."""
        scheme = super(ModInputsecurityscorecard, self).get_scheme()
        scheme.title = ("SecurityScorecard")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs \
            under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("securityscorecard_api_url", title="SecurityScorecard API URL",
                                         description="Enter the SecurityScorecard API URL.Url should contain https.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("level_overall_change", title="Severity - Overall Score",
                                         description="Specify the severity level to be used when logging overall score \
                                            changes to Splunk.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("level_factor_change", title="Severity - Factor Score",
                                         description="Specify the severity level to be used when logging factor score \
                                            changes to Splunk.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("level_new_issue_change", title="Severity - Issue Level Events",
                                         description="Specify the severity level to be used when logging changes in \
                                            the scorecard event log.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("domain", title="Your Domain",
                                         description="Please enter your own scorecard\'s domain to monitor your own \
                                            scorecard. This is a mandatory field.",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("fetch_company_factors", title="Log factor score for self?",
                                         description="Do you want to monitor the factor level score for your own \
                                            scorecard?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("fetch_company_issues", title="Log new events for self?",
                                         description="Do you want to monitor for issue level events for your own \
                                            scorecard?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("diff_override_own_overall", title="Log if overall score is zero?",
                                         description="Do you want to log events to Splunk when overall score for \
                                            yourself does not change?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("diff_override_own_factor", title="Log if factor score is zero?",
                                         description="Do you want to log events to Splunk when the factor level scores \
                                            for yourself do not change?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("portfolio_ids", title="Portfolio Ids",
                                         description="To monitor all portfolio ids, please enter \'all\'. If you want \
                                            to monitor specific portfolio ids, then please enter comma separate list \
                                            of portfolio ids",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("fetch_portfolio_overall", title="Log overall score - 3rd party?",
                                         description="Do you want to monitor the overall score for 3rd party \
                                            scorecards?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("fetch_portfolio_factors", title="Log factor score - 3rd party?",
                                         description="Do you want to monitor the factor level score for 3rd party \
                                            scorecards?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("fetch_portfolio_issues", title="Log new events - 3rd party?",
                                         description="Do you want to monitor for issue level events for 3rd party \
                                            scorecards?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("diff_override_portfolio_overall", title="Log overall score when zero?",
                                         description="Do you want to log events to Splunk when the overall level scores \
                                            for 3rd parties do not change?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("diff_override_portfolio_factor", title="Log factor score when zero?",
                                         description="Do you want to log events to Splunk when the factor level scores \
                                            for 3rd parties do not change?",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("fetch_issue_level_data", title="Log issue level findings?",
                                         description="Do you want to log issue level details to splunk?",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        """This method returns the TA name."""
        return "TA-securityscorecard"

    def validate_input(self, definition):
        """Validate the input stanza."""
        input_module.validate_input(self, definition)

    def collect_events(self, ew):
        """Write out the events."""
        input_module.collect_events(self, ew)

    def get_account_fields(self):
        """This method returns the account configuration fields."""
        account_fields = []
        account_fields.append("global_account")
        return account_fields

    def get_checkbox_fields(self):
        """This method returns the fields that contains checkbox."""
        checkbox_fields = []
        checkbox_fields.append("fetch_company_factors")
        checkbox_fields.append("fetch_company_issues")
        checkbox_fields.append("diff_override_own_overall")
        checkbox_fields.append("diff_override_own_factor")
        checkbox_fields.append("fetch_portfolio_overall")
        checkbox_fields.append("fetch_portfolio_factors")
        checkbox_fields.append("fetch_portfolio_issues")
        checkbox_fields.append("diff_override_portfolio_overall")
        checkbox_fields.append("diff_override_portfolio_factor")
        checkbox_fields.append("fetch_issue_level_data")
        return checkbox_fields

    def get_global_checkbox_fields(self):
        """This method returns the global checkbox fields."""
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == "__main__":
    exitcode = ModInputsecurityscorecard().run(sys.argv)
    sys.exit(exitcode)
