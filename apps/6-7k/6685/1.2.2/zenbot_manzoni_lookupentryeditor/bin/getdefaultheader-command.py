#!/usr/bin/env python

from asyncore import file_dispatcher
import sys, os, re, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration()
class GetdefaultheaderCommand(GeneratingCommand):
    csv_file = Option(require=True)

    def generate(self):
        regex = r"__mv_"
        try:
            with open(os.path.join(self.csv_file),'r') as f:
                column_list = f.readline().strip().split(",")
                filtered_column = [column for column in column_list if not re.search(regex, column)]
                filtered_column = ",".join(filtered_column)

                return [{"_time": time.time(), "header": filtered_column}]
        except:
            return [{"_time": time.time(), "header": None}]
       


dispatch(GetdefaultheaderCommand, sys.argv, sys.stdin, sys.stdout, __name__)