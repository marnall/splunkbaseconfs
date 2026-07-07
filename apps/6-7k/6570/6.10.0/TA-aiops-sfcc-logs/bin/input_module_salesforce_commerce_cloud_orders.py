import logging

from json import dumps
from uuid import uuid4
from os import environ
from os.path import join
from sys import getsizeof
from functools import partial
from typing import Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

import utils
import license
import pipeline
import api_client
import file_manager

from observability import WideEvent
from config import (
    CREATED_DATETIME_FORMAT,
    SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT,
)


@dataclass(frozen=True)
class OrderDataInputConfig:
    """Encapsulates all configuration for the order data input."""

    unique_id: str
    name: str
    site_id: str
    ocapi_hostname: str
    ocapi_credentials: dict[str, str]
    connection_type: str
    ocapi_shop_ordersearch_url: str
    select_statement: str
    host_override: str
    from_datetime_str: str
    max_datetime_str: str
    time_buffer: int
    delta_period: int
    auth_headers: dict[str, str] = field(default_factory=dict)


class CheckpointManager:
    """Manages the state and time window for the data ingestion."""

    def __init__(
        self,
        data_input_name,
        from_datetime_str,
        max_datetime_str,
        time_buffer,
        delta_period,
    ):
        self.data_input_name = data_input_name
        self.from_datetime_str = from_datetime_str
        self.max_datetime_str = max_datetime_str
        self.time_buffer = time_buffer
        self.delta_period = delta_period

        self.json_file_manager = file_manager.JSONFileManager(
            join(
                environ.get("SPLUNK_HOME", "/opt/splunk"),
                "var",
                "lib",
                "splunk",
                "modinputs",
                "salesforce_commerce_cloud_orders",
            ),
            file_replace_period_in_days=30,
            file_clean_period_in_days=30,
        )
        self.json_repo = file_manager.JSONFileRepository(self.json_file_manager)
        self.checkpoint_content = utils.get_job_checkpoint(
            self.json_repo, self.data_input_name, "orders", start_at=None
        )

        self.date_from = None
        self.date_to = None

    def is_ingestion_finished(self):
        if self.max_datetime_str and self.date_from:
            from_datetime = datetime.strptime(self.date_from, CREATED_DATETIME_FORMAT)
            max_datetime = datetime.strptime(
                self.max_datetime_str, CREATED_DATETIME_FORMAT
            )
            has_period_reached = (
                from_datetime + timedelta(seconds=self.time_buffer) >= max_datetime
            )
            if has_period_reached:
                return True
        return False

    def _apply_lookback_safeguard(self, from_datetime):
        if self.max_datetime_str is None or self.max_datetime_str == "":
            duration = datetime.now() - from_datetime
            if duration.days > 7:
                logging.info(
                    f"Initial run detected with a from_datetime={from_datetime.strftime(CREATED_DATETIME_FORMAT)} which is more than 7 days ago and no 'to_datetime' is set. "
                    f"This might be due to a lost checkpoint state. To prevent massive data re-ingestion, the start time will be reset to 5 minutes ago. "
                    f"data_input={self.data_input_name}"
                )
                # Set the start time to 15 minutes ago to prevent massive data re-ingestion
                return datetime.now() - timedelta(minutes=15)
        return from_datetime

    def calculate_time_window(self):
        initial_from_datetime = datetime.strptime(
            self.from_datetime_str, CREATED_DATETIME_FORMAT
        ) - timedelta(seconds=self.time_buffer)
        # If there is a checkpoint, use it to determine the start time
        if self.checkpoint_content and self.checkpoint_content.start_at:
            start_at_datetime = datetime.strptime(
                self.checkpoint_content.start_at, CREATED_DATETIME_FORMAT
            )
            if start_at_datetime > initial_from_datetime:
                from_datetime = start_at_datetime - timedelta(seconds=self.time_buffer)
            else:
                from_datetime = initial_from_datetime
        # If there is no checkpoint, apply the lookback safeguard
        else:
            from_datetime = self._apply_lookback_safeguard(initial_from_datetime)

        self.date_from = from_datetime.strftime(CREATED_DATETIME_FORMAT)

        to_datetime = datetime.now()
        if self.max_datetime_str:
            max_datetime = datetime.strptime(
                self.max_datetime_str, CREATED_DATETIME_FORMAT
            )
            if from_datetime < max_datetime:
                to_datetime = min(
                    max_datetime,
                    from_datetime
                    + timedelta(seconds=self.time_buffer + int(self.delta_period)),
                )

        self.date_to = to_datetime.strftime(CREATED_DATETIME_FORMAT)
        return self.date_from, self.date_to

    def save_checkpoint(self):
        """Saves the current in-memory checkpoint to disk."""
        self.checkpoint_content.start_at = self.date_to
        utils.save_job_checkpoint(
            self.json_file_manager,
            self.json_repo,
            self.checkpoint_content,
            self.data_input_name,
            "orders",
            start_at=self.date_to,
        )

    def _normalize_and_update_data(self, states_to_process):
        """
        Private helper to normalize and update the internal data dictionary.
        This is the single source of truth for state formatting.
        """
        for state in states_to_process:
            order_id = state.pop("order_id")
            self.checkpoint_content.data[order_id] = state

    def update_in_memory_state(self, states_to_update):
        """Updates the in-memory checkpoint dictionary with new states."""
        self._normalize_and_update_data(states_to_update)


