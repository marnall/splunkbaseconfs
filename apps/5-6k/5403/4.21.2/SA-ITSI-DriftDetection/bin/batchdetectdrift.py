import json
import os
import sys
import time

import exec_anaconda

exec_anaconda.exec_anaconda()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

from util.constants import (ITSI_DRIFT_DETECTION_KPIS_URI,
                            LOOKBACK_PERIOD,
                            AGGREGATION_SPAN,
                            AGGREGATION_FUNCTION,
                            TOLERANCE_IN_PERCENT,
                            THRESHOLD_DIRECTION,
                            KVSTORE_KEY, 
                            ITSI_APP_NAME,
                            ITSI_DRIFT_DETECTION_CONFIGURATION,
                            ITSI_APP_OWNER,
                            DEFAULT_DATA_SPAN,
                            ADJUSTED_DATA_SPAN,
                            DAYS_OF_TWO_YEARS)

from logger import get_logger
from util.telemetry_logger import log_telemetry

logger = get_logger()


@Configuration()
class BatchDriftDetectionCommand(GeneratingCommand):

    @staticmethod
    def safe_network_call(func_, *args, **kwargs):
        try:
            response = func_(*args, **kwargs)
            if response.status != 200:
                owner = kwargs.get("owner", None)
                app = kwargs.get("app", None)
                end_point = args[0] if args else None
                logger.error(f"Network call failed with status {response.status}, end point: {end_point}, owner: {owner}, app: {app}")
                return None
            return json.loads(response.body.read())
        except Exception as e:
            logger.error(f"Exception occurred during network call: {str(e)}")
            return None

    def get_kpis_configured_for_drift_detection(self):
        return self.safe_network_call(self.service.get,
                                      ITSI_DRIFT_DETECTION_KPIS_URI,
                                      owner=ITSI_APP_OWNER,
                                      app=ITSI_APP_NAME) or []
    
    @staticmethod
    def calculate_data_span(lookback_period):
        try:
            # the lookback_period looks like "-70d", "-50d", "-750d" 
            # the unit is always "d", and there is an "-" sign at the begining.
            period = int(lookback_period[1:-1])
            # We switch to ADJUSTED_DATA_SPAN when the period is longer than two years
            # in which the data will be larger than ITSI reading limit, (1 million rows) 
            return ADJUSTED_DATA_SPAN if period >= DAYS_OF_TWO_YEARS else DEFAULT_DATA_SPAN
        except:
            return DEFAULT_DATA_SPAN
        
    @staticmethod
    def construct_spl_query(template_info, kpi_id):
        spl_template = """| mstats latest(alert_value) AS alert_value latest(alert_level) AS alert_level WHERE index=itsi_summary_metrics earliest={lookback_period} latest=now() AND itsi_kpi_id="{kpi_id}" AND is_filled_gap_event!=1 AND is_null_alert_value=0 by itsi_kpi_id, itsi_service_id span={data_span}
        | where alert_level!=-2
        | bin _time span={aggregation_span}
        | stats {aggregation_function}(alert_value) as alert_value by _time, itsi_kpi_id, itsi_service_id
        | table _time, alert_value, itsi_kpi_id, itsi_service_id
        | detectdrift threshold_direction="{threshold_direction}", threshold={tolerance_in_percent}"""
        # data_span is generated accroding to the lookback_period
        data_span = BatchDriftDetectionCommand.calculate_data_span(template_info[LOOKBACK_PERIOD])
        return spl_template.format(
            lookback_period=template_info[LOOKBACK_PERIOD],
            aggregation_span=template_info[AGGREGATION_SPAN],
            aggregation_function=template_info[AGGREGATION_FUNCTION],
            tolerance_in_percent=template_info[TOLERANCE_IN_PERCENT],
            threshold_direction=template_info[THRESHOLD_DIRECTION],
            kpi_id=kpi_id,
            data_span=data_span
        )

    def execute_spl_query(self, spl_query):
        """
        Executes an SPL query in blocking mode using the Splunk service.

        This method creates a search job, waits for it to complete, and logs the job's SID (Search ID)
        along with its final status. It returns the SID of the completed job or None if the execution fails.

        Parameters:
        - spl_query (str): The SPL query to be executed.

        Returns:
        - sid (str): The SID of the successfully executed job or None upon failure.

        Note:
        The job's success is evaluated based on the 'isFailed' flag and the 'dispatchState'.
        A job is considered successful if 'isFailed' is 0 (false) and 'dispatchState' is "DONE".
        Any other states indicate a failure or an incomplete job.

        For more details on parameters to `jobs.create` and job management,
        visit: https://dev.splunk.com/enterprise/docs/devtools/python/sdk-python/howtousesplunkpython/howtorunsearchespython/
        """
        try:
            # Replace newline characters with spaces
            single_line_query = spl_query.replace('\n', ' ')
            logger.info(f"Executing SPL query: {single_line_query}")

            job = self.service.jobs.create(spl_query, exec_mode="blocking")
            sid = job.sid

            logger.info(f"Search job initiated: SID={sid}")

            while not job.is_done():
                time.sleep(1)

            # Retrieve the final job status details
            is_failed = job["isFailed"]  # 0: success, 1: failure
            dispatch_state = job["dispatchState"]  # "DONE": success, "FAILED": failure

            # Evaluate job success
            if is_failed == "0" and dispatch_state == "DONE":
                job_status = "Success"
            else:
                job_status = "Failure"

            logger.info(f"Search job finished: SID={sid}, Status={job_status}, Dispatch State={dispatch_state}")

            return sid
        except Exception as e:
            logger.error(f"Failed to execute SPL query: {str(e)}")
            return None

    @staticmethod
    def get_kpi_id(kpi):
        return kpi.get(KVSTORE_KEY, "unknown")
    
    def generate(self):
        time_0 = time.time()
        log_telemetry(
            event_type = 'batchdetectdrift_start',
        )

        kpis = self.get_kpis_configured_for_drift_detection()

        cnt_kpi = len(kpis)
        log_telemetry(
            event_type = 'get_drift_configured_kpi',
            count_kpi = cnt_kpi
        )

        if cnt_kpi == 0:
            logger.info("No KPIs configured for drift detection.")
            return

        for kpi in kpis:
            try:
                kpi_id = self.get_kpi_id(kpi)
                template_info = kpi.get(ITSI_DRIFT_DETECTION_CONFIGURATION, {})

                if not template_info:
                    log_telemetry(
                        event_type = 'no_template_found',
                        kpi_id = kpi_id
                    )
                    kpis_in_log = kpis[:10] if len(kpi)>5 else kpis
                    logger.error((f"No template info found for KPI ID: {kpi_id}. Skipping drift detection." 
                                 f"The full response from kpi is {kpis_in_log} (up to 5 kpis)."))
                    continue

                logger.info(f"Initiating drift detection job for KPI ID: {kpi_id}")
                time_1 = time.time()

                # Construct the SPL query using the template information and KPI ID
                spl_query = self.construct_spl_query(template_info=template_info, kpi_id=kpi_id)

                # Execute the SPL query and proceed only if an SID was successfully returned
                sid = self.execute_spl_query(spl_query)

                log_telemetry(
                    event_type = 'inner_csc_complete',
                    kpi_id = kpi_id,
                    sid = sid,
                    total_time = f'{time.time() - time_1:.3f}s',
                )

                if not sid:
                    logger.error(f"Execution failed for KPI ID: {kpi_id}")
                    continue

                logger.info(f"Completed drift detection job: KPI ID={kpi_id}, SID={sid}")
                yield {'SID': sid}

            except Exception as e:
                logger.error(f"An error occurred during drift detection for KPI ID: {self.get_kpi_id(kpi)}: {e}")

        log_telemetry(
            event_type = 'batchdetectdrift_complete',
            total_time = f'{time.time() - time_0:.3f}s',
        )

dispatch(BatchDriftDetectionCommand, sys.argv, sys.stdin, sys.stdout, __name__)
