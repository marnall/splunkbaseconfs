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

import calendar
import logging as logger
import time
import traceback
import os
import sys
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)

import splunk.Intersplunk
from splunklib.client import connect


def cache_delete(session_key, collection):
    """
        Deletes data from Splunk KV store
    """
    service = connect(token=session_key, owner='nobody', app=APP_ID)
    collection = service.kvstore[collection]
    timestamp_yesterday = calendar.timegm(time.gmtime()) - 86400
    collection.data.delete(query='{ "cache_time": { "$lt": %s } }' % str(timestamp_yesterday))


try:
    settings = dict()
    records = splunk.Intersplunk.readResults(settings=settings, has_header=True)
    out = []
    session_key = settings['sessionKey']
    cache_delete(session_key, "dt_rrset_kvstore")
    cache_delete(session_key, "dt_rdata_kvstore")

    out.append({"result": "success"})

    splunk.Intersplunk.outputResults(out)

except Exception as e:
    stack = traceback.format_exc()
    splunk.Intersplunk.generateErrorResults(str(e))
    logger.error(str(e) + ". Traceback: " + str(stack))