def _batch_periods_into_fetch_jobs(
    periods: list[tuple[datetime, datetime, int]],
) -> list[tuple[datetime, datetime]]:
    """Merges consecutive time periods into larger batches (jobs).

    This ensures no single batch exceeds the OCAPI order search limit. It takes
    a list of smaller, contiguous time periods and groups them into the fewest
    possible jobs for efficient fetching.

    Args:
        periods (List[Tuple[datetime, datetime, int]]): A list of tuples,
            where each represents a time period: (start_time, end_time, order_count).

    Returns:
        List[Tuple[datetime, datetime]]: A list of tuples representing the
            optimal fetch jobs: (job_start_time, job_end_time).
    """
    if not periods:
        return []

    fetch_jobs = []
    # Sort by start time to ensure we are merging adjacent periods correctly.
    sorted_periods = sorted(periods, key=lambda p: p[0])

    # Initialize the first batch with the first period's data.
    batch_start_time, batch_end_time, batch_order_count = sorted_periods[0]

    # Iterate over the remaining periods to add them to batches.
    for period_start, period_end, order_count in sorted_periods[1:]:
        # If adding the next period would exceed the limit, finalize the current batch.
        if batch_order_count + order_count > SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT:
            # Add the completed batch to our list of jobs.
            fetch_jobs.append((batch_start_time, batch_end_time))

            # Start a new batch with the current period.
            batch_start_time = period_start
            batch_end_time = period_end
            batch_order_count = order_count
        else:
            # Otherwise, extend the current batch with this period's orders.
            batch_order_count += order_count
            # Always update the batch end time to the end of the last period considered.
            batch_end_time = period_end

    # After the loop, there's always one last batch to add.
    fetch_jobs.append((batch_start_time, batch_end_time))
    logging.info(
        f"Merged time_periods_count={len(periods)} fetch_jobs_count={len(fetch_jobs)}"
    )

    return fetch_jobs


