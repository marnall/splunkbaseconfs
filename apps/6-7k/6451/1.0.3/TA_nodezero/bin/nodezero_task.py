import json
import logging
import os
import sys
from ast import Str

import import_declare_test  # type: ignore
from solnlib import credentials
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
from splunklib.modularinput.event_writer import EventWriter

from h3queries import H3Queries
from horizon3client import H3APIClient
from horizon3client.exceptions import InternalError, AuthorizationError, APIError

from logs import set_up_logging


PARENT = os.path.sep + os.path.pardir
APP_PATH = os.path.abspath(__file__ + PARENT + os.path.sep)
h3queries = H3Queries()


class NODEZERO_TASK(smi.Script):
    def __init__(self):
        super(NODEZERO_TASK, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme("nodezero_task")
        scheme.description = "Input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "description",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "account",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "n0_index",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        input_item = next(iter(inputs.inputs.items()))[1]
        session_key = self.service.token
        logger = set_up_logging(session_key)
        h3_api_key = self.get_api_key(input_item["account"], session_key)

        try:
            h3 = H3APIClient(h3_api_key)
        except Exception as e:
            logger.fatal(f"Error initializing Horizon3 API connection: {e}")
            return

        op_statuses = self.pull_op_statuses(h3, logger)

        # saved_state = checkpoint._collection_data.query()
        checkpoint = checkpointer.KVStoreCheckpointer(
            "nodezero_ta_opstatus", session_key, "TA_nodezero"
        )

        new_ops = self.compare_pulled_ops_to_checkpoints(
            op_statuses, checkpoint, logger
        )

        # Pull data for ops that are done and canceled
        for op in new_ops:
            if op["op_state"] not in ["done", "canceled"]:
                logger.debug(
                    f"Op: {op['op_id']} has state: {op['op_state']}. Not pulling data this time...",
                )
                continue

            try:
                self.process_op(ew, input_item, logger, h3, checkpoint, op)
            except AuthorizationError as e:
                logger.error(f"Authorization error: {e}")
                ew.log(EventWriter.ERROR, f"Authorization error: {e}")
                break

        logger.debug(f"new_ops length: {len(new_ops)}")

    ### End Splunk Required Functions ###

    def process_op(
        self,
        ew: EventWriter,
        input_item,
        logger: logging.Logger,
        h3: H3APIClient,
        checkpoint: checkpointer.KVStoreCheckpointer,
        op,
    ):

        missing_data = (None, 0)

        if op.get("pulled_hosts") in missing_data:
            host_csv = self.pull_host_csv(h3, logger, op["op_id"])
            op = self.index_hosts_and_update_checkpoint(
                ew, input_item, checkpoint, op, host_csv
            )

        if op.get("pulled_weaknesses") in missing_data:
            weakness_csv = self.pull_weakness_csv(h3, logger, op["op_id"])
            op = self.index_weaknesses_and_update_checkpoint(
                ew, input_item, checkpoint, op, weakness_csv
            )

        if op.get("pulled_action_logs") in missing_data:
            action_logs = self.pull_action_logs(
                h3, h3queries.action_logs_page, op["op_id"], logger
            )
            op = self.index_action_logs_and_update_checkpoint(
                ew, input_item, checkpoint, op, action_logs
            )

    def pull_op_statuses(self, h3: H3APIClient, logger: logging.Logger) -> dict:
        try:
            op_statuses = h3._gql(query=h3queries.op_status)["data"]["op_tabs_page"][
                "op_tabs"
            ]
        except InternalError as e:
            logger.critical(f"CRITICAL ERROR: {str(e)}.  Op Statuses not pulled")
            op_statuses = None
        return op_statuses

    def pull_host_csv(self, h3: H3APIClient, logger: logging.Logger, op_id: Str):
        try:
            host_csv = h3._gql(h3queries.host_summary_csv, {"op_id": op_id},)[
                "data"
            ]["host_tabs_csv"]
            del host_csv[0]  # remove header
        except InternalError as e:
            logger.error(f"Error: {str(e)}.  Skipping {op_id} host data")
            host_csv = None
        except APIError as e:
            logger.error(f"Error: {str(e)}.  Skipping {op_id} host data")
            host_csv = None

        return host_csv

    def pull_weakness_csv(self, h3: H3APIClient, logger: logging.Logger, op_id: Str):
        try:
            weakness_csv = h3._gql(h3queries.weakness_csv, {"op_id": op_id},)[
                "data"
            ]["weakness_tabs_csv"]
        except InternalError as e:
            logger.error(f"Error: {str(e)}.  Skipping {op_id} weaknesses")
            weakness_csv = None
        except APIError as e:
            logger.error(f"Error: {str(e)}.  Skipping {op_id} weakness data")
            weakness_csv = None

        return weakness_csv

    def pull_action_logs(
        self, h3: H3APIClient, query, op_id: Str, logger: logging.Logger
    ):
        action_logs = []
        returned_action_logs = None
        page_num = 1
        try:
            while returned_action_logs != []:
                logger.debug(f"Pulling page {page_num} of {op_id} action_logs...")
                res_json = h3._gql(query, {"op_id": op_id, "page_num": page_num})

                page_num += 1
                returned_action_logs = res_json["data"]["action_logs_page"][
                    "action_logs"
                ]

                action_logs = action_logs + returned_action_logs
        except InternalError as e:
            logger.error(f"Error: {str(e)}.  Skipping {op_id} action_logs")
            action_logs = None
        except APIError as e:
            logger.error(f"Error: {str(e)}.  Skipping {op_id} action logs")
            action_logs = None

        return action_logs

    def compare_pulled_ops_to_checkpoints(
        self,
        op_statuses,
        checkpoint: checkpointer.KVStoreCheckpointer,
        logger: logging.Logger,
    ):
        new_ops = []

        # Add/Update KVStore Checkpointer and create new_ops
        for h3_op in op_statuses:
            checkpoint_data = checkpoint.get(h3_op["op_id"])

            # New KVStore op, save op_status to state
            if checkpoint_data is None:
                logger.debug(f"New op! {h3_op['op_id']}")
                for flag in ["pulled_weaknesses", "pulled_hosts", "pulled_action_logs"]:
                    h3_op[flag] = 0
                checkpoint.update(h3_op["op_id"], h3_op)
                new_ops.append(checkpoint.get(h3_op["op_id"]))
                continue

            # Op has a new state, save new state to kvstore
            if checkpoint_data["op_state"] != h3_op["op_state"]:
                logger.info(
                    f"Updating op_id {h3_op['op_id']} from {checkpoint_data['op_state']} to {h3_op['op_state']}",
                )
                checkpoint.update(h3_op["op_id"], h3_op)
                new_ops.append(checkpoint.get(h3_op["op_id"]))
                continue

            ret_missing = (None, 0)
            if (
                (checkpoint_data.get("pulled_weaknesses") in ret_missing)
                or (checkpoint_data.get("pulled_hosts") in ret_missing)
                or (checkpoint_data.get("pulled_action_logs") in ret_missing)
                ):
                new_ops.append(checkpoint.get(h3_op["op_id"]))

        return new_ops

    def index_action_logs_and_update_checkpoint(
        self, ew, input_item, checkpoint, op, action_logs
    ):
        if action_logs is not None:
            for action in action_logs:
                event = smi.Event(
                    data=json.dumps(action),
                    host=op["op_id"],
                    index=input_item["n0_index"],
                    source="ta_nodezero_modinput",
                    sourcetype="h3:nodezero:api:action_logs",
                )
                ew.write_event(event)
            op["pulled_action_logs"] = 1
            checkpoint.update(op["op_id"], op)
        return op

    def index_weaknesses_and_update_checkpoint(
        self, ew, input_item, checkpoint, op, weakness_csv
    ):
        if weakness_csv is not None:
            del weakness_csv[0]  # remove header
            for row in weakness_csv:
                event = smi.Event(
                    data=row,
                    host=op["op_id"],
                    index=input_item["n0_index"],
                    source="ta_nodezero_modinput",
                    sourcetype="h3:nodezero:api:weakness_export_csv",
                )
                ew.write_event(event)
            op["pulled_weaknesses"] = 1
            checkpoint.update(op["op_id"], op)
        return op

    def index_hosts_and_update_checkpoint(
        self, ew, input_item, checkpoint, op, host_csv
    ):
        if host_csv is not None:
            for row in host_csv:
                event = smi.Event(
                    data=row,
                    host=op["op_id"],
                    index=input_item["n0_index"],
                    source="ta_nodezero_modinput",
                    sourcetype="h3:nodezero:api:host_export_csv",
                )
                ew.write_event(event)
            op["pulled_hosts"] = 1
            checkpoint.update(op["op_id"], op)
        return op

    def get_api_key(self, account_name, session_key):

        cm = credentials.CredentialManager(
            session_key,
            "TA_nodezero",
            realm="__REST_CREDENTIAL__#TA_nodezero#configs/conf-nodezero_accounts",
        )

        return json.loads(cm.get_password(account_name))["api_key"]


if __name__ == "__main__":
    exit_code = NODEZERO_TASK().run(sys.argv)
    sys.exit(exit_code)
