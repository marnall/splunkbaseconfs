import os
import time
import traceback
from urllib.parse import quote_plus
import import_declare_test

import json
import sys

from splunklib import modularinput as smi

import concurrent.futures
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.event_ingestor import EventIngestor
from infoblox_helpers.rest_helper import RestHelper
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.constants import THREAT_TYPES, DATETIME_FORMAT
from InfobloxAppForSplunk_utils import disable_input, get_checkpoint, save_checkpoint
from datetime import datetime, timedelta, timezone


class InfoBloxThreatIntelligence(smi.Script):
    """InfoBloxThreatIntelligence class."""

    def __init__(self):
        """Initialize."""
        super(InfoBloxThreatIntelligence, self).__init__()

    def get_scheme(self):
        """Get scheme."""
        scheme = smi.Scheme('infoblox_threat_intelligence')
        scheme.description = 'Threat Intelligence'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                'global_account',
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                'threat_level',
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                'confidence_level',
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                'historical_data',
                required_on_create=False
            )
        )

        scheme.add_argument(
            smi.Argument(
                'start_date',
                required_on_create=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """Validate input."""
        pass

    def fetch_and_ingest_historical_data(
        self,
        threat_type,
        checkpoint_key,
        session_key,
        data_collection_from_time,
        data_collection_to_time,
        start_date_epoch_time,
        infoblox_rest_helper,
        event_ingestor,
        logger,
        input_params
    ):
        """Fetch and ingest historical data into index."""
        try:
            flag = 0
            event_count = 0
            data_collection_from_epoch_time = (
                datetime.strptime(
                    data_collection_from_time,
                    DATETIME_FORMAT
                ) - datetime(1970, 1, 1)
            ).total_seconds()
            while data_collection_from_epoch_time >= start_date_epoch_time:
                threat_intelligence_data = infoblox_rest_helper.get_latest_threat_intelligence_data(
                    threat_type,
                    data_collection_from_time,
                    data_collection_to_time,
                    input_params.get('confidence_level', "")
                )
                threat_type = threat_intelligence_data.pop("threat_type", None)
                logger.info("message=records_received | Got {} {} records.".format(
                    threat_intelligence_data.get("record_count", 0),
                    threat_type
                ))

                if threat_intelligence_data.get("threat"):
                    temp_event_count = event_ingestor.ingest_latest_threats(
                        threat_intelligence_data.get("threat", []),
                        threat_intelligence_data.get("threat")[0].get("type").lower(),
                        input_params.get('threat_level', 0)
                    )
                    event_count += temp_event_count
                    logger.info("message=event_ingestion_success | Total {} {} records ingested.".format(
                        temp_event_count,
                        threat_intelligence_data.get("threat")[0].get("type").lower()))

                # save checkpoint data_collection_from_time
                save_checkpoint(
                    checkpoint_key,
                    session_key,
                    "historical_{}".format(threat_type),
                    data_collection_from_time,
                    logger
                )
                logger.info(
                    "message=historical_checkpoint_updated "
                    "| Historical Checkpoint {} Updated for {} : {}".format(
                        checkpoint_key, threat_type,
                        data_collection_from_time
                    )
                )
                # update data_collection_to_time to data_collection_from_time
                data_collection_to_time = (
                    datetime.strptime(
                        data_collection_from_time, DATETIME_FORMAT) - timedelta(microseconds=1)
                ).strftime(DATETIME_FORMAT)[:-3]
                data_collection_to_epoch_time = (datetime.strptime(
                    data_collection_to_time, DATETIME_FORMAT) - datetime(1970, 1, 1)).total_seconds()
                # update data_collection_from_time to minus 3 hour
                timestamp = datetime.strptime(data_collection_from_time, DATETIME_FORMAT)
                three_hours_ago = timestamp - timedelta(hours=3)
                data_collection_from_time = three_hours_ago.strftime(DATETIME_FORMAT)[:-3]
                data_collection_from_epoch_time = (datetime.strptime(
                    data_collection_from_time, DATETIME_FORMAT) - datetime(1970, 1, 1)).total_seconds()
                if flag or data_collection_to_epoch_time <= start_date_epoch_time:
                    break
                elif data_collection_from_epoch_time < start_date_epoch_time:
                    flag = 1
                    data_collection_from_epoch_time = start_date_epoch_time
                    data_collection_from_time = datetime.fromtimestamp(
                        start_date_epoch_time, tz=timezone.utc).strftime(DATETIME_FORMAT)[:-3]
            return {"event_count": event_count}
        except Exception:
            logger.error("message=fetch_and_ingest_historical_data_eror | {}".format(traceback.format_exc()))

    def calculate_from_to_time(self, input_params, ckpt_present, threat_type, logger, now_utc, start_date_epoch_time):
        """Calculate from and to time."""
        if ckpt_present and ckpt_present != input_params.get("start_date"):
            logger.info(
                "message=checkpoint_present "
                "| checkpoint present for {} : {}.".format(threat_type, ckpt_present)
            )
            ckpt_present_datetime = datetime.strptime(ckpt_present, DATETIME_FORMAT)
            three_hour_ago_utc = ckpt_present_datetime - timedelta(hours=3)
            if three_hour_ago_utc.timestamp() <= start_date_epoch_time:
                data_collection_from_time = input_params.get("start_date")
            else:
                data_collection_from_time = three_hour_ago_utc.strftime(DATETIME_FORMAT)[:-3]
            data_collection_to_time = (
                datetime.strptime(
                    ckpt_present,
                    DATETIME_FORMAT
                ) - timedelta(microseconds=1)
            ).strftime(DATETIME_FORMAT)[:-3]
            logger.info(data_collection_from_time)
            logger.info(data_collection_to_time)
        elif ckpt_present and ckpt_present == input_params.get("start_date"):
            logger.info(
                "message=checkpoint_present "
                "| checkpoint present for {} : {}. and it is same as start date time: {}".format(
                    threat_type,
                    ckpt_present,
                    input_params.get("start_date")
                )
            )
            return None, None
        else:
            logger.info(
                "message=checkpoint_not_present "
                "| checkpoint not present for {}. Hence starting data collection from : {} to : {}".format(
                    threat_type,
                    input_params.get("start_date"),
                    now_utc.strftime(DATETIME_FORMAT)[:-3]
                )
            )
            three_hour_ago_utc = now_utc - timedelta(hours=3)
            if three_hour_ago_utc.timestamp() <= start_date_epoch_time:
                data_collection_from_time = input_params.get("start_date")
            else:
                data_collection_from_time = three_hour_ago_utc.strftime(DATETIME_FORMAT)[:-3]
            data_collection_to_time = now_utc.strftime(DATETIME_FORMAT)[:-3]

        return data_collection_from_time, data_collection_to_time

    def get_latest_data(
        self,
        checkpoint_key,
        session_key,
        infoblox_rest_helper,
        event_ingestor,
        logger,
        input_params,
        from_time_to_dict,
    ):
        """Get Latest data."""
        event_count = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            try:
                future_obj = {
                    executor.submit(
                        infoblox_rest_helper.get_latest_threat_intelligence_data,
                        threat_type,
                        from_time_to_dict.get(threat_type, {}).get("from_time", ""),
                        from_time_to_dict.get(threat_type, {}).get("to_time", ""),
                        input_params.get('confidence_level', "")
                    ): threat_type for threat_type in THREAT_TYPES
                }
                for future in concurrent.futures.as_completed(future_obj):
                    threat_intelligence_data = future.result()
                    threat_type = threat_intelligence_data.pop("threat_type", None)

                    logger.info("message=records_received | Got {} records.".format(
                        threat_intelligence_data.get("record_count", 0)
                    ))

                    if threat_intelligence_data.get("threat"):
                        temp_event_count = event_ingestor.ingest_latest_threats(
                            threat_intelligence_data.get("threat", []),
                            threat_intelligence_data.get("threat")[0].get("type").lower(),
                            input_params.get('threat_level', 0)
                        )
                        event_count += temp_event_count
                        logger.info("message=event_ingestion_success | Total {} {} records ingested.".format(
                            temp_event_count,
                            threat_intelligence_data.get("threat")[0].get("type").lower()))
                    # save checkpoint data_collection_from_time
                    save_checkpoint(
                        checkpoint_key,
                        session_key,
                        "latest_{}".format(threat_type),
                        from_time_to_dict.get(threat_type, 0).get("to_time", ""),
                        logger
                    )
                    logger.info(
                        "message=checkpoint_updated "
                        "| Latest Checkpoint {} Updated for {} : {}".format(
                            checkpoint_key, threat_type,
                            from_time_to_dict.get(threat_type, 0).get("to_time", "")
                        )
                    )
                return event_count
            except Exception as e:
                logger.error("message=threat_intelligence_latest_data_error | {}".format(traceback.format_exc()))

                # saving checkpoint in case of first iteration
                ckpt_present = get_checkpoint(checkpoint_key, session_key, "latest_{}".format(threat_type), logger)
                if not ckpt_present:
                    save_checkpoint(
                        checkpoint_key,
                        session_key,
                        "latest_{}".format(threat_type),
                        from_time_to_dict.get(threat_type, 0).get("from_time", ""),
                        logger
                    )
                    logger.info(
                        "message=checkpoint_updated "
                        "| Latest Checkpoint {} Updated for {} : {}".format(
                            checkpoint_key, threat_type,
                            from_time_to_dict.get(threat_type, 0).get("from_time", "")
                        )
                    )
                raise Exception(str(e))

    def generate_from_to_time_dict(self, checkpoint_key, session_key, now_utc, logger):
        """Calculate latest from time."""
        from_time_to_time_dict = {}
        for threat_type in THREAT_TYPES:
            ckpt_present = get_checkpoint(checkpoint_key, session_key, "latest_{}".format(threat_type), logger)
            if ckpt_present:
                logger.info(
                    "message=checkpoint_present | checkpoint present for {} : {}".format(
                        threat_type, ckpt_present
                    )
                )
                data_collection_from_time = (
                    datetime.strptime(
                        ckpt_present, DATETIME_FORMAT) + timedelta(microseconds=1000)
                ).strftime(DATETIME_FORMAT)[:-3]
            else:
                logger.info(
                    "message=checkpoint_not_present | checkpoint not present for {}. "
                    "Hence collecting data of last one hour".format(threat_type)
                )
                one_hour_ago_utc = now_utc - timedelta(hours=1)
                data_collection_from_time = one_hour_ago_utc.strftime(DATETIME_FORMAT)[:-3]
            data_collection_to_time = now_utc.strftime(DATETIME_FORMAT)[:-3]
            from_time_to_time_dict[threat_type] = {
                'from_time': data_collection_from_time,
                'to_time': data_collection_to_time
            }
        return from_time_to_time_dict

    def iterate_input(self, inputs, session_key, input_items):
        """Iterate input."""
        for input_name, input_item in inputs.inputs.items():
            input_item['stanza_name'] = input_name
            input_item['name'] = input_name.split('://')[1]
            input_item['session_key'] = session_key
            input_items.append(input_item)
        return input_items

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Stream events."""
        try:
            start_time = time.time()
            event_count = 0
            input_items = [{'count': len(inputs.inputs)}]
            meta_configs = self._input_definition.metadata
            session_key = meta_configs['session_key']
            input_items = self.iterate_input(inputs, session_key, input_items)
            input_name = input_items[1]['name']
            logger = setup_logging("ta_infoblox_threat_intelligence", input_name=input_name)

            logger.info("message=data_collection_start_execution | Data collection stared.")
            account_info = get_credentials(
                session_key=session_key,
                account_name=input_items[1]['global_account']
            )
            input_items[1].update(account_info)

            # Initialize rest helper and event ingestor
            infoblox_rest_helper = RestHelper(input_items[1], logger)
            event_ingestor = EventIngestor(input_items[1], ew, logger)

            input_params = list(inputs.inputs.values())[0]

            now_utc = datetime.now(timezone.utc)
            checkpoint_key = "InfobloxAppForSplunk_{}_checkpointer".format(input_name)
            if input_params.get('historical_data') == "1":
                logger.info("message=historical_data | Historical data collection started.")
                future_obj = None
                future_list = dict()
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                        for threat_type in THREAT_TYPES:
                            # get checkpoint
                            ckpt_present = get_checkpoint(
                                checkpoint_key,
                                session_key,
                                "historical_{}".format(threat_type),
                                logger
                            )
                            start_date_epoch_time = (
                                datetime.strptime(
                                    input_params.get("start_date"),
                                    DATETIME_FORMAT
                                ) - datetime(1970, 1, 1)
                            ).total_seconds()
                            data_collection_from_time, data_collection_to_time = self.calculate_from_to_time(
                                input_params,
                                ckpt_present,
                                threat_type,
                                logger,
                                now_utc,
                                start_date_epoch_time
                            )
                            if not data_collection_from_time:
                                continue
                            future_obj = executor.submit(
                                self.fetch_and_ingest_historical_data,
                                threat_type,
                                checkpoint_key,
                                session_key,
                                data_collection_from_time,
                                data_collection_to_time,
                                start_date_epoch_time,
                                infoblox_rest_helper,
                                event_ingestor,
                                logger,
                                input_params
                            )

                            future_list[future_obj] = threat_type

                        if future_list:
                            for future in concurrent.futures.as_completed(future_list):
                                event_count += future.result().get("event_count", 0)
                    total_time_taken = time.time() - start_time
                    logger.info(
                        "message=events_collected | Total events ingested in Splunk"
                        " are {}".format(event_count)
                    )
                    logger.info(
                        "message=data_collection_end_execution | Data collection completed"
                        " and total time taken: {}".format(total_time_taken)
                    )

                    # disable input
                    disable_input(list(inputs.inputs.keys())[0], session_key, logger)
                except Exception:
                    logger.error(
                        "message=threat_intelligence_historical_data_error | {}".format(
                            traceback.format_exc()
                        )
                    )
            else:
                # Calculating data collection start time and end time
                from_time_to_time_dict = self.generate_from_to_time_dict(checkpoint_key, session_key, now_utc, logger)
                logger.info("message=latest_from_time_to_time | {}".format(from_time_to_time_dict))
                # Collecting latest data
                event_count += self.get_latest_data(
                    checkpoint_key,
                    session_key,
                    infoblox_rest_helper,
                    event_ingestor,
                    logger,
                    input_params,
                    from_time_to_time_dict
                )

            total_time_taken = time.time() - start_time
            logger.info(
                "message=events_collected | Total events ingested in Splunk"
                " are {}".format(event_count)
            )
            logger.info(
                "message=data_collection_end_execution | Data collection completed"
                " and total time taken: {}".format(total_time_taken)
            )
        except Exception:
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    exit_code = InfoBloxThreatIntelligence().run(sys.argv)
    sys.exit(exit_code)