def _ingest_orders_in_batches(
    order_api_client: api_client.SalesforceOrderAPIClient,
    order_type: str,
    date_from: datetime,
    date_to: datetime,
    select_statement: str,
    pipeline,
    wide_event: WideEvent,
    **kwargs,
) -> list[Any]:
    """Orchestrates ingesting a large volume of orders in optimal batches.

    This function first uses a planner to identify small, safe-to-fetch time
    windows to avoid hitting API limits. It then merges these small periods
    into larger, optimal jobs and processes each one sequentially.

    Args:
        order_api_client (utils.SalesforceOrderAPIClient): The client for API calls.
        order_type (str): The type of orders ('created' or 'updated').
        date_from (datetime): The start of the overall time window.
        date_to (datetime): The end of the overall time window.
        select_statement (str): The OCAPI select statement for the order query.
        pipeline (OrderPipeline): The processing pipeline for fetched orders.
        wide_event (WideEvent): The observability event tracker.
        **kwargs: Additional keyword arguments for the fetch function.

    Returns:
        List[Any]: A list of all checkpoint states from the processed jobs.
    """
    planner = utils.TimePeriodOrderFetchPlanner(
        order_api_client, order_type, select_statement
    )
    checkpoint_states = []
    safe_periods = planner.plan_fetchable_time_periods(date_from, date_to)

    if not safe_periods:
        return []

    optimal_fetch_jobs = _batch_periods_into_fetch_jobs(safe_periods)
    for job_start, job_end in optimal_fetch_jobs:
        logging.info(
            f"Processing batched time period type={order_type} job_start={job_start.isoformat()} job_end={job_end.isoformat()}"
        )
        job_start_str = job_start.strftime(CREATED_DATETIME_FORMAT)
        job_end_str = job_end.strftime(CREATED_DATETIME_FORMAT)
        states_from_job = _fetch_order_data(
            order_api_client,
            order_type,
            job_start_str,
            job_end_str,
            select_statement,
            pipeline,
            wide_event,
            **kwargs,
        )
        checkpoint_states.extend(states_from_job)

    return checkpoint_states


def validate_input(helper, definition):
    from_datetime = definition.parameters.get("from_datetime", None)
    time_buffer = definition.parameters.get("time_buffer", None)

    if from_datetime is None:
        raise ValueError('Please enter "From datetime"')
    if time_buffer is None:
        raise ValueError('Please enter "Time buffer"')


def _fetch_order_data(
    order_api_client,
    order_type,
    date_from,
    date_to,
    select_statement,
    pipeline,
    wide_event: WideEvent,
    **kwargs,
):
    total_count_method = getattr(
        order_api_client, f"get_{order_type}_orders_total_count_within_period"
    )
    get_data_method = getattr(
        order_api_client, f"get_{order_type}_orders_within_period"
    )
    thread_workers_count = 4
    all_states_to_save = []

    total_count = total_count_method(date_from, date_to, fields=select_statement)
    logging.info(f"Found {total_count} total {order_type} orders to fetch.")
    wide_event.add_timeline_event(
        "orders.ingestion.api_fetch.count_completed",
        order_type=order_type,
        total_count=total_count,
        date_from=date_from,
        date_to=date_to,
    )

    if total_count == 0:
        return all_states_to_save

    with ThreadPoolExecutor(
        max_workers=thread_workers_count,
        thread_name_prefix=f"{order_type.capitalize()}OrdersWorkersPool",
    ) as executor:
        futures = {
            executor.submit(
                get_data_method,
                date_from,
                date_to,
                fields=select_statement,
                start=chunk,
            ): chunk
            for chunk in range(0, total_count, 200)
        }
        failed_tasks: list[partial] = []

        logging.debug(
            f"Spawned {len(futures)} workers for {order_type} orders.",
            extra={"futures": futures},
        )

        for future in as_completed(futures):
            chunk_start = futures[future]
            if future.exception():
                error_message = str(future.exception())
                logging.exception(
                    f"Task has failed for type={order_type} reason={error_message}",
                )
                wide_event.add_error_event(
                    "orders.ingestion.api_batch.failed",
                    future.exception(),
                    order_type=order_type,
                    chunk_start=chunk_start,
                )
                data = futures[future]
                failed_task_func = partial(
                    get_data_method,
                    date_from,
                    date_to,
                    fields=select_statement,
                    start=data,
                )
                utils.add_failed_task_for_retry(failed_tasks, failed_task_func, data)
                continue

            response = future.result()
            logging.info(
                f"Processing batch type={order_type} chunk_start={chunk_start} chunk_end={chunk_start + 200}"
            )
            states = pipeline.execute(response, **kwargs)
            all_states_to_save.extend(states)
            wide_event.add_timeline_event(
                "orders.ingestion.api_batch.finished",
                order_type=order_type,
                chunk_start=chunk_start,
                item_count_in_batch=len(states),
            )

        if failed_tasks:
            logging.info(
                f"Retrying failed tasks for type={order_type} failed_tasks_count={len(failed_tasks)}"
            )
            wide_event.add_timeline_event(
                "orders.ingestion.api_batch.retried",
                order_type=order_type,
                failed_tasks_count=len(failed_tasks),
            )
            futures_retries = utils.resubmit_failed_tasks_for_retry(
                failed_tasks, executor
            )
            for retried_future in as_completed(futures_retries):
                chunk_start = futures_retries[retried_future]
                response = retried_future.result()
                logging.info(
                    f"Processing retried batch type={order_type} chunk_start={chunk_start} chunk_end={chunk_start + 200}"
                )
                states = pipeline.execute(response, **kwargs)
                all_states_to_save.extend(states)

    return all_states_to_save


