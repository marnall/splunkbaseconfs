# Copyright (C) 2010-2025 Sideview LLC.  All Rights Reserved.


"""
An adapter that takes CSV as input, performs a lookup to some external system,
then returns the CSV results
"""

# this serves absolutely no purpose in this code, which is py2/py3 compatible without it but the
# stupid PURA app fails us if we dont' do this.
from io import open


import csv
import sys

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


QOS_LEVELS = {"good":4, "acceptable":3, "fair":2, "poor":1}

def get_reference_file():
    """ the config for these customer-defined threshold is actually a
    lookup file"""
    csv_path = make_splunkhome_path(["etc", "apps", "cisco_cdr", "lookups", "call_quality_thresholds.csv"])

    csv_handle = None
    custom = []

    try:
        csv_handle = open(csv_path, 'rU')

        csv_dict_reader = csv.DictReader(csv_handle)

        for reader_row in csv_dict_reader:
            row = {}
            for field in reader_row:
                row[field] = reader_row[field]

            custom.append(row)
    except Exception as e:
        return custom, str(e)

    finally:

        # Close the file
        if csv_handle is not None:
            csv_handle.close()

    return custom, None



def in_range(x, min_value, max_value):
    """ returns true if x is between the two specified values """
    if min_value and max_value:
        return x >= float(min_value) and ((x < float(max_value)) or (max_value == "Infinity"))
    return False


def process_line(result, reference):
    """ the actual worker who inspects the given row"""
    result["quality"] = "N/A"

    packets_sent = float(result["numberPacketsSent"])
    if packets_sent > 0:
        lost_packets_percent = 100 * (float(result["numberPacketsLost"]) / packets_sent)
    else:
        lost_packets_percent = 0


    lowest_level_matched = 10

    try:
        for row in reference:
            if QOS_LEVELS[row["quality"]] > lowest_level_matched:
                continue

            if "jitterMin" in row and "jitterMax" in row:
                if in_range(float(result["jitter"]), row["jitterMin"], row["jitterMax"]):
                    result["quality"] = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]
            if "latencyMin" in row and "latencyMax" in row:
                if in_range(float(result["latency"]), row["latencyMin"], row["latencyMax"]):
                    result["quality"] = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]
            if "lostPacketsPercentMin" in row and "lostPacketsPercentMax" in row:
                if in_range(lost_packets_percent, row["lostPacketsPercentMin"], row["lostPacketsPercentMax"]):
                    result["quality"] = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]

            if "MLQKMin" in row and "MLQKMax" in row:
                if in_range(float(result["MLQK"]), row["MLQKMin"], row["MLQKMax"]):
                    result["quality"] = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]

            # CS and SCS scores should use different thresholds by length of call
            if "CSR_overallMin" in row and "CSR_overallMax" in row:
                if in_range(float(result["CSR_overall"]), row["CSR_overallMin"], row["CSR_overallMax"]):
                    result["quality"] = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]

            if "SCSR_overallMin" in row and "SCSR_overallMax" in row:
                if in_range(float(result["SCSR_overall"]), row["SCSR_overallMin"], row["SCSR_overallMax"]):
                    result["quality"] = row["quality"]
                    lowest_level_matched = QOS_LEVELS[row["quality"]]


    except Exception as e:
        result["quality"] = str(e)





def main():

    r = csv.reader(sys.stdin)
    w = None
    header = []
    first = True
    reference = {}

    errors = []
    try:
        reference, inner_exception = get_reference_file()
        errors.append(str(inner_exception))
    except Exception as e:
        errors.append(str(e))

    for line in r:
        if first:
            header = line

            header.append("quality")
            csv.writer(sys.stdout).writerow(header)
            w = csv.DictWriter(sys.stdout, header)
            first = False
            continue

        # Read the result
        result = {}
        i = 0
        while i < len(header):
            if i < len(line):
                result[header[i]] = line[i]
            else:
                result[header[i]] = ''
            i += 1
        process_line(result, reference)
        #result["quality"] = ",".join(errors)


        w.writerow(result)

main()
