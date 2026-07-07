# Python imports
import logging
import sys
import json
import gzip
import csv

# Local imports
from ta_crowdstrike_base_actions import CrowdStrikeBaseAction
import crowdstrike_consts as consts

# Setup the logger
logger = CrowdStrikeBaseAction.setup_logger('crowdstrike_change_detection_state_modalert')


class CrowdStrikeChangeDetectionStatusAction(CrowdStrikeBaseAction):

    def __init__(self, settings, logger, action_name=None):
        """ Initialize object of CrowdStrikeChangeDetectionStatusAction.

        :param settings: includes action metadata and various other configurations obtained by reading standard input
        :param logger: logger for the action
        :param action_name: action name
        """

        # Call __int__ of super class
        super(CrowdStrikeChangeDetectionStatusAction, self).__init__(settings, logger, action_name)

# Start execution of script
if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)

    # Create object of "CrowdStrikeChangeDetectionStatusAction" class
    modaction = CrowdStrikeChangeDetectionStatusAction(sys.stdin.read(), logger, 'crowdstrike_change_detection_state')

    try:
        modaction.addinfo()
        # Define the endpoint for the action
        endpoint = consts.CHANGE_DETECTION_STATE
        # Get the required and optional parameters for the action
        detection_id = modaction.configuration.get("detection_id")
        detection_status = modaction.configuration.get("detection_status")
        data = {"status": detection_status}

        # Iterate over the results and invoke action
        with gzip.open(modaction.results_file, 'rb') as fh:
            for num, result in enumerate(csv.DictReader(fh)):
                # set rid to row # (0->n) if unset
                result.setdefault('rid', str(num))
                modaction.update(result)
                modaction.invoke()
                if detection_id == "detection_id":
                    data["ids"] = [result[detection_id]]
                else:
                    data["ids"] = [detection_id]
                # Perform the actual work
                modaction.dowork(endpoint, method="patch", data=json.dumps(data), source="falconapi.crowdstrike.com",
                                 sourcetype="crowdstrike:falconhost:ar")

    except Exception as e:
        try:
            modaction.message(e, 'failure', level=logging.CRITICAL)
        except:
            logger.critical(e)
        print >> sys.stderr, "ERROR Unexpected error: %s" % e
        sys.exit(3)
