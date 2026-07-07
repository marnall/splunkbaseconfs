"""Custom alert action to send outbound TS Splunk App matches to ThreatStream"""
import json
import sys
import six
from datetime import datetime
from splunklib.results import Message
from logger import setup_logger

from ts.optic_client import Optic
from ts.settings import default_ui_url
from util.utils import verify_https_url
import util.splunk_access

import splunklib.results as results
import splunklib

logger = setup_logger('ts_my_attacks')


def my_attacks(splunk_config):
    """Main execution loop to get the my_attacks data from Splunk.
    1. Creates the Pre-requisite MyAttacks"""
    if six.PY2:
        python_version = 'python2'
    else:
        python_version = 'python3'

    logger.debug("Running on {}".format(python_version))
    logger.debug("Splunk SDK Library version {}".format(splunklib.__version__))
    splunk_job_sid = splunk_config.get('sid')
    session_key = splunk_config.get('session_key')

    splunkd = util.splunk_access.SplunkAccess(logger=logger, session_key=session_key)
    user_org_id = None

    try:
        # here we support onprem, TS Cloud and Integrator
        setup_config = splunkd.config.setup_config()
        # URL is the value of 'Snapshot Host' on Splunk App Setup Page
        url = setup_config.get("url")
        # on_prem_url is the value of 'UI Host' on Splunk App Setup Page
        on_prem_url = setup_config.get('on_prem_url')
        myattacks_url = verify_https_url(url, logger)
    except Exception as e:
        six.print_("ERROR getting config %s" % e, file=sys.stderr)
        logger.error("ERROR getting config %s" % e)

    try:
        optic = Optic(url=myattacks_url, splunka=splunkd, logger=logger)
        user_org_id = optic.get_user_org_id(on_prem_url)
        optic.myattacks.user_org_id = user_org_id
    except Exception as f:
        logger.error("ERROR getting Org ID: %s" % f)

    # Get results
    myattacks_job = splunkd.service.jobs[splunk_job_sid]

    # ``JSONResultsReader`` is iterable, and returns a ``dict`` for results, or a
    # :class:`Message` object for Splunk messages. This class has one field,
    # ``is_preview``, which is ``True`` when the results are a preview from a
    # running search, or ``False`` when the results are from a completed search.

    results_stream = results.JSONResultsReader(myattacks_job.results(output_mode='json'))
    # Deprecated results_stream = results.ResultsReader(myattacks_job.results())

    my_attack_results = [r for r in results_stream]
    # Check if the first element is the "No matching fields exist." Splunk message, handling the case
    # where there are no events generated
    no_results_message = (
            my_attack_results
            and isinstance(my_attack_results[0], Message)
            and 'No matching fields exist' in my_attack_results[0].message
    )
    if no_results_message:
        six.print_("No results to send to Threatstream My Attacks", file=sys.stderr)
        logger.info("No results to send to Threatstream My Attacks")
        return

    # SPK-862 - Filter out any other Splunk Message objects that may be in the events stream
    # E.G: "WARN: One or more peers has been excluded from the search because they have been quarantined"
    filtered_my_attack_results = []
    splunk_message_objects = []
    for r in my_attack_results:
        if isinstance(r, Message):
            splunk_message_objects.append(r)
        else:
            filtered_my_attack_results.append(r)
    if splunk_message_objects:
        logger.info("The following Splunk Message Objects were found and stripped from MyAttacks results: %s" % splunk_message_objects)
    logger.debug("results_list: %s" % filtered_my_attack_results)

    if filtered_my_attack_results:
        try:
            time_format = '%Y-%m-%dT%H:%M:%S.%f'
            myattacks_ts = datetime.utcnow()
            myattacks_time = myattacks_ts.strftime(time_format)
            for my_attack in filtered_my_attack_results:
                my_attack['device_source'] = 'splunk'
                my_attack['reported_ts'] = myattacks_time
                if user_org_id:
                    my_attack['org_id'] = user_org_id

            optic.myattacks.send(filtered_my_attack_results)
        except Exception as e:
            logger.exception(e)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        try:
            my_attacks(payload)
        except Exception as e:
            logger.error("Failed to send My Attacks data to Threatstream")
            logger.exception(e)
