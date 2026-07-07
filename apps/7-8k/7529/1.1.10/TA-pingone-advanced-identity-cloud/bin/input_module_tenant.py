# encoding = utf-8
# Version 1.1.10

import os
import sys
import time
import datetime
import json

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''

# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # tenant_name = definition.parameters.get('tenant_name', None)
    # splunk_index = definition.parameters.get('splunk_index', None)
    # pingone_aic_forgerock_tenant = definition.parameters.get('pingone_aic_forgerock_tenant', None)
    # api_key_id = definition.parameters.get('api_key_id', None)
    # api_key_secret = definition.parameters.get('api_key_secret', None)
    # log_sources = definition.parameters.get('log_sources', None)
    # log_filter = definition.parameters.get('log_filter', None)
    pass


def collect_events(helper, ew):
    for stanza in helper.get_input_stanza_names():
        helper.log_info("")
        helper.log_info("===========================")
        helper.log_info("POLLING instance: " + stanza)
        helper.log_info("===========================")

        # Ensure HTTPS only
        tenant_url = helper.get_arg("tenant_url", stanza)
        if tenant_url.startswith("http://"):
            tenant_url = tenant_url.replace("http://", "https://", 1)

        # Get config for this tenant
        api_key_id = helper.get_arg("api_key_id", stanza)
        api_key_secret = helper.get_arg("api_key_secret", stanza)
        log_sources = helper.get_arg("log_sources", stanza)
        log_filter = helper.get_arg("log_filter", stanza)
        if not log_sources:
            log_sources = "am-authentication,am-access,am-config,idm-activity"

        helper.log_info("Sources: " + log_sources)
        index = helper.get_output_index(stanza)
        headers = {"x-api-key": api_key_id, "x-api-secret": api_key_secret}
        cp_key = "beginTime-" + stanza

        # Determine time of last request
        previousBeginTime = helper.get_check_point(cp_key)
        try:
            if previousBeginTime:
                datetime.datetime.strptime(previousBeginTime, "%Y-%m-%dT%H:%M:%S%z")
        except Exception:
            previousBeginTime = None

        if previousBeginTime is None:
            helper.log_info("No previous beginTime saved so backdating to 2 minutes ago")
            begin_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120)
        else:
            prev_dt = datetime.datetime.strptime(previousBeginTime, "%Y-%m-%dT%H:%M:%S%z")
            if (datetime.datetime.now(datetime.timezone.utc) - prev_dt).seconds > 3600:
                helper.log_info("Previous beginTime too old (>1h); backdating 2 minutes")
                begin_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=120)
            else:
                begin_dt = prev_dt

        end_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=60)

        helper.log_info(f"beginTime {begin_dt.isoformat()} endTime {end_dt.isoformat()}")

        had_success = False
        last_event_epoch = None
        cookie = None
        pages = 0
        max_pages = 100

        while pages < max_pages:
            pages += 1
            params = {
                "_pageSize": 1000,
                "source": log_sources,
                "beginTime": begin_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endTime": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            if cookie:
                params["_pagedResultsCookie"] = cookie
            if log_filter and log_filter.strip().lower() != "true":
                params["_queryFilter"] = log_filter

            resp = helper.send_http_request(
                tenant_url + "/monitoring/logs",
                "GET",
                parameters=params,
                headers=headers,
                verify=True,
                timeout=60,
                use_proxy=True,
            )

            if not resp or resp.status_code != 200:
                helper.log_info(f"HTTP error; not advancing checkpoint. status={getattr(resp,'status_code',None)}")
                break

            try:
                data = resp.json()
            except Exception as e:
                helper.log_info(f"JSON parse error; not advancing checkpoint. err={e}")
                break

            results = data.get("result", []) or []
            helper.log_info(f"Page={pages} resultCount={data.get('resultCount')} cookie={bool(data.get('pagedResultsCookie'))}")

            for entry in results:
                payload = entry.get("payload")
                ts = (isinstance(payload, dict) and payload.get("timestamp")) or entry.get("timestamp")
                evt_time = None
                if ts:
                    try:
                        iso = ts.replace("Z", "+00:00")
                        evt_time = datetime.datetime.fromisoformat(iso).timestamp()
                        last_event_epoch = max(last_event_epoch or 0, evt_time)
                    except Exception as e:
                        helper.log_debug(f"ts parse failed: {ts} err={e}")

                # normalize event body
                body = dict(payload) if isinstance(payload, dict) else dict(entry)
                if isinstance(payload, dict):
                    body.setdefault("timestamp", ts)

                evt = helper.new_event(
                    data=json.dumps(body, ensure_ascii=False),
                    time=evt_time,
                    index=index,
                    source=stanza,
                    sourcetype="_json",
                    done=True,
                    unbroken=True,
                )
                ew.write_event(evt)

            had_success = True
            cookie = data.get("pagedResultsCookie")
            if not cookie:
                helper.log_info("No pagedResultsCookie; all pages done")
                break

        # ----- checkpoint logic -----
        old_cp = helper.get_check_point(cp_key)
        if had_success:
            if last_event_epoch:
                new_cp = datetime.datetime.fromtimestamp(last_event_epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                helper.save_check_point(cp_key, new_cp)
                helper.log_info(f"Checkpoint advanced to last event time: {new_cp} (was {old_cp})")
            else:
                new_cp = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                helper.save_check_point(cp_key, new_cp)
                helper.log_info(f"Checkpoint advanced to end_dt: {new_cp} (was {old_cp})")
        else:
            helper.log_info(f"Keeping prior checkpoint due to error/empty response (was {old_cp})")