def _create_config(helper) -> OrderDataInputConfig:
    auth_headers_str = helper.get_arg("auth_headers")
    auth_headers = (
        utils.split_http_auth_headers(helper, auth_headers_str)
        if auth_headers_str
        else {}
    )

    return OrderDataInputConfig(
        unique_id=str(uuid4()),
        name=helper.get_arg("name"),
        site_id=helper.get_arg("site_id"),
        ocapi_hostname=helper.get_arg("ocapi_hostname"),
        ocapi_credentials=helper.get_arg("ocapi_credentials"),
        connection_type=helper.get_arg("connection_type"),
        auth_headers=auth_headers,
        ocapi_shop_ordersearch_url=helper.get_arg("ocapi_shop_ordersearch_url"),
        select_statement=helper.get_arg("select_statement"),
        host_override=helper.get_arg("host_override"),
        from_datetime_str=helper.get_arg("from_datetime"),
        max_datetime_str=helper.get_arg("to_datetime"),
        time_buffer=int(helper.get_arg("time_buffer")),
        delta_period=int(helper.get_arg("delta_period")),
    )


@license.license_required
def collect_events(helper, ew):
    # Create the configuration
    config = _create_config(helper)
    wide_event = WideEvent(
        run_id=config.unique_id,
        data_input=config.name,
        host=config.ocapi_hostname,
        site_id=config.site_id,
    )
    wide_event.add_context(
        "configurations",
        {
            "host": config.ocapi_hostname,
            "endpoint": config.ocapi_shop_ordersearch_url,
            "site_id": config.site_id,
            "from_datetime": config.from_datetime_str,
            "to_datetime": config.max_datetime_str,
            "time_buffer": config.time_buffer,
            "delta_period": config.delta_period,
            "connection_type": config.connection_type,
        },
    )

    url, endpoint = None, None
    try:
        url, endpoint = utils.get_sfcc_url_and_endpoint(
            config.ocapi_hostname,
            config.ocapi_shop_ordersearch_url,
            config.site_id,
            connection_type=config.connection_type,
        )
        utils.init_program_termination_handlers(config.unique_id, config.name, helper)
        utils.enforce_secure_connection(url)
        logging.info(
            f"Starting Orders ingestion data_input={config.name} site_id={config.site_id} id={config.unique_id} connection_type={config.connection_type}"
        )
        event_host_field = (
            config.host_override if config.host_override else config.ocapi_hostname
        )
        wide_event.add_timeline_event(
            "orders.ingestion.started",
        )
        checkpoint_manager = CheckpointManager(
            config.name,
            config.from_datetime_str,
            config.max_datetime_str,
            config.time_buffer,
            config.delta_period,
        )
        date_from_str, date_to_str = checkpoint_manager.calculate_time_window()
        date_from, date_to = (
            datetime.strptime(date_from_str, CREATED_DATETIME_FORMAT),
            datetime.strptime(date_to_str, CREATED_DATETIME_FORMAT),
        )

        wide_event.add_context("ocapi", {"url": url, "endpoint": endpoint})
        wide_event.add_context(
            "checkpoint",
            {
                "found": bool(
                    checkpoint_manager.checkpoint_content
                    and checkpoint_manager.checkpoint_content.start_at
                ),
                "created_at": checkpoint_manager.checkpoint_content.created_at,
                "last_modified_at": checkpoint_manager.checkpoint_content.last_modified_at,
            },
        )

        if checkpoint_manager.is_ingestion_finished():
            logging.info(
                f"Data input has reached configured max time period data_input={config.name} to={config.max_datetime_str}"
            )
            wide_event.add_timeline_event(
                "orders.ingestion.finished_max_time_period",
                max_time=config.max_datetime_str,
            )
            wide_event.add_attribute("status", "finished")
            return None

        logging.info(
            f"Going to fetch Orders {date_from_str} - {date_to_str} for site {config.site_id} with maximum time {config.max_datetime_str}"
        )
        order_api_client = api_client.SalesforceOrderAPIClient(
            url,
            endpoint,
            config.ocapi_credentials["username"],
            config.ocapi_credentials["password"],
        )
        if config.auth_headers:
            order_api_client.set_permanent_http_headers(config.auth_headers)

        splunk_index = helper.get_output_index()
        co_splunk_indexer = utils.SplunkIndexer(
            helper,
            ew,
            splunk_index=splunk_index,
            host=event_host_field,
            source="created_orders",
            sourcetype="aiopsgroup:monitoring:sfcc:order_json",
        )
        uo_splunk_indexer = utils.SplunkIndexer(
            helper,
            ew,
            splunk_index=splunk_index,
            host=event_host_field,
            source="updated_orders",
            sourcetype="aiopsgroup:monitoring:sfcc:modified_order",
        )
        co_pipeline = pipeline.OrderPipeline(
            pipeline.OrdersExtractFromAPIResponseStep(),
            pipeline.DictExtractValueByKeyStep("data"),
            pipeline.OrderInsertInIndexStep(co_splunk_indexer),
            pipeline.MapOrderToStateStep(),
        )
        uo_pipeline = pipeline.OrderPipeline(
            pipeline.OrdersExtractFromAPIResponseStep(),
            pipeline.DictExtractValueByKeyStep("data"),
            pipeline.OrderExtendEventWithStateStep(),
            pipeline.OrderInsertInIndexStep(uo_splunk_indexer),
            pipeline.MapOrderToStateStep(),
        )

        # Process created orders
        total_created = order_api_client.get_created_orders_total_count_within_period(
            date_from_str, date_to_str, fields=config.select_statement
        )
        if total_created < SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT:
            created_orders_states = _fetch_order_data(
                order_api_client,
                "created",
                date_from_str,
                date_to_str,
                config.select_statement,
                co_pipeline,
                wide_event,
            )
        else:
            created_orders_states = _ingest_orders_in_batches(
                order_api_client,
                "created",
                date_from,
                date_to,
                config.select_statement,
                co_pipeline,
                wide_event,
            )
        checkpoint_manager.update_in_memory_state(created_orders_states)
        wide_event.add_timeline_event(
            "orders.ingestion.checkpoint.state.updated",
            updated_by="created_orders",
            orders_count=len(created_orders_states),
        )

        # Process updated orders
        total_updated = order_api_client.get_updated_orders_total_count_within_period(
            date_from_str, date_to_str, fields=config.select_statement
        )
        if total_updated < SALESFORCE_OCAPI_ORDER_SEARCH_FETCH_LIMIT:
            updated_orders_states = _fetch_order_data(
                order_api_client,
                "updated",
                date_from_str,
                date_to_str,
                config.select_statement,
                uo_pipeline,
                wide_event,
                checkpoint=checkpoint_manager.checkpoint_content,
            )
        else:
            updated_orders_states = _ingest_orders_in_batches(
                order_api_client,
                "updated",
                date_from,
                date_to,
                config.select_statement,
                uo_pipeline,
                wide_event,
                checkpoint=checkpoint_manager.checkpoint_content,
            )
        logging.info(
            f"Data successfully fetched from={date_from_str} to={date_to_str} site_id={config.site_id} id={config.unique_id}"
        )
        checkpoint_manager.update_in_memory_state(updated_orders_states)
        wide_event.add_timeline_event(
            "orders.ingestion.checkpoint.state.updated",
            updated_by="updated_orders",
            orders_count=len(updated_orders_states),
        )
        checkpoint_manager.save_checkpoint()
        wide_event.add_timeline_event(
            "orders.ingestion.checkpoint.saved",
            next_start_at=checkpoint_manager.date_to,
        )
        wide_event.add_timeline_event(
            "orders.ingestion.finished",
            date_from=date_from_str,
            date_to=date_to_str,
        )
        wide_event.update_context(
            "ocapi",
            total_created_orders_fetched=len(created_orders_states),
            total_updated_orders_fetched=len(updated_orders_states),
        )
        checkpoint_data_size_in_mb = round(
            getsizeof(checkpoint_manager.checkpoint_content.data) / 1024 / 1024, 3
        )
        wide_event.update_context(
            "checkpoint",
            next_start_at=date_to_str,
            states_count=len(checkpoint_manager.checkpoint_content.data),
            size_in_mb=checkpoint_data_size_in_mb,
        )
        logging.info(
            f"Finished Orders ingestion data_input={config.name} site_id={config.site_id} id={config.unique_id}"
        )
        wide_event.add_attribute("status", "finished")
    except (
        api_client.APIRetryError,
        api_client.APIReadTimeoutError,
        api_client.APIClientOrServerError,
        api_client.APIResponseBodyDecodeError,
    ) as ocapi_err:
        logging.error(
            f"[ERROR][OCAPIError] Orders ingestion data_input={config.name} site_id={config.site_id} id={config.unique_id} exception={str(type(ocapi_err))} message='{ocapi_err.exc_msg}' http_status_code={ocapi_err.http_status_code} http_response_body={ocapi_err.http_response_body}"
        )
        wide_event.add_error_event(
            "ocapi_error",
            ocapi_err,
            http_status_code=ocapi_err.http_status_code,
            http_response_body=ocapi_err.http_response_body,
        )
        wide_event.add_attribute("status", "failed")
    except file_manager.JSONFileDecodeError as json_file_decode_err:
        logging.error(
            f"[ERROR][File Checkpoint] Failed to load file data_input={config.name} site_id={config.site_id} id={config.unique_id} exception={str(type(json_file_decode_err))} message={json_file_decode_err.exc_msg} file={json_file_decode_err.fname}"
        )
        wide_event.add_error_event("checkpoint_error", json_file_decode_err)
        wide_event.add_attribute("status", "failed")
    except Exception as error:
        logging.error(
            f"[ERROR] Orders ingestion data_input={config.name} site_id={config.site_id} id={config.unique_id} exception={str(type(error))} message='{str(error)}'"
        )
        wide_event.add_error_event("unknown_error", error)
        wide_event.add_attribute("status", "failed")
        raise error
    finally:
        event_data = wide_event.build()
        splunk_event = helper.new_event(
            index="aiops_ingestion",
            host=event_host_field,
            source="aiops_ingestion",
            sourcetype="aiopsgroup:monitoring:sfcc:ingestion",
            data=dumps(event_data),
        )
        ew.write_event(splunk_event)
