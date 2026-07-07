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
import json
import logging as logger
import sys
import re
import time
import traceback
import os
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", APP_ID, "lib"))

import dnsdb2
from IPy import IP
import splunk.Intersplunk
from splunklib.client import connect
from splunklib.binding import HTTPError
from common import get_credentials, get_client_info
from dt_logger import DTLogger
from dt_api_wrapper import DtApiWrapper
from utils import get_proxy


def cache_read(
    queryType,
    session_key,
    rrType,
    target,
    time_first_before,
    time_first_after,
    time_last_before,
    time_last_after,
):
    """
    Reads data from Splunk KV store
    """
    service = connect(token=session_key, owner="nobody", app=APP_ID)
    collection = service.kvstore["dt_%s_kvstore" % queryType]
    key = (
        target
        + "-"
        + str(rrType)
        + "-"
        + time_first_before
        + "-"
        + time_first_after
        + "-"
        + time_last_before
        + "-"
        + time_last_after
    )
    try:
        data = collection.data.query_by_id(key)
        return data
    except HTTPError as http_error:
        if http_error.status == 404:
            raise KeyError


def cache_insert(
    queryType,
    session_key,
    rrType,
    target,
    output,
    time_first_before,
    time_first_after,
    time_last_before,
    time_last_after,
):
    """
    Inserts data into Splunk KV store
    """
    timestamp = calendar.timegm(time.gmtime())
    service = connect(token=session_key, owner="nobody", app=APP_ID)
    key = (
        target
        + "-"
        + str(rrType)
        + "-"
        + time_first_before
        + "-"
        + time_first_after
        + "-"
        + time_last_before
        + "-"
        + time_last_after
    )
    data = {"output": output, "cache_time": timestamp}

    collection = service.kvstore["dt_%s_kvstore" % queryType]
    if isinstance(data, list):
        collection.data.batch_save(*data)
    elif isinstance(data, dict):
        data["_key"] = str(key)
        try:
            collection.data.insert(json.dumps(data))
        except HTTPError as http_error:
            # If item with this ID already exists, update it.
            if http_error.status == 409:
                collection.data.update(key, json.dumps(data))


def is_valid_ip(ip):
    try:
        ip = IP(ip)
    except (ValueError, TypeError):
        return False
    else:
        return True


def is_raw_rdata(raw):
    if re.match(r"^[a-fA-F0-9]+$", raw) and (len(raw) % 2) == 0:
        return True
    return False


