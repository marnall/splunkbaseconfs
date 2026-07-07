# Copyright 2016 Farsight Security, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging as logger
import traceback

from IPy import IP
import splunk.Intersplunk

def is_valid_ip(ip):
    try:
        ip = IP(ip)
    except (ValueError, TypeError):
        return False
    else:
        return True

try:
    input_events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    output_events = []

    ip = options.get("ip", "")
    is_valid = str(is_valid_ip(ip))
    output_events = [ {"is_valid": is_valid} ]

    splunk.Intersplunk.outputResults(output_events)

except Exception as e:
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
