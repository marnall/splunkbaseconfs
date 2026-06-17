# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.
"""
This implements a custom search command that will read the user-configurable
"call_quality_thresholds.csv" file from the app's lookup directory and use the information in there to
apply quality-of-service thresholds to any of the matching quality fields that the command sees in
the events it processes.
When there are one or more matches it then outputs a "quality" field with a value of either good,
acceptable, fair or poor.  If the organization has actual service-levels that they must meet, they
can simply enter those exact thresholds into the lookup and thus get a report of "distinct count of
calls over call quality" and that will be their canonical report of calls that met/missed required quality.
"""

import os
import sys
import csv
import traceback
import logging

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration #, Option, validators

SPLUNK_HOME = os.environ['SPLUNK_HOME']
APP = "cisco_cdr"

# for now we are forced to hardcode these because they have an implicit ordering, and the ordering
# matters to the logic, so we can return the "worst" one when there are several matches.
QOS_LEVELS = {"good":4, "acceptable":3, "fair":2, "poor":1}


def get_quality_thresholds():
    """ the config for these customer-defined threshold is actually a
    lookup file"""


    # we dont use abspath because we might be running on SH, or we might be running on the searchpeers.
    # if we're on the peers, this script will be deep within /var/run/searchpeers, eg:
    #/var/run/searchpeers/crumble-1638396912/apps/cisco_cdr/lookups
    # so we just quietly traverse up and over, and our lookup will be there.
    csv_path = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..', "lookups","call_quality_thresholds.csv"))

    csv_handle = None
    custom = []


    with open(csv_path, 'r') as csv_handle:
        csv_dict_reader = csv.DictReader(csv_handle)
        for reader_row in csv_dict_reader:
            row = {}
            for field in reader_row:
                row[field] = reader_row[field]
            custom.append(row)
    return custom


def in_range(x, min_value, max_value):
    """ returns true if x is between the two specified values """
    if min_value and max_value:
        return x >= float(min_value) and ((x < float(max_value)) or (max_value == "Infinity"))
    return False

class IllegalCallQualityName(KeyError):
    pass

@Configuration()
class CallQualityCommand(StreamingCommand):
    """ pylint is our friend. But sometimes it tests our friendship. """
    thresholds = get_quality_thresholds()

    """
    # if someday this command needs arguments, here is how you set them:
    myFirstArgument = Option(
        doc='''
        **Syntax:** **fieldname=***<fieldname>*
        **Description:** There were a hundred and sixty of us living in a small shoebox in the middle of the road.''',
        require=True, validate=validators.Fieldname())
    """
    def prepare(self):
        self.configuration.required_fields = [
            "CCR",
            "CS",
            "CS_total",
            "CSR_overall",
            "ICR",
            "ICRmx",
            "jitter",
            "latency",
            "MLQK",
            "MLQKav",
            "numberPacketsSent",
            "numberPacketsLost",
            "SCS",
            "SCS_total",
            "SCSR_overall"
        ]


    def stream(self, records):

        for record in records:
            self.process_line(record)
            yield record


    def process_line(self, result):
        """ the actual worker who inspects the given row"""

        lowest_level_matched = 10
        quality = None

        try:
            for row in self.thresholds:

                #try and fail slightly more gracefully than just an generic traceback.
                if row["quality"] not in QOS_LEVELS:
                    raise IllegalCallQualityName("Error - there is an illegal quality value specified in call_quality_thresholds -- \"%s\"" % row["quality"])
                # skip rules that are for quality level that we're already worse than.
                if QOS_LEVELS[row["quality"]] > lowest_level_matched:
                    continue

                metric = row["field"]
                if metric != "lostPacketsPercent" and metric not in self.configuration.required_fields:
                    exc_string = "the \"%s\" field in call_quality_thresholds is not listed as a required field for the call_quality search command." % metric
                    if not metric:
                        exc_string = "there appears to be a row in call_quality_thresholds that has a blank value for the field."
                    raise Exception("Error - " + exc_string)

                if metric == "lostPacketsPercent":
                    if "numberPacketsSent" not in result or "numberPacketsLost" not in result:
                        continue
                    if not result["numberPacketsSent"].isdigit() or not result["numberPacketsLost"].isdigit():
                        continue
                    packets_sent = float(result["numberPacketsSent"])
                    packets_lost = float(result["numberPacketsLost"])
                    if packets_sent > 0:
                        value = str(100 * (packets_lost / packets_sent))
                    else:
                        value = 0
                else:
                    value = result[metric]

                # skip rows that aren't integers or floats.
                if not str(value).replace('.', '', 1).isdigit():
                    continue

                if in_range(float(value), row["min"], row["max"]):
                    quality = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]

            result["quality"] = quality

        except IllegalCallQualityName as e:
            # str(e) looks much better but has a lame side effect of wrapping it in single quotes.
            raise KeyError(e.args[0])
        except Exception as e:
            result["quality"] = traceback.format_exc()

dispatch(CallQualityCommand, sys.argv, sys.stdin, sys.stdout, __name__)