def run_query(
    dnsdb,
    target,
    req_type,
    rrtype,
    bailiwick,
    time_first_before,
    time_first_after,
    time_last_before,
    time_last_after,
    target_type="auto",
):
    timestamps = [
        time_first_before,
        time_first_after,
        time_last_before,
        time_last_after,
    ]
    for i, timestamp in enumerate(timestamps):
        try:
            timestamps[i] = int(
                time.mktime(time.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ"))
            )
        except ValueError:
            pass
        except TypeError:
            pass
    # Final parsed time inputs
    p_time_first_before = timestamps[0]
    p_time_first_after = timestamps[1]
    p_time_last_before = timestamps[2]
    p_time_last_after = timestamps[3]
    if req_type:
        req_type = req_type.lower()
    else:
        req_type = "rdata"
    try:
        if target_type == "auto":
            if req_type == "rrset":
                response = list(
                    dnsdb.lookup_rrset(
                        target,
                        rrtype=rrtype,
                        bailiwick=bailiwick,
                        time_first_before=p_time_first_before,
                        time_first_after=p_time_first_after,
                        time_last_before=p_time_last_before,
                        time_last_after=p_time_last_after,
                        ignore_limited=True,
                    )
                )
            elif req_type == "rdata":
                if is_valid_ip(target):
                    response = list(
                        dnsdb.lookup_rdata_ip(
                            target,
                            rrtype=rrtype,
                            time_first_before=p_time_first_before,
                            time_first_after=p_time_first_after,
                            time_last_before=p_time_last_before,
                            time_last_after=p_time_last_after,
                            ignore_limited=True,
                        )
                    )
                elif is_raw_rdata(target):
                    response = list(
                        dnsdb.lookup_rdata_raw(
                            target,
                            rrtype=rrtype,
                            time_first_before=p_time_first_before,
                            time_first_after=p_time_first_after,
                            time_last_before=p_time_last_before,
                            time_last_after=p_time_last_after,
                            ignore_limited=True,
                        )
                    )
                else:
                    response = list(
                        dnsdb.lookup_rdata_name(
                            target,
                            rrtype=rrtype,
                            time_first_before=p_time_first_before,
                            time_first_after=p_time_first_after,
                            time_last_before=p_time_last_before,
                            time_last_after=p_time_last_after,
                            ignore_limited=True,
                        )
                    )
            else:
                raise Exception("Unknown type: " + str(req_type))
        else:
            if req_type == "rrset":
                if target_type != "name":
                    raise Exception("rrset lookup only supports target type of rrset")
                response = list(
                    dnsdb.lookup_rrset(
                        target,
                        rrtype=rrtype,
                        bailiwick=bailiwick,
                        time_first_before=p_time_first_before,
                        time_first_after=p_time_first_after,
                        time_last_before=p_time_last_before,
                        time_last_after=p_time_last_after,
                        ignore_limited=True,
                    )
                )
            elif req_type == "rdata":
                if target_type == "ip":
                    response = list(
                        dnsdb.lookup_rdata_ip(
                            target,
                            rrtype=rrtype,
                            bailiwick=bailiwick,
                            time_first_before=p_time_first_before,
                            time_first_after=p_time_first_after,
                            time_last_before=p_time_last_before,
                            time_last_after=p_time_last_after,
                            ignore_limited=True,
                        )
                    )
                elif target_type == "raw":
                    response = list(
                        dnsdb.lookup_rdata_raw(
                            target,
                            rrtype=rrtype,
                            time_first_before=p_time_first_before,
                            time_first_after=p_time_first_after,
                            time_last_before=p_time_last_before,
                            time_last_after=p_time_last_after,
                            ignore_limited=True,
                        )
                    )
                else:
                    response = list(
                        dnsdb.lookup_rdata_name(
                            target,
                            rrtype=rrtype,
                            bailiwick=bailiwick,
                            time_first_before=p_time_first_before,
                            time_first_after=p_time_first_after,
                            time_last_before=p_time_last_before,
                            time_last_after=p_time_last_after,
                            ignore_limited=True,
                        )
                    )

    except dnsdb2.QueryError as e:
        raise Exception("Server returned query error: %s" % str(e))
    except dnsdb2.QueryFailed as e:
        raise Exception("Server encountered an error while running query: %s" % str(e))
    except dnsdb2.QueryLimited as e:
        # With ignore_limited=True we should never see this
        raise Exception("Result limit reached")
    except dnsdb2.QueryTruncated as e:
        raise Exception(
            "Query results are incomplete due to a server error: %s" % str(e)
        )
    except dnsdb2.QuotaExceeded as e:
        raise Exception("Query quota for this API key has been reached.")
    except dnsdb2.AccessDenied as e:
        raise Exception("Authorization failed. Check API key")
    except dnsdb2.ConcurrencyExceeded as e:
        raise Exception("Number of concurrent connections has exceeded your limit.")
    except dnsdb2.ProtocolError as e:
        raise Exception(
            "Invalid data is received via the Streaming Application Framework: %s"
            % str(e)
        )
    except Exception as e:
        raise Exception(
            f"Oops, we have hit a snag. If this error persists, please contact DomainTools support. Error: {str(e)}"
        )
    return response


def main():
    try:
        input_events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        dt_log = DTLogger(
            "dnsdb",
            os.path.basename(__file__),
            settings.get("owner", "unknown"),
            "dnsdb",
        )
        keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        output_events = []
        sessionKey = settings["sessionKey"]
        target = options.get("target", "")
        target.replace("/", ",")
        req_type = options.get("type", "rrset")
        bailiwick = options.get("bailiwick", None)
        time_first_before = options.get("time_first_before", None)
        time_first_after = options.get("time_first_after", None)
        time_last_before = options.get("time_last_before", None)
        time_last_after = options.get("time_last_after", None)
        rrtype = options.get("rrtype", None)
        if not target:
            error = splunk.Intersplunk.generateErrorResults(
                "Usage: | dtdnsdb target=ip/hostname "
                "type=rdata/rrset/raw [rrtype=**A/MX/CNAME/etc] [bailiwick=bailiwick]"
                "[time_first_before=time] [time_first_after=time] [time_last_before=time] [time_last_after=time]"
            )
            splunk.Intersplunk.outputResults(error)
            sys.exit()

        # Special case for all-time searches
        if str(time_last_after) == "0":
            time_last_after = None
            time_first_before = None

        # Deal with dashboard sending "now" as a time
        if str(time_first_before) == "now":
            time_first_before = None

        # Deal with dashboard sending "" as a time
        if str(time_last_before) == "":
            time_last_before = None
        if str(time_first_after) == "":
            time_first_after = None

        if rrtype is not None:
            rrtype = rrtype.lower()
        if rrtype == "*":
            rrtype = None

        if req_type != None:
            req_type = req_type.lower()

        # dnsdb refuses rdata requests for any-dnssec
        if req_type == "rdata" and rrtype == "any-dnssec":
            splunk.Intersplunk.outputResults([])
            sys.exit()

        apikey = get_credentials(sessionKey)
        swclient, version = get_client_info(sessionKey)
        proxy = get_proxy(sessionKey)

        if not apikey:
            splunk.Intersplunk.generateErrorResults(
                "No API key found. Configure the DomainTools App before running this command"
            )
            sys.exit()

        if proxy != "":
            dnsdb = dnsdb2.Client(
                apikey,
                swclient=swclient,
                version=version,
                proxies={"https": proxy, "http": proxy},
            )
        else:
            dnsdb = dnsdb2.Client(apikey, swclient=swclient, version=version)

        # KV Store caching
        try:
            cache_results = cache_read(
                req_type,
                sessionKey,
                rrtype,
                target,
                str(time_first_before),
                str(time_first_after),
                str(time_last_before),
                str(time_last_after),
            )
        except KeyError:
            output_events = run_query(
                dnsdb,
                target,
                req_type,
                rrtype,
                bailiwick,
                time_first_before,
                time_first_after,
                time_last_before,
                time_last_after,
            )

            cache_insert(
                req_type,
                sessionKey,
                rrtype,
                target,
                output_events,
                str(time_first_before),
                str(time_first_after),
                str(time_last_before),
                str(time_last_after),
            )
        else:
            if (
                calendar.timegm(time.gmtime()) - int(cache_results["cache_time"])
                > 86400
            ):
                output_events = run_query(
                    dnsdb,
                    target,
                    req_type,
                    rrtype,
                    bailiwick,
                    time_first_before,
                    time_first_after,
                    time_last_before,
                    time_last_after,
                )
                cache_insert(
                    req_type,
                    sessionKey,
                    rrtype,
                    target,
                    output_events,
                    str(time_first_before),
                    str(time_first_after),
                    str(time_last_before),
                    str(time_last_after),
                )
            else:
                output_events = cache_results["output"]

        splunk.Intersplunk.outputResults(output_events)

    except Exception as e:
        stack = traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))
        logger.error(str(e) + ". Traceback: " + str(stack))


if __name__ == "__main__":
    main()
