# encoding = utf-8
import ta_netskopeappforsplunk_declare
import logging

logger = logging.getLogger()


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Collect Netskope events."""
    try:
        # Keep all code (including imports) inside this higher level try block
        # to make sure that error logs always gets printed in log file

        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'common')))
        sys.path.insert(0, os.path.abspath(os.path.join(__file__, '..', 'modinputs', 'clients')))

        import collector
        import utility

        utility.disable_external_lib_logging()

        ec = collector.ClientsCollector()
        ec.run(helper, ew)

    except Exception as ex:
        logger.exception(ex)
