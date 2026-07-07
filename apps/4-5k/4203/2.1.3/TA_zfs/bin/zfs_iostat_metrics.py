import csv
import datetime
import subprocess
import sys

# Import our helpers
from zfs_helpers import *

SCHEME = """<scheme>
  <title>ZFS iostat metrics</title>
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

        for pool_name in pools_out:
            iostat_cmd = ['zpool', 'iostat', '-Hlp', pool_name]
            iostat_out = subprocess.Popen(
                iostat_cmd,
                stdout=subprocess.PIPE).stdout.read().replace(' - ',
                                                              ' 0 ').split()
            timestamp = datetime.datetime.now().strftime('%s')

            if len(iostat_out) == 17:
                log_obj = [[
                    'metric_timestamp', 'metric_name', '_value',
                    'process_object_guid'
                ],
                           [
                               timestamp, 'zfs.iostat.capacity_alloc_b',
                               iostat_out[1], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.capacity_free_b',
                               iostat_out[2], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.operations_read',
                               iostat_out[3], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.operations_write',
                               iostat_out[4], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.bandwidth_read_b',
                               iostat_out[5], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.bandwidth_write_b',
                               iostat_out[6], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.total_wait_read_ns',
                               iostat_out[7], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.total_wait_write_ns',
                               iostat_out[8], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.disk_wait_read_ns',
                               iostat_out[9], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.disk_wait_write_ns',
                               iostat_out[10], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.syncq_wait_read_ns',
                               iostat_out[11], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.syncq_wait_write_ns',
                               iostat_out[12], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.asyncq_wait_read_ns',
                               iostat_out[13], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.asyncq_wait_write_ns',
                               iostat_out[14], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.scrub_wait_ns',
                               iostat_out[15], pool_name
                           ],
                           [
                               timestamp, 'zfs.iostat.trim_wait_ns',
                               iostat_out[16], pool_name
                           ]]
                writer = csv.writer(sys.stdout)
                writer.writerows(log_obj)

            else:
                sys.exit("zpool iostat had unrecognized output")

    except Exception, e:
        raise Exception, "Error getting zpool iostat: %s" % str(e)


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
        # dewit
        get_iostat()

    sys.exit(0)
