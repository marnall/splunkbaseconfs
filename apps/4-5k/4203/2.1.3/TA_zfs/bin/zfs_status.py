import json
import datetime
import subprocess
import re
import sys
from collections import OrderedDict

# Import our helpers
from zfs_helpers import *

SCHEME = """<scheme>
  <title>ZFS status</title>
  <description>Get data from zpool status command.</description>
  <use_external_validation>false</use_external_validation>
  <streaming_mode>simple</streaming_mode>

  <endpoint>
    <args>
      <arg name="zpool_list">
        <title>Zpool List</title>
        <description>A space delimited list of one or more zpools to investigate with the zfs status command. Use ALL__POOLS to specify using all zpools returned by zpool list.</description>
        <validation>
          validate(isstr('zpool_list'),"zpool_list is not a string")
        </validation>
      </arg>
    </args>
  </endpoint>
</scheme>
"""


def do_scheme():
    print SCHEME


# Routine to get the value of an input
def get_status():
    try:
        pools_out = get_pools()
        for pool_name in pools_out:
            logging.debug("zpool status for '%s'" % pool_name)
            status_cmd = ['zpool', 'status', pool_name]
            status_obj = subprocess.Popen(
                status_cmd, stdout=subprocess.PIPE).stdout.read()
            logging.debug("zpool status is %s" % status_obj)

            # catch stats if ZFS scrub is in progress
            if "scrub in progress since" in status_obj:
                logging.debug("scrub in progress")
                status_vars = re.search(
                    "\s*state:\s(?P<state>.+?)$\s*scan:\s(?P<operation_type>scrub\sin\sprogress)\ssince\s(?P<operation_date_o>.+?\d{4})$\s*(?P<scanned_bytes_o>[0-9.]+?[BKMGTP])\sscanned\sout\sof\s(?P<target_bytes_o>[0-9.]+?[BKMGTP])\sat\s(?P<operation_speed>[0-9.].+?)\,\s(?P<togo_o>\S+)\sto\sgo$\s*(?P<repaired_bytes_o>[0-9.]+?[BKMGTP])\srepaired\,\s(?P<operation_pct>[0-9.]+?)\%\sdone$\s*config:.+?errors:\s*(?P<errors>.+?)$",
                    status_obj, re.MULTILINE | re.DOTALL)
                status_type = "scrub_in_progress"

            # catch stats if ZFS had a scrub canceled before completing.
            elif "scrub canceled on" in status_obj:
                logging.debug("scrub was canceled")
                status_vars = re.search(
                    "\s*state:\s(?P<state>.+?)$\s*scan:\s(?P<operation_type>scrub\scanceled)\son\s(?P<operation_date_o>.+?\d{4})$\s*config:.+?errors:\s*(?P<errors>.+?)$",
                    status_obj, re.MULTILINE | re.DOTALL)
                status_type = "scrub_canceled"

            # catch stats if ZFS is resilvering
            elif "resilver in progress" in status_obj:
                logging.debug("resilver in progress")
                status_vars = (
                    "\s*state\:\s(?P<state>.+?)$\s*status\:.+?action\:\s(?P<action>.+?)$\s*scrub\:\s(?P<operation_type>resilver\sin\sprogress)\sfor\s(?P<duration_o>\S+)\,\s(?P<operation_pct>[0-9.]+?)\%\sdone\,\s(?P<togo_o>\S+)\sto\sgo$\s*config:.+?errors:\s*(?P<errors>.+?)$",
                    status_obj, re.MULTILINE | re.DOTALL)
                status_type = "resilver_in_progress"

            # relatively normal status output.
            else:
                logging.debug("nominal operation")
                status_vars = re.search(
                    "\s*state:\s(?P<state>.+?)$\s*scan:\s(?P<operation_type>scrub\srepaired|resilvered)\s(?P<operation_bytes_o>[0-9.]+?[BKMGTP])\sin\s(?P<duration_o>.+?)\swith\s(?P<operation_errors>\d+?)\serrors\son\s(?P<operation_date_o>.+?\d{4})$\s*config:.+?errors:\s*(?P<errors_o>.+?)$",
                    status_obj, re.MULTILINE | re.DOTALL)
                status_type = "normal"

            # we got a weird one. Let's preserve the data rather than drop it.
            if status_vars is None:
                logging.debug("edgecase. failing safe.")
                status_vars = re.search(
                    "\s*state\:\s(?P<state>.+?)$\s*(?P<status>status\:\s.+?)\s*config\:.+?errors:\s*(?P<errors_o>.+?)$",
                    status_obj, re.MULTILINE | re.DOTALL)
                logging.debug("edgecase is %s" % status_vars.group('status'))
                status_type = "edge"

            logging.debug("status_vars are %s" % status_vars.groupdict())

            timestamp = datetime.datetime.now().isoformat()
            # Mon Sep 17 07:11:42 2018
            log_obj = {'_time': timestamp, 'pool': pool_name}

            # reformat operation_date into a real timestamp
            # format like: Mon Sep 17 07:11:42 2018
            if status_type != "edge":
                status_operation_date = datetime.datetime.strptime(
                    status_vars.group('operation_date_o'), '%c').isoformat()
                log_obj['operation_date'] = status_operation_date
                logging.debug("added operation_date")

            # reformat awful data size format into plain bytes
            # input format like: 183.2G
            if (status_type == "scrub_in_progress") or (
                    status_type == "normal"):
                for group in status_vars.groupdict():
                    if "bytes_o" in group:
                        logging.debug("found bytes group '%s;, reformatting" %
                                      group)
                        bytes_obj = re.search('([0-9.]+?)([BKMGTP])',
                                              status_vars.group(group))
                        byteskey = group[:-2]
                        logging.debug("adding %s" % byteskey)
                        logging.debug("group(1) is %s" % bytes_obj.group(1))
                        logging.debug("group(2) is %s" % bytes_obj.group(2))
                        if bytes_obj.group(2) == "B":
                            log_obj[byteskey] = str(
                                int(round(float(bytes_obj.group(1)))))
                        elif bytes_obj.group(2) == "K":
                            log_obj[byteskey] = str(
                                int(round(float(bytes_obj.group(1)) * 1024)))
                        elif bytes_obj.group(2) == "M":
                            log_obj[byteskey] = str(
                                int(round(float(bytes_obj.group(1)) *
                                          1048576)))
                        elif bytes_obj.group(2) == "G":
                            log_obj[byteskey] = str(
                                int(
                                    round(
                                        float(bytes_obj.group(1)) *
                                        1073741824)))
                        elif bytes_obj.group(2) == "T":
                            log_obj[byteskey] = str(
                                int(
                                    round(
                                        float(bytes_obj.group(1)) *
                                        1099511627776)))
                        elif bytes_obj.group(2) == "P":
                            log_obj[byteskey] = str(
                                int(
                                    round(
                                        float(bytes_obj.group(1)) *
                                        1125899906842624)))

            # reformat weird zfs time span format
            # input format like: 5h7m
            if (status_type == "normal") or (
                    status_type == "resilver_in_progress"):
                logging.debug("has duration_o, reformatting")
                duration_search = re.search('(\d+?)h(\d+?)m',
                                            status_vars.group('duration_o'))
                dur_h = int(duration_search.group(1))
                dur_m = int(duration_search.group(2))
                dur_s = (dur_h * 3600) + (dur_m * 60)
                log_obj['operation_duration'] = dur_s
                logging.debug("added operation_duration")

            # reformat weird zfs time span format
            # input format like: 5h7m
            if (status_type == "resilver_in_progress") or (
                    status_type == "scrub_in_progress"):
                logging.debug("has togo_o, reformatting")
                togo_search = re.search('(\d+?)h(\d+?)m',
                                        status_vars.group('togo_o'))
                togo_h = int(togo_search.group(1))
                togo_m = int(togo_search.group(2))
                togo_s = (togo_h * 3600) + (togo_m * 60)
                log_obj['operation_togo'] = togo_s
                logging.debug("added operation_togo")

            # dump keys into log_obj dict
            logging.debug("dumping keys into log_obj")
            for item in status_vars.groupdict():
                if not item.endswith("_o"):
                    log_obj[item] = status_vars.group(item)
                    logging.debug("added %s" % item)

            # output log_obj json
            print json.dumps(OrderedDict(sorted(log_obj.items())))

    except Exception, e:
        raise Exception, "Error running zpool command with get_pools: %s" % str(
            e)


# Script must implement these args: scheme, validate-arguments
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        else:
            print "You giveth weird arguments"

    else:
        # dewit
        get_status()

    sys.exit(0)
