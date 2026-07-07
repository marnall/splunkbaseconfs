import logging as logger
import sys
import os
from KennyLoggins import KennyLoggins
from google_client import GSuiteModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from datetime import timedelta
from datetime import datetime
import multiprocessing.dummy as mp
from app_properties import __app_name__
import _paths

__author__ = 'ksmith'
_MI__app_name__ = 'Google Analytics Modular Input'
log = KennyLoggins(__app_name__, "analytics-modularinput", logger.INFO)

modular_input = GSuiteModularInput(app_name=__app_name__, scheme={
    "title": "Google Analytics Data",
    "description": "Consumes Analytics Data from GWorkspaces",
    "args": [
        {"name": "guid", "description": "distinct guid", "title": "GUID", "required": True},
        {"name": "view", "description": "The Google View to consume data from", "title": "View", "required": True},
        {"name": "metrics", "description": "The Metrics to consume", "title": "Metrics", "required": True},
        {"name": "dimensions", "description": "The dimensions to consume", "title": "Dimensions", "required": True},
        {"name": "time_field", "description": "The time field to use for event time", "title": "Time Field"},
        {"name": "backfill", "description": "The number of days to backfill", "title": "Backfill"},
        {"name": "credential", "description": "The API Key guid for authentication.", "title": "API Key Guid",
         "required": True}
    ]
})


def run():
    log.info("action=start_modular_input name=ga_analytics")
    modular_input.set_logger(log)
    modular_input.start()
    additional_buffer_dates = 5
    try:
        modular_input.sourcetype("google:workspaces:analytics")
        modular_input.source("google:workspaces:analytics:{}:{}".format(modular_input.get_config("view"),
                                                                        modular_input.get_config("guid")))
        modular_input.setup_gw("analytics")
        today = datetime.today()
        yesterdaydt = today - timedelta(days=1)
        yesterday = yesterdaydt.strftime("%Y-%m-%d")
        backfill = modular_input.get_config("backfill", default=1)
        log.debug("action=get_backfill backfill={} type={}".format(backfill, type(backfill)))
        try:
            backfill = int(backfill)
        except:
            backfill = 1
        if backfill > 1:
            log.debug("action=running_backfill total_backfill={}".format(backfill))
            dates = []
            for n in range(backfill):
                t = n + 1
                log.debug("action=running_backfill n={}".format(t))
                yesterdaydt = today - timedelta(days=t)
                yesterday = yesterdaydt.strftime("%Y-%m-%d")
                dates.append(yesterday)
                modular_input.analytics_api_reports(yesterday)
        else:
            log.debug("action=no_backfill backfill={}".format(backfill))
            modular_input.analytics_api_reports(yesterday)
        # GRAB THE CHECKPOINT, AND MAKE SURE ONLY THE "backfill" number of days is listed in the
        # "executed_timeranges" to prevent checkpoint SIZE ISSUES
        updated_checkpoint = modular_input.get_analytics_checkpoint()
        stored_dates = updated_checkpoint["executed_timeranges"]
        dates_stored = len(stored_dates)
        stored_dates.sort()
        log.debug(
            "action=checkpoint_review len_dates_stored={} backfill={} checkpoint={}".format(dates_stored, backfill,
                                                                                            stored_dates))
        if dates_stored <= (backfill + additional_buffer_dates):
            log.info(
                f"action=checkpoint_review msg='checkpoint ok.' len_stored_dates={dates_stored} backfill={backfill}")
        else:
            start_index = dates_stored - backfill - additional_buffer_dates
            log.info(
                f"action=checkpoint_review msg='checkpoint exceeds backfill' buffer={additional_buffer_dates} len_stored_dates={dates_stored} backfill={backfill} starting={start_index}")
            new_dates = stored_dates[start_index::]
            log.info(f"action=checkpoint_review length_new_dates={len(new_dates)} new_dates={new_dates}")
            updated_checkpoint["executed_timeranges"] = new_dates
            modular_input.set_analytics_checkpoint(updated_checkpoint)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "input_guid=\"{}\" " \
                    "input_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, modular_input.get_config("guid"),
                    modular_input.get_config("input_name"))
        log.error("{}".format(error_msg))
    finally:
        modular_input.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
