# Copyright (C) 2022-2024 Sideview LLC.  All Rights Reserved.
import csv
import os
import json
import sys
import re
from pathlib import Path
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration

COUNT_MATCHER = re.compile(r'([^\.;]+)\.([^;]+);(\d+);')


def build_count_fields(count_string):
    collected = {}
    field_order = []
    for m in re.finditer(COUNT_MATCHER, count_string):

        category = m.group(1)
        field = m.group(2)
        value = m.group(3)
        if field not in collected:
            collected[field] = {
                "field": field
            }
        collected[field][category] = value

        if field not in field_order:
            field_order.append(field)
    out = []
    for field in field_order:
        out.append(collected[field])


    return out


@Configuration()
class CheckYourselfCommand(ReportingCommand):



    def get_job_status(self, job_dispatch_dir):
        """ gets the contents of the current job's status.csv file and returns it as a
        flat dictionary. """
        csv_path = os.path.join(job_dispatch_dir, "status.csv")
        with open(csv_path, 'r') as csv_handle:
            csv_dict_reader = csv.DictReader(csv_handle)
            for reader_row in csv_dict_reader:
                row = {}
                for field in reader_row:
                    row[field] = reader_row[field]
                return row

    def get_job_counts(self, job_dispatch_dir):
        csv_path = os.path.join(job_dispatch_dir, "info.csv")
        with open(csv_path, 'r') as csv_handle:
            csv_dict_reader = csv.DictReader(csv_handle)
            for reader_row in csv_dict_reader:
                #return reader_row["_countMap"]
                return build_count_fields(reader_row["_countMap"])


    @Configuration()
    def map(self, records):
        """ This may be the wrong way to do this, but for now it's a ReportingCommand
        that should only ever run at SH."""
        return records

    def reduce(self, records):
        output = {}
        # there's a deprecation warning to use metadata instead of input_header, but a brief
        # stick-poking hits an inconvenience that metadata is not iterable.
        header = self.input_header
        for key in header:
            output[key] = header[key]

        job_dispatch_dir = Path(header["infoPath"]).parent
        status_dict = self.get_job_status(job_dispatch_dir)
        for key in status_dict:
            output[key] = status_dict[key]

        countMaps = self.get_job_counts(job_dispatch_dir)
        output["counts"] = countMaps

        yield output


if __name__ == "__main__":
    dispatch(CheckYourselfCommand, sys.argv, sys.stdin, sys.stdout, __name__)
