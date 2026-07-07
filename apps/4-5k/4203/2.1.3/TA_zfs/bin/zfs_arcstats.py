import json
import datetime
import re
import sys
from collections import OrderedDict

# import our helpers
from zfs_helpers import *

SCHEME = """<scheme>
  <title>ZFS arcstat</title>
  <description>Get data from zfs arcstat output.</description>
  <use_external_validation>false</use_external_validation>
  <streaming_mode>simple</streaming_mode>

  <endpoint>
    <args>
      <arg name="filter">
        <title>Output Filter</title>
        <description>A regex filter (inclusive) to apply to the statistics from arcstat. Think a grep filter, eg. '^l2*' for all values that start with "l2"</description>
        <required_on_create>true</required_on_create>
        <validation>
          validate(isstr('filter'),"filter is not a string")
        </validation>
      </arg>
    </args>
  </endpoint>
</scheme>
"""


def do_scheme():
    print SCHEME


# Routine to get the value of an input
def get_arcstats():
    try:
        config = get_config()
        input_filter = config["filter"]
        timestamp = datetime.datetime.now().isoformat()

        log_obj = {'_time': timestamp}

        with open("/proc/spl/kstat/zfs/arcstats", "rb") as arcstats:
            line = arcstats.readline()
            while line:
                arc_compile = re.compile("^(\w+)\s+\d\s+(\d+)")
                arc_groups = arc_compile.findall(line)
                line = arcstats.readline()

                for k, v in arc_groups:
                    if k != "13" and k != "name":
                        if input_filter != "ALL__STATS":
                            match = re.search(input_filter, k)
                            if match:
                                log_obj.update({k: v})
                        else:
                            log_obj.update({k: v})
        print json.dumps(OrderedDict(sorted(log_obj.items())))

    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(
            e)


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
        get_arcstats()

sys.exit(0)
