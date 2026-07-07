"""This is Input Module file for account scoring input."""

import ta_vectra_saas_declare  # noqa:F401
import traceback
import logging

logger = logging.getLogger()
from common import log


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    # vectra_saas_account = definition.parameters.get('vectra_saas_account', None)
    pass


def collect_events(helper, ew):
    """Implement your data collection logic here."""
    try:
        # Keep all code (including imports) inside this higher level try block
        # to make sure that error logs always gets printed in log file
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'modinputs', 'account_scoring')))
        sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'common')))

        import collector

        input_name = helper.get_arg("name")
        logger = log.get_logger("account_scoring_input_{}".format(input_name))

        asc = collector.AccountScoringCollector(logger)
        asc.run(helper, ew)

    except Exception:
        logger.error(traceback.format_exc())
