# File: rsasecureidam_consts.py
#
# Copyright (c) 2023-2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.


RSA_RUN_COMMAND = (
    "./rsautil AMBulkAdmin -a {username} -P {password} --ctkip -i {input_file}"
    " -r {output_results_file} --o {output_log_file} --rej {output_reject_file} --newlog"
)

RSA_HEADER_LINE = "Action,TokSerial,TokEnabled\n"
RSA_LIST_TOKEN_HEADER_LINE = "Action,CompareField,CompareType\n"

RSA_ENABLE_TOKEN_QUERY = "CTS,{token},1\n"
RSA_REVOKE_TOKEN_QUERY = "CTS,{token},0\n"
RSA_LIST_TOKENS_QUERY = "LTIF,{compare_field},{compare_type}\n"

RSA_COMMAND_PATH = "cd /opt/rsa/am/utils\n"

RSA_TEST_CONNECTIVITY_SUCCESS = "Test Connectivity Passed"
RSA_TEST_CONNECTIVITY_FAIL = "Test Connectivity Failed"
RSA_TOKEN_ENABLE_MESSAGE = "Token has been successfully enabled!"
RSA_TOKEN_REVOKE_MESSAGE = "Token has been successfully disabled!"
