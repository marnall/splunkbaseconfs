#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import os

# Extrenal libraries to ASDL inputs
import sys

cur_dir = os.path.dirname(os.path.abspath(__file__))
new_path = os.path.join(cur_dir, "../lib/ASDL_lib")
sys.path.append(new_path)

import exec_anaconda

exec_anaconda.exec_anaconda()
# sys.path.append(os.environ.get("SPLUNK_HOME")+ "/lib/python3.7/site-packages")
sys.path.insert(0, os.path.join(cur_dir, "../lib/py3.8"))
import pandas
import pyarrow

"""
Runs module for AWS SQS Based S3 inputs.
"""
from aws_bootstrap_env import run_module

if __name__ == "__main__":
    run_module("splunk_ta_aws.modinputs.sqs_based_s3")
