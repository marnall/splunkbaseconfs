import sys
import logging
import logging.handlers
import os
import re
import json

import splunk.Intersplunk as si
from splunk.clilib.bundle_paths import make_splunkhome_path


class Usage(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def setup_logger():
    """
    Setup a logger for the search command
    """

    logger = logging.getLogger('multisnapshots')
    logger.setLevel(logging.WARN)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'multi_snapshots.log']))
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


def default_snapshot_results(results):
    results["snapshot_name"].append("N/A")
    results["snapshot_descr"].append("N/A")
    results["snapshot_time"].append("N/A")
    results["snapshot_state"].append("N/A")
    results["snapshot_depth"].append("0")

    return results

def is_curresponding_record_found(event, snapshot, depth, file_id):
    """
    This method will traverse through the given event and search for the snapshot matching the specified file_id
    :returns: Boolean denoting whether the match is found or not
    """
    if int(file_id) == int(snapshot["id"]):
        event["snapshot_name"].append(snapshot["name"])
        event["snapshot_descr"].append(snapshot["description"])
        event["snapshot_time"].append(snapshot["createTime"])
        event["snapshot_state"].append(snapshot["state"])
        event["snapshot_depth"].append(str(depth))
        logger.debug("Found match for file id:%s and filename:%s" % (file_id, snapshot["name"]))
        return True

    if "childSnapshotList" in snapshot:
        depth = depth + 1
        # There can be more than one child snapshot for one parent snapshot
        for child_snapshot in snapshot['childSnapshotList']:
            if is_curresponding_record_found(event, child_snapshot, depth, file_id):
                # Return True if the corresponding record is found
                return True

    return False

(isgetinfo, sys.argv) = si.isGetInfo(sys.argv)
if isgetinfo:
    # outputInfo(streaming, generating, retevs, reqsop, preop, timeorder=False):
    si.outputInfo(True, False, True, False, None, False)
    sys.exit(0)

results, dummyresults, settings = si.getOrganizedResults()

if __name__ == '__main__':
    try:
        logger = setup_logger()
        if len(sys.argv) < 3:
            raise Usage(len(sys.argv))

        # From 'snapshot.rootSnapshotList{}' and 'filenames' in argv, get the corresponding JSON data from results
        ss_name = sys.argv[1]
        f_name = sys.argv[2]
        for r in results:
            ss_data = r.get(ss_name)
            filenames = r.get(f_name)
            r["snapshot_name"] = []
            r["snapshot_descr"] = []
            r["snapshot_time"] = []
            r["snapshot_depth"] = []
            r["snapshot_state"] = []
            
            if (ss_data):
                logger.debug('ss_data: %s ...', ss_data)
                try:
                    snapshot = json.loads(ss_data)
                except ValueError:
                    logger.warning("An invalid json found and will be skipped for host : {0}, moid : {1}".format(r['host'], r['moid']))
                    continue

                match = re.search(r'(\d+)\.vmsn', filenames)

                if match:
                    # Extracing the file ID from the regex match
                    file_id = match.group(1)
                    if not is_curresponding_record_found(r, snapshot, 1, file_id):
                        r = default_snapshot_results(r)
                else:
                    r = default_snapshot_results(r)
            else:
                r = default_snapshot_results(r)
        
        logger.debug(results)
        si.outputResults(results)

    except Usage as e:
        results = si.generateErrorResults(
            "Received '%s' arguments. Usage: multilevelsnapshots rootSnapshotList filename" % e)
        si.outputResults(results)

    except Exception as e:
        import traceback

        stack = traceback.format_exc()
        logger.error("Error '%s'" % stack)
        results = si.generateErrorResults("Error '%s'" % stack)
        si.outputResults(results)
