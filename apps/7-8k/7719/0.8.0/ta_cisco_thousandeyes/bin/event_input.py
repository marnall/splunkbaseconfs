import json
import traceback
import import_declare_test  # noqa: F401

from log_helper import setup_logging
from splunklib import modularinput as smi
from thousandeyes_constant import THOUSANDEYES_TA_NAME, ACCOUNT_GROUP_SOURCETYPE  # noqa E402
from thousandeyes_client import ThousandEyesClient
from solnlib.modular_input.checkpointer import KVStoreCheckpointer
from thousandeyes_utils import get_current_date, calculate_start_date, get_account_id


class ThousandEyesEventCollector:
    """ThousandEyes collector for event data collection."""

    def __init__(self, inputs, ew):
        """
        Initialize object.

        :param inputs: input details.
        :param ew: Event Writer object.

        :return: ThousandEyesEventCollector Object
        """
        self.ew = ew
        self.session_key = inputs.metadata["session_key"]

        self.input_name = list(inputs.inputs.keys())[0]
        self.input_item = inputs.inputs[self.input_name]
        self.normalized_input_name = self.input_name.split("/")[-1]

        self.index = self.input_item["index"]
        self.logger = setup_logging(f"{THOUSANDEYES_TA_NAME}_event_{self.normalized_input_name}")
        self.thousandeyes_account_group = self.input_item["thousandeyes_acc_group"]
        self.thousandeyes_account_group_id = get_account_id(
            self.thousandeyes_account_group
        )
        self.thousandeyes_account = self.input_item["thousandeyes_user"]
        self.interval = int(self.input_item.get("interval"))
        self.thousandeyes_client = ThousandEyesClient(
            self.session_key, self.thousandeyes_account, self.logger
        )
        self.checkpoint = self.initialize_checkpoint()

    def initialize_checkpoint(self):
        """
        Initialize an checkpointer.

        :return: KVStoreCheckpointer Object
        """
        return KVStoreCheckpointer(
            collection_name=f"{THOUSANDEYES_TA_NAME}_checkpointer",
            session_key=self.session_key,
            app=THOUSANDEYES_TA_NAME,
        )

    def ingest_account_group_details(self):
        """Collect and ingest account group results."""
        current_checkpoint = self.checkpoint.get(self.normalized_input_name)
        if (
            current_checkpoint is None
            or current_checkpoint.get("first_run_completed", None) is None
        ):
            self.logger.info(
                f"{self.normalized_input_name}|Fetching all account group details."
            )
            acc_groups = self.thousandeyes_client.get_all_acc_groups()
            for acc in acc_groups.get("accountGroups"):
                event = smi.Event(
                    data=json.dumps(acc, ensure_ascii=False),
                    sourcetype=ACCOUNT_GROUP_SOURCETYPE,
                    index=self.index,
                )
                self.ew.write_event(event)
            self.logger.info(
                f"{self.normalized_input_name}|Successfuly fetched all account group details."
            )
            ckpt = {"first_run_completed": 1}
            if current_checkpoint:
                ckpt.update(current_checkpoint)
            self.checkpoint.update(self.normalized_input_name, ckpt)
            self.logger.info(
                f"{self.normalized_input_name}|Updated account group checkpoint."
            )

    def collect_events(self):
        """Collect Event results."""
        try:
            count = 0
            self.logger.info(
                f"{self.normalized_input_name}|Starting event data collection."
            )
            self.ingest_account_group_details()
            current_checkpoint = self.checkpoint.get(self.normalized_input_name)
            if (
                current_checkpoint is None
                or current_checkpoint.get("last_run", None) is None
            ):
                end_date = get_current_date()
                start_date = calculate_start_date(end_date, self.interval)
            else:
                start_date = current_checkpoint.get("last_run")
                end_date = get_current_date()

            self.logger.info(
                f"{self.normalized_input_name}|Collecting events from {start_date} to {end_date}."
            )
            events = self.thousandeyes_client.get_events(
                self.thousandeyes_account_group_id, start_date, end_date
            )
            count += len(events.get("events"))
            self.ingest_events(events)
            self.logger.debug(
                f"{self.normalized_input_name}|Collected {len(events.get('events'))} events."
            )

            while (
                events.get("_links", {}).get("next") and len(events.get("events")) != 0
            ):

                events = self.thousandeyes_client.get_paginated_data(
                    events.get("_links").get("next").get("href")
                )
                count += len(events.get("events"))
                self.ingest_events(events)
                self.logger.debug(
                    f"{self.normalized_input_name}|Collected {len(events.get('events'))} events."
                )
            if current_checkpoint:
                current_checkpoint.update({"last_run": events.get("endDate")})
            else:
                current_checkpoint = {"last_run": events.get("endDate")}
            self.checkpoint.update(self.normalized_input_name, current_checkpoint)
            self.logger.debug(
                f"{self.normalized_input_name}|Updated checkpoint with value {events.get('endDate')} ."
            )
        except Exception as e:
            self.logger.error(
                f"{self.normalized_input_name}|Error occurred during event data collection: {e}"
                f" {traceback.format_exc()}"
            )
        finally:
            self.logger.info(
                f"{self.normalized_input_name}|Finished collecting events."
                f"Collected total {count} events."
            )
            self.logger.info(
                f"{self.normalized_input_name}|Exiting event data collection."
            )

    def ingest_events(self, events):
        """Ingest event result into splunk."""
        for event in events.get("events"):
            event.update({"aid": self.thousandeyes_account_group_id})
            event = smi.Event(
                data=json.dumps(event, ensure_ascii=False),
                stanza=self.input_name,
            )
            self.ew.write_event(event)
