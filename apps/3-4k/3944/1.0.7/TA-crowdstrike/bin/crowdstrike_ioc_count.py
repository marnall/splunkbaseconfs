# Python imports
import logging
import sys
import gzip
import csv

# Local imports
from ta_crowdstrike_base_actions import CrowdStrikeBaseAction
import crowdstrike_consts as consts

# Setup the logger
logger = CrowdStrikeBaseAction.setup_logger('crowdstrike_ioc_count_modalert')


class CrowdStrikeIOCCountAction(CrowdStrikeBaseAction):

    def __init__(self, settings, logger, action_name=None):
        """ Initialize object of CrowdStrikeIOCCountAction.

        :param settings: includes action metadata and various other configurations obtained by reading standard input
        :param logger: logger for the action
        :param action_name: action name
        """

        # Call __int__ of super class
        super(CrowdStrikeIOCCountAction, self).__init__(settings, logger, action_name)

# Start execution of script
if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

    # Create object of "CrowdStrikeIOCCountAction" class
    modaction = CrowdStrikeIOCCountAction(sys.stdin.read(), logger, 'crowdstrike_ioc_count')

    try:
        modaction.addinfo()
        # Define the endpoint for the action
        endpoint = consts.GET_DEVICE_COUNTS_ASSOCIATED_WITH_IOC
        # Get the required and optional parameters for the action
        indicator_type = modaction.configuration.get("indicator_type")
        indicator_value = modaction.configuration.get("indicator_value")

        # Prepare request parameters
        params = {"type": indicator_type, "value": indicator_value}

        # Iterate over the results and invoke action
        with gzip.open(modaction.results_file, 'rb') as fh:
            for num, result in enumerate(csv.DictReader(fh)):
                # set rid to row # (0->n) if unset
                result.setdefault('rid', str(num))
                modaction.update(result)
                modaction.invoke()
                if indicator_value == "ioc_value":
                    params["value"] = result[indicator_value]
                else:
                    params["value"] = indicator_value
                # Perform the actual work
                modaction.dowork(endpoint, params=params, source="falconapi.crowdstrike.com",
                                 sourcetype="crowdstrike:falconhost:ar")

    except Exception as e:
        try:
            modaction.message(e, 'failure', level=logging.CRITICAL)
        except:
            logger.critical(e)
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        sys.exit(3)
