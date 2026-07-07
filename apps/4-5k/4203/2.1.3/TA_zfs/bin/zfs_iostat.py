import json
import datetime
import subprocess
import sys
from collections import OrderedDict

# import our helpers
from zfs_helpers import *

SCHEME = """<scheme>
  <title>ZFS iostat</title>
  <description>Get data from zpool iostat command.</description>
  <endpoint>
    <args>
      <arg name="zpool_list">
        <title>Zpool List</title>
        <description>A space delimited list of one or more zpools to investigate with the zfs iostat command.
          Use ALL__POOLS to specify using all zpools returned by zpool list
        </description>
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
def get_iostat():
    try:
        pools_out = get_pools()
        logging.debug("got pools %s" % pools_out)
        for pool_name in pools_out:
            iostat_cmd = ['zpool', 'iostat', '-Hlp', pool_name]
            logging.debug("my iostat command is %s" % iostat_cmd)
            iostat_out = subprocess.Popen(
                iostat_cmd, stdout=subprocess.PIPE).stdout.read().split()
            logging.debug("iostat_out is %s" % iostat_out)
            timestamp = datetime.datetime.now().isoformat()
            if len(iostat_out) == 17:
                log_obj = {
                    '_time': timestamp,
                    'pool': pool_name,
                    'capacity_alloc_b': iostat_out[1],
                    'capacity_free_b': iostat_out[2],
                    'operations_read': iostat_out[3],
                    'operations_write': iostat_out[4],
                    'bandwidth_read_b': iostat_out[5],
                    'bandwidth_write_b': iostat_out[6],
                    'total_wait_read_ns': iostat_out[7],
                    'total_wait_write_ns': iostat_out[8],
                    'disk_wait_read_ns': iostat_out[9],
                    'disk_wait_write_ns': iostat_out[10],
                    'syncq_wait_read_ns': iostat_out[11],
                    'syncq_wait_write_ns': iostat_out[12],
                    'asyncq_wait_read_ns': iostat_out[13],
                    'asyncq_wait_write_ns': iostat_out[14],
                    'scrub_wait_ns': iostat_out[15],
                    'trim_wait_ns': iostat_out[16]
                }

                print json.dumps(OrderedDict(sorted(log_obj.items())))

            else:
                sys.exit("zpool iostat had unrecognized output")

    except Exception, e:
        raise Exception, "Error getting zpool iostat info: %s" % str(e)


# Script must implement these args: scheme, validate-arguments
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_args()
        else:
            print 'You giveth weird arguments'

    else:
        get_iostat()

sys.exit(0)
