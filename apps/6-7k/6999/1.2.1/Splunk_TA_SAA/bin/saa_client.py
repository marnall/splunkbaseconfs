"""This module contains a HTTP client to interact with the SAA API"""

import import_declare_test  # noqa: F401

import asyncio
import json


import dateutil.parser
import httpx
from saa_consts import JOB_SOURCETYPE, JOB_TASK_SOURCETYPE, JOB_RESOURCE_SOURCETYPE
from saa_utils import get_account_from_conf_file, get_proxy_settings, redact_token_for_logging
from splunklib import modularinput as smi
from typing import Optional
from structlog.stdlib import BoundLogger
from httpx._types import ProxiesTypes
from typing import cast
import time
from solnlib import log


class SAAClient:
    """
    SAAClient is a http client to retrieve information from Splunk Attack Analyzer
    """

    def __init__(  # pylint: disable=too-many-arguments
        self,
        logger: BoundLogger,
        base_url: str,
        api_token: str,
        proxies: Optional[dict] = None,
    ) -> None:
        self._logger = logger
        self.base_url = base_url
        self.api_token = api_token
        self.proxies = proxies
        self.forensics_semaphore = asyncio.Semaphore(10)

    @property
    def logger(self):
        """Returns the configured logger"""
        if self._logger is None:
            raise AttributeError("No logger configured")
        return self._logger

    def _get_auth_headers(self):
        return {"X-API-KEY": self.api_token}

    def test_connectivity(self):
        url = f"{self.base_url}/v1/jobs/poll"

        headers = self._get_auth_headers()

        proxies = cast(ProxiesTypes, self.proxies)

        try:
            with httpx.Client(proxies=proxies) as httpx_client:
                res = httpx_client.get(url, headers=headers)

            res.raise_for_status()

            res_body = res.json()

            if "Jobs" not in res_body:
                raise ValueError("server did not return expected event format")

        except ValueError as exc:
            log.log_server_error(self.logger, exc, msg_after="value error")
            raise exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                log.log_permission_error(self.logger, exc, msg_after="could not authenticate with provided API Key")
                self.logger.error("could not authenticate with provided API Key")
            raise exc

    def poll_jobs(  # pylint: disable=too-many-arguments
        self,
        params,
        event_writer,
        checkpointer,
        checkpoint_name,
        index,
        forensic_components,
        input_name,
        ingest_forensics=False,
    ):
        """Poll jobs from the API and write to the passed event writer

        Args:
            params (_type_): _description_
            event_writer (_type_): _description_
            index (_type_): _description_

        Returns:
            _type_: _description_
        """
        url = f"{self.base_url}/v1/jobs/poll"

        failed_attempts = 0
        next_tok = ""
        has_jobs = True

        while failed_attempts < 3 and has_jobs:
            try:
                final_params = {**params, "taskdetails": True, "count": 5}
                if next_tok != "":
                    final_params["token"] = next_tok

                self.logger.debug(f"querying with params {str(final_params)}")

                headers = self._get_auth_headers()

                proxies = cast(ProxiesTypes, self.proxies)

                with httpx.Client(proxies=proxies) as httpx_client:
                    res = httpx_client.get(url, headers=headers, params=final_params)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.logger.warning(f"unable to poll jobs {str(exc)}")
                failed_attempts += 1
                continue

            res.raise_for_status()  # At this point we assume we need a valid response
            try:
                res_json = res.json()
            except ValueError as e:
                log.log_exception(self.logger, e, "failed to parse response to JSON")
                raise e

            next_tok = res_json["NextToken"]
            new_jobs = res_json["Jobs"]
            self.logger.info(f"num_jobs {len(new_jobs)}")
            if len(new_jobs) > 0:
                events_to_write = []

                jobs_tasks_and_resources = {}

                for job in new_jobs:
                    job_created_time = dateutil.parser.isoparse(job["CreatedAt"])
                    job_created_timestamp = job_created_time.timestamp()

                    task_ids = []
                    resource_ids = []

                    if "Tasks" in job:
                        for task in job["Tasks"]:
                            task_ids.append(task["ID"])

                            task_created_time = dateutil.parser.isoparse(task["CreatedAt"])
                            task_created_timestamp = task_created_time.timestamp()

                            task["JobID"] = job["ID"]

                            event_writer.write_event(
                                smi.Event(
                                    time=f"{task_created_timestamp:.3f}",
                                    data=json.dumps(task, ensure_ascii=False, default=str),
                                    index=index,
                                    sourcetype=JOB_TASK_SOURCETYPE,
                                )
                            )
                    if "Resources" in job:
                        for resource in job["Resources"]:
                            resource_ids.append(resource["ID"])

                            resource_created_time = dateutil.parser.isoparse(resource["CreatedAt"])
                            resource_created_timestamp = resource_created_time.timestamp()

                            event_writer.write_event(
                                smi.Event(
                                    time=f"{resource_created_timestamp:.3f}",
                                    data=json.dumps(resource, ensure_ascii=False, default=str),
                                    index=index,
                                    sourcetype=JOB_RESOURCE_SOURCETYPE,
                                )
                            )
                    job.pop("Tasks", None)
                    job.pop("Resources", None)
                    event_data = json.dumps(job, ensure_ascii=False, default=str)

                    events_to_write.append(
                        smi.Event(
                            time=f"{job_created_timestamp:.3f}",
                            data=event_data,
                            index=index,
                            sourcetype=JOB_SOURCETYPE,
                        )
                    )

                    jobs_tasks_and_resources[job["ID"]] = {"task_ids": task_ids, "resource_ids": resource_ids}

                if ingest_forensics:
                    self.logger.info("start retrieving forensics")

                    loop = asyncio.get_event_loop()
                    list_of_events_to_write = loop.run_until_complete(
                        self.query_forensics_async(
                            index, new_jobs, jobs_tasks_and_resources, forensic_components, event_writer
                        )
                    )
                    for event_list in list_of_events_to_write:
                        events_to_write.extend(event_list)

                    self.logger.info("finished retrieving forensics")

                self.logger.info(f"starting eventwriter with {len(events_to_write)} events to write")

                n_events_written = {}

                for event in events_to_write:
                    event_writer.write_event(event)

                    if event.sourceType not in n_events_written:
                        n_events_written[event.sourceType] = 0
                    n_events_written[event.sourceType] += 1

                self.logger.info(f"finishing eventwriter with {len(events_to_write)} events written")

                for sourcetype, count in n_events_written.items():
                    log.events_ingested(
                        logger=self.logger,
                        sourcetype=sourcetype,
                        modular_input_name=input_name,
                        n_events=count,
                        index=index,
                    )

                self.logger.info(
                    "saving checkpoint",
                    checkpoint_name=checkpoint_name,
                    token=redact_token_for_logging(next_tok),
                )
                checkpointer.update(
                    checkpoint_name,
                    {"next_token": next_tok},
                )

            else:
                has_jobs = False

        self.logger.info(f"Returned {next_tok}")
        return next_tok

    async def query_forensics_async(self, index, jobs, jobs_tasks_and_resources, forensic_components, event_writer):
        """Queries normalized forensics for a set of jobs"""

        values = await asyncio.gather(
            *[
                self.query_forensic_async(
                    job, jobs_tasks_and_resources[job["ID"]], index, forensic_components, event_writer
                )
                for job in jobs
            ]
        )
        return values

    async def query_forensic_async(self, job, job_tasks_and_resources, index, components, event_writer):
        """Queries an individual jobs normalized forensics"""

        async with self.forensics_semaphore:
            job_id = job["ID"]
            url = f"{self.base_url}/v1/jobs/{job_id}/forensics"

            proxies = cast(ProxiesTypes, self.proxies)
            async with httpx.AsyncClient(proxies=proxies, timeout=10.0) as httpx_client:
                res_forensic = await httpx_client.get(url, headers=self._get_auth_headers())
                forensic = res_forensic.json()

                events = self.forensic_to_splunk_events(index, forensic, job, components, job_tasks_and_resources)

                return events

    def forensic_to_splunk_events(self, index, forensic, job, selected_components, job_tasks_and_resources):
        """Convert a normalized forensic into a set of Splunk Events for indexing"""
        forensic_sourcetype = "splunk:aa:forensic:{subsourcetype}"

        job_id = job["ID"]
        job_task_ids = job_tasks_and_resources["task_ids"]
        job_resource_ids = job_tasks_and_resources["resource_ids"]

        job_completed_time = dateutil.parser.isoparse(job["CompletedAt"])
        job_completed_timestamp = job_completed_time.timestamp()

        events = []
        for component in selected_components:
            if (
                component in forensic
                and forensic[component] is not None
                and isinstance(forensic[component], list)
                and len(forensic[component]) > 0
                and isinstance(forensic[component][0], dict)
            ):
                for entry in forensic[component]:
                    entry["JobID"] = job_id

                    if "ResourceTaskReferences" in entry:
                        for i, item in enumerate(entry["ResourceTaskReferences"]):
                            task_key = item["TaskKey"]
                            resource_key = item["ResourceKey"]

                            if int(task_key) < len(job_task_ids):
                                entry["ResourceTaskReferences"][i]["Task"] = job_task_ids[int(task_key)]
                            if int(resource_key) < len(job_resource_ids):
                                entry["ResourceTaskReferences"][i]["Resource"] = job_resource_ids[int(resource_key)]

                    event_data = json.dumps(entry, ensure_ascii=False, default=str)

                    events.append(
                        smi.Event(
                            time=f"{job_completed_timestamp:.3f}",
                            data=event_data,
                            index=index,
                            sourcetype=forensic_sourcetype.format(subsourcetype=component.lower()),
                        )
                    )
            else:
                self.logger.warn(
                    f"did not find forensic component {component} in {job_id} keys={json.dumps(list(forensic.keys()))}"
                )
        return events

    def submit_url(self, url):
        """Create a new job by submitting a url"""
        submit_url = f"{self.base_url}/v1/jobs/urls"
        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"

        proxies = cast(ProxiesTypes, self.proxies)
        with httpx.Client(proxies=proxies) as httpx_client:
            res = httpx_client.post(submit_url, headers=headers, json={"url": url})

        res.raise_for_status()
        return res.json()

    def submit_url_oneshot(self, url):
        submission_result = self.submit_url(url)
        job_id = submission_result["JobID"]
        job_summary = self.query_job(job_id)

        return job_summary

    def query_job(self, job_id):
        headers = self._get_auth_headers()
        headers["Content-Type"] = "application/json"
        job_summary_url = f"{self.base_url}/v1/jobs/{job_id}"

        proxies = cast(ProxiesTypes, self.proxies)
        with httpx.Client(proxies=proxies) as httpx_client:
            res = httpx_client.get(job_summary_url, headers=headers)

        res.raise_for_status()
        return res.json()

    def query_for_completed_job(self, job_id):
        is_finished = False

        job_summary = {}

        while not is_finished:
            job_summary = self.query_job(job_id)

            if job_summary["State"] in ["done", "error", "timedout", "any"]:
                is_finished = True

            time.sleep(10)

        return job_summary


def get_configured_client(session_key: str, logger: BoundLogger, account: str) -> SAAClient:
    """
    Factory function to create a configured client
    """

    # get account information
    account_config = get_account_from_conf_file(session_key, account)

    account_base_url = account_config["base_url"]
    account_api_key = account_config["api_key"]
    proxies = get_proxy_settings(logger, session_key)

    return SAAClient(logger, account_base_url, account_api_key, proxies)
