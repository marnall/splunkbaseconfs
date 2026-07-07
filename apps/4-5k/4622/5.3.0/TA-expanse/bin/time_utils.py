# This regex pattern gets dates like 2020-02-19T20:42:15:832Z
import datetime
import re
import time
from decimal import Decimal

from dateutil.parser import parse

regex_date_colons = """
        (19[0-9]{2}|2[0-9]{3})
        -
        (0[1-9]|1[012])
        -
        ([123]0|[012][1-9]|31)
        T
        ([01][0-9]|2[0-3])
        :
        ([0-5][0-9])
        :
        ([0-5][0-9])
        :
        ([0-9]+)
        Z
        """
# This regex pattern gets dates like 2020-02-18T23:37:51Z
regex_date_no_ms = """
        (19[0-9]{2}|2[0-9]{3})
        -
        (0[1-9]|1[012])
        -
        ([123]0|[012][1-9]|31)
        T
        ([01][0-9]|2[0-3])
        :
        ([0-5][0-9])
        :
        ([0-5][0-9])
        Z
        """
# This regex pattern gets dates like 2020-02-18T23:37.51Z
regex_date_default = """
        (19[0-9]{2}|2[0-9]{3})
        -
        (0[1-9]|1[012])
        -
        ([123]0|[012][1-9]|31)
        T
        ([01][0-9]|2[0-3])
        :
        ([0-5][0-9])
        :
        ([0-5][0-9])
        .
        ([0-9]+)
        Z
        """


def get_splunk_time(helper, data_time):
    # We check the Flow's creation time date format that we get back from processor, and convert accordingly.
    if re.match(regex_date_colons, data_time, re.VERBOSE):
        return Decimal(datetime.datetime.strptime(data_time, "%Y-%m-%dT%H:%M:%S:%fZ").strftime('%s.%f'))
    elif re.match(regex_date_no_ms, data_time, re.VERBOSE):
        return Decimal(datetime.datetime.strptime(data_time, '%Y-%m-%dT%H:%M:%SZ').strftime('%s.%f'))
    elif re.match(regex_date_default, data_time, re.VERBOSE):
        return Decimal(datetime.datetime.strptime(data_time, "%Y-%m-%dT%H:%M:%S.%fZ").strftime('%s.%f'))
    else:
        helper.log_debug(
            'Unexpected Date Format, truncated milliseconds to ingest Flow Date: {}'.format(data_time))
        return time.mktime(parse(data_time).timetuple())
