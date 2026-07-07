# Copyright 2014-2025 Sideview, LLC. all rights reserved

# this is actually unnecessary since all of our print() usage passes a single var but we need this
# or else the lame PURA app says we dont run in python3.
from __future__ import print_function

import csv
import time
import os
import shutil
import sys
import json
import traceback
import getopt
from namifier import Namifier

PATH = "/home/nick/sideview/logs/oracle_sbc/oracle-cdr-07202023.txt"
ENCODING = "ISO-8859-1"


def execute():

    namifier = Namifier()





    with open(PATH, 'r+', encoding=ENCODING) as old_file:
        anonymized_file_path = os.path.join(os.path.dirname(PATH), "exact_same_file_rn_lol.txt")

        with open(anonymized_file_path, 'w+', newline="") as new_file:

            for line in old_file:

                #the challenge is to iterate over all of the sip addresses like
                # "<sip:12345678@100.101.102.103>"
                # and map each of the numbers to another unique number stably
                # and map each of the IP's to another IP stably.

                new_file.write(line)





if __name__ == '__main__':
    execute()
