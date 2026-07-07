"""
Written by Kyle Smith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
import json

# - VMware Live Query Inputs
#     - Use this tab to configure inputs that will pull the results of a previously executed LiveQuery job.
#     - Ref:
#     - ``Name``: The generic name this input should be named.
#     - ``Disabled``: This is a checkbox if the input is disabled.
#     - ``API Token``: The API Configuration API Key to use for the API authorization.
#     - ``Proxy``: The proxy configuration, if needed.
#     - ``Lookback (days)``: The number of historical days to pull from the API.
#     - ``Index``: The Splunk Index in which to store the data
#     - ``Interval``: The frequency (in seconds) that the API should poll for data. Range: 60-86400
#     - ``Result Query``: This will filter the jobs to ones that match this string.

import logging as logger
import math
import sys
import re
import os
import multiprocessing.dummy as mp
import uuid
from datetime import datetime, timedelta
from VMWUtilities import KennyLoggins
from vmware_cbc_client import VmwareCBCModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import vmware_paths
from cbc_sdk.audit_remediation import Result, RunHistory

__app_name__ = vmware_paths.__app_name__
__author__ = "ksmith"
_MI__app_name__ = "VMWare Security Audit Logs Modular Input"
_SPLUNK_HOME = make_splunkhome_path([""])

kl = KennyLoggins()
log = kl.get_logger(__app_name__, "vmware-cbc-livequery-modularinput", logger.INFO)


class VmwareCBCLiveQueryModularInput(VmwareCBCModularInput):
    def __init__(self, **kwargs):
        VmwareCBCModularInput.__init__(self, **kwargs)

    def _get_livequery_threaded(self, num, x, id_lookup):
        try:
            livequery = self._process_evt_ips(x.get("_info", "{}"))
            self.dbg(
                action="found_livequery",
                function="threaded",
                result_num=num,
                id=livequery.get("id"),
                livequery_dict=list(livequery.keys()),
            )
            self.print_event(json.dumps(livequery), time_field="time_received")
        except Exception as e:
            self._catch_error(e)
            raise e

    def get_live_query(self, run_id):
        # https://developer.carbonblack.com/reference/carbon-black-cloud/cb-liveops/latest/livequery-api/
        try:
            self.log.debug("action=start get_live_query")
            if not self._set_lock(run_id):
                self.fatal(action="set_lock", run_id=run_id, message="set_lock failed")
                return
            oldst = self.sourcetype()
            tenant = self.get_config("tenant")
            chkpnt_name = "tnt-{}_org-{}_livequery.txt".format(
                tenant.get("guid"), tenant.get("org_key")
            )
            lb = self.get_config("lookback")
            self.log.debug(
                "action=evaluating_lookback lookback={} lookback_type={}".format(
                    lb, type(lb)
                )
            )
            if int(lb) > 0:
                self.log.debug(
                    "action=evaluating_lookback new_lookback={}".format(
                        (int(lb) * 1440)
                    )
                )
                self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
            chkpnt = self.get_checkpoint(chkpnt_name)
            self.sourcetype("vmware:cbc:livequery:run")
            self.log.warning("checkpoint={}".format(chkpnt))
            chkpnt_start_time = datetime.utcfromtimestamp(chkpnt)
            chkpnt_now_time = datetime.utcnow()
            time_diff = (chkpnt_now_time - chkpnt_start_time).total_seconds()
            one_week_ago_from_checkpoint = chkpnt_now_time - timedelta(days=7)
            if time_diff > 86000:  # Just shy of 24 hours.
                original_start = chkpnt_start_time
                chkpnt_start_time = chkpnt_now_time - timedelta(hours=18)
                self.warn(
                    action="resetting_checkpoint_start",
                    time_diff=time_diff,
                    original_start=original_start,
                    new_start=chkpnt_start_time,
                    end=chkpnt_now_time,
                )
            start = "{}Z".format(chkpnt_start_time.isoformat())
            end = "{}Z".format(chkpnt_now_time.isoformat())
            result_query = "{}".format(self.get_config("result_query", f"*"))
            self.log.info(
                "action=calling_livequery_run_submit_query status=start "
                "start={} start_type={} end={} end_type={} difference={} "
                "checkpoint={} result_query=\"{}\"".format(
                    start, type(start), end, type(end), time_diff, chkpnt,
                    result_query
                )
            )

            date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
            try:
                date_format_start = datetime.strptime(start, date_format)
            except ValueError as ve:
                self.log.debug(f"action=value_error exception={ve} start={start}")
                date_format_start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ")
            livequery_history = []
            save_anyway = False
            error_code_api = 0
            save_anyway_codes = [419]
            livequery_scroller = None
            livequery_history_lookup = {"aa": {}, "k": []}
            row_limit_history = 10000
            max_scroll_rows = self.get_config("max_scroll_rows", 10000)
            try:
                livequery_history = list(
                    self.cb.select(RunHistory, rows=row_limit_history)
                    .where(result_query)
                    .sort_by("CREATE_TIME", "DESC")
                    .all()
                )
                original_history_length = len(livequery_history)

                # ADD IN A FILTER TO ONLY USE LAST 7 DAYS based on create time : one_week_ago_from_checkpoint
                # "create_time": "2022-11-28T14:15:00.000Z"
                # datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%f%z'))

                def _validate_livequery_history(lqh):
                    ct = datetime.strptime(lqh.get("create_time"), '%Y-%m-%dT%H:%M:%S.%fZ')
                    ret = ct.timestamp() >= one_week_ago_from_checkpoint.timestamp()
                    self.dbg(action="scroll_results", one_week_ago_from_checkpoint=one_week_ago_from_checkpoint,
                             week_ago_ts=one_week_ago_from_checkpoint.timestamp(),
                             create_ts=ct.timestamp(),
                             create_time=ct, id=lqh.get("id"), test_result=ret)
                    return ret

                livequery_history_lookup["aa"] = {
                    x.get("id"): {
                        "name": x.get("name"),
                        "total_result_count": x.get("total_results"),
                    }
                    for x in livequery_history if _validate_livequery_history(x)
                }
                livequery_history_lookup["k"] = list(
                    livequery_history_lookup["aa"].keys()
                )
                # livequery_history_lookup["k"] = [f"{x}" for x in range(5000)]
                history_length = len(livequery_history_lookup["k"])

                # This is to try and auto-prevent issues with data ingestion and 504 timeouts.
                if history_length < 1000:
                    # If history is < 1000, let's use configured or the default limit of 10000, it should be ok.
                    max_scroll_rows = self.get_config("max_scroll_rows", 10000)
                else:
                    # 10000 / 10000 * 1000 = 1000 at the lowest. This assumes the limit of the RunHistory is reached.
                    # 10000 / 1000 * 1000 = 10000 at the highest. This assumes at least 1000 RunHistory.
                    max_scroll_rows = math.floor(row_limit_history / history_length) * 1000

                self.dbg(
                    action="scroll_results",
                    start=start,
                    end=end,
                    result_query=result_query,
                    lookback=lb,
                    history_length=history_length,
                    original_history_length=original_history_length,
                    row_limit_history=row_limit_history,
                    checkpoint=chkpnt,
                    max_scroll_rows=max_scroll_rows,
                    run_id_count=len(livequery_history_lookup["k"]),
                )
                # VMW-149
                livequery_scroller = (
                    self.cb.select(Result)
                    .set_time_received(start=start, end=end)
                    .set_run_ids(livequery_history_lookup["k"])
                )
            except Exception as e:
                try:
                    found_all = re.findall(r"\d{3}", str(e))
                    self.log.debug(f'action=find_things e="{e}" find_all="{found_all}"')
                    error_code_api = (
                        int(found_all[0] if len(found_all) > 0 else 500) or 200
                    )
                    self.log.error(
                        "action=livequery_results_error error_code_api={}".format(
                            error_code_api
                        )
                    )
                    # DESK-1085: Failure of 410 causes a checkpoint to fail. Let's save the checkpoint anyway,
                    # and see if we can keep going.
                    if error_code_api in save_anyway_codes:
                        save_anyway = True
                except Exception as e2:
                    self.catch_error(e2)
                    self.log.warning(
                        f"action=bypass_exception amber_flag_2 exception={e2}"
                    )
            remaining_number = 1
            self.sourcetype("vmware:cbc:livequery:result")
            total_results = 0
            iteration = 0
            if livequery_scroller is None:
                self.fatal(action="livequery_scroller_is_none")
            while remaining_number > 0 and livequery_scroller is not None:
                lq_results = livequery_scroller.scroll(rows=max_scroll_rows)
                self.dbg(
                    action="scroll_results",
                    lq_results=len(lq_results),
                    iteration=iteration,
                    start=start,
                    end=end,
                    result_query=result_query,
                    lookback=lb,
                    row_limit_history=row_limit_history,
                    checkpoint=chkpnt,
                    max_scroll_rows=max_scroll_rows,
                    run_id_count=len(livequery_history_lookup["k"]),
                )
                total_results += len(lq_results)
                iteration += 1
                remaining_number = (
                    livequery_scroller.num_remaining
                    if livequery_scroller.num_remaining is not None
                    else 0
                )
                self.dbg(
                    action="received_livequery_run_results",
                    remaining_number=remaining_number,
                    result_query=result_query,
                )
                p = mp.Pool(10)
                matrix = [
                    (num, result, livequery_history_lookup)
                    for num, result in enumerate(lq_results)
                ]
                p.starmap(self._get_livequery_threaded, matrix)
                p.close()
                p.join()

            self.inform(action="calling_livequery_run_submit_query", status="end",
                        livequery_results_count=total_results)
            self.sourcetype(oldst)
            if total_results > 0:
                total_results_cycled = sum(
                    [
                        v["total_result_count"]
                        for x, v in livequery_history_lookup["aa"].items()
                    ]
                )
                self.inform(
                    action="saving_checkpoint",
                    chkpoint_name=chkpnt_name,
                    livequery_results_count=total_results,
                    run_history_total_results_count=total_results_cycled,
                )
                self.set_checkpoint(chkpnt_name)
            elif save_anyway:
                self.log.warning(
                    "action=saving_checkpoint error_code_api={} "
                    "msg='saving checkpoint due to forced condition' "
                    "start={} livequery_submitted".format(error_code_api, start)
                )
                self.set_checkpoint(chkpnt_name)
            else:
                self.log.warning(
                    "action=saving_checkpoint "
                    "msg='not saving checkpoint in case there was a communication error' "
                    "start={} livequery_submitted".format(start)
                )
            self._remove_lock()
        except Exception as e:
            self._catch_error(e)
            self._remove_lock()
            raise e


modular_input = VmwareCBCLiveQueryModularInput(
    app_name=__app_name__,
    scheme={
        "title": "VMWare Live Query Ingest",
        "description": "Gathers the results of a Live Query",
        "args": [
            {
                "name": "guid",
                "description": "distinct guid",
                "title": "GUID",
                "required": True,
            },
            {
                "name": "input_name",
                "description": "descriptive name",
                "title": "Name",
                "required": True,
            },
            {
                "name": "credential_guid",
                "description": "The API Key guid for authentication.",
                "title": "API Key Guid",
                "required": True,
            },
            {
                "name": "result_query",
                "description": "(Optional) Query to filter results",
                "title": "Result Query",
            },
            {
                "name": "lookback",
                "description": "Lookback in days used to retrieve query results",
                "title": "lookback",
            },
        ],
    },
)


def run():
    log.info(
        "action=start_modular_input name=vmware-cbc-livequery path={}".format(sys.path)
    )
    run_id = '{}'.format(str(uuid.uuid4()))
    modular_input.set_logger(log)
    modular_input.start()
    try:
        modular_input.setup_cb()
        modular_input.sourcetype("vmware:cbc:informational")
        modular_input.source(
            "vmware:cbc:input:{}".format(modular_input.get_config("guid"))
        )
        modular_input.splunk_index(modular_input.get_config("index", "main"))
        tmp_mi_config = modular_input.get_config()
        tmp_mi_config.pop("api_key_secret", "API Secret Key not found")
        modular_input.get_live_query(run_id)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_code_api = 0
        try:
            error_code_api = int(re.findall(r"\d{3}", str(e))[0]) or 200
        except Exception as e2:
            log.debug(
                f"action=bypass_exception amber_flag_3 exception={e2} error_code_api={error_code_api}"
            )
        error_msg = (
            " "
            "error_code_api={} "
            'error_message="{}" '
            'error_type="{}" '
            'error_arguments="{}" '
            'error_filename="{}" '
            'error_line_number="{}" '
            'input_guid="{}" '
            'input_name="{}" '.format(
                error_code_api,
                str(e),
                type(e),
                "{}".format(e),
                fname,
                exc_tb.tb_lineno,
                modular_input.get_config("guid"),
                modular_input.get_config("input_name"),
            )
        )
        log.error("{}".format(error_msg))
    finally:
        modular_input.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print("No tests for the scheme present")
        else:
            print("You giveth weird arguments")
    else:
        run()

    sys.exit(0)
