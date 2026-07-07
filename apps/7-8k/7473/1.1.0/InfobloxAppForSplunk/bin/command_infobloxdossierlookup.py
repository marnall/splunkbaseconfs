import import_declare_test
import sys
import time
import json
import traceback
from datetime import datetime
from infoblox_helpers.kvstore import CollectionManager
from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper
from infoblox_helpers.constants import SOURCES
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option


logger = setup_logging("ta_infoblox_dossier_lookup_custom_command")
WAIT_FOR_JOB_STATUS = 1800


@Configuration()
class InfoBloxDossierLookup(GeneratingCommand):
    """Infoblox Dossier Lookup custom command."""

    insight_type = Option(name="type", require=True)
    target = Option(name="target", require=True)
    account_name = Option(name="account_name", require=True)

    def validate(self):
        """Validate method."""
        if self.insight_type not in ("host", "ip", "url", "email", "hash"):
            logger.error("message=command_error | Infoblox Error : Given Type parameter is not valid.")
            raise Exception("Given Type parameter is not valid.")
        if self.target.strip() == "":
            logger.error("message=command_error | Infoblox Error : Given Target parameter is empty.")
            raise Exception("Given Target parameter is empty.")

    def post_dossier(self, rest_helper_obj):
        """Post request for Dossier."""
        payload = {
            "target": {
                "group": {
                    "type": self.insight_type,
                    "targets": [
                        self.target
                    ],
                    "sources": SOURCES[self.insight_type]
                }
            }
        }
        data = rest_helper_obj.post_dossier(json.dumps(payload, ensure_ascii=False))
        job_id = data.get("job_id")
        logger.info(f'message=command_info | Infoblox Info : Created Job Id: {job_id}.')
        return job_id

    def get_job_status(self, rest_helper_obj, job_id):
        """Get Job ID status."""
        start_time_check_status = time.time()
        while True:
            logger.info(f'message=command_info | Infoblox Info : Getting Job Id Status for: {job_id}.')

            data = rest_helper_obj.get_job_status(job_id)
            if data.get("status") == "success":
                logger.info(f'message=command_info | Infoblox Info : Got Success Job Status for: {job_id}.')
                return
            else:
                logger.info(
                    f'message=command_info | Infoblox Info : Got the Job Status for'
                    f' {job_id}: {data.get("status")}.'
                )
            if time.time() - start_time_check_status > WAIT_FOR_JOB_STATUS:
                logger.error(
                    f'message=command_job_status_timeout | Infoblox Error : The dossier job {job_id}'
                    f' have not completed within {WAIT_FOR_JOB_STATUS} seconds. Hence Exiting.'
                )
                exit(0)
            time.sleep(5)

    def get_job_result(self, rest_helper_obj, job_id):
        """Get Job ID Result."""
        data = rest_helper_obj.get_job_result(job_id)
        logger.info(f'message=command_info | Infoblox Info : Got Job Id Result for: {job_id}.')
        return data

    def transform_dns_data(self, data):
        """Transform DNS data."""
        dns_data = []
        for k, v in data.items():
            if k == "A":
                for meta_fields in v:
                    dns_data.append({
                        "type_dns": k,
                        "value": meta_fields.get("ip", ""),
                        "reverse": meta_fields.get("reverse", ""),
                        "ttl": meta_fields.get("ttl", "")
                    })
            elif isinstance(v, list):
                for mv in v:
                    dns_data.append({
                        "type_dns": k,
                        "value": mv
                    })
            else:
                dns_data.append({
                    "type_dns": k,
                    "value": v
                })
        return dns_data

    def generate(self):
        """Generate method."""
        try:
            logger.info("message=command_start_execution | Infoblox Info : Started Custom Command Script Execution.")
            start_time = time.time()
            session_key = self._metadata.searchinfo.session_key
            logger.info(
                f'message=command_start_execution | Infoblox Info : Provided params'
                f' are type: {self.insight_type} and target: {self.target} account_name: {self.account_name}.')
            self.validate()
            dossier_lookup = CollectionManager(
                "infoblox_dossier",
                service=self.service,
                session_key=session_key,
            )
            kv_values = dossier_lookup.get(
                query={"$or": [{"type": self.insight_type}], "$and": [{"target": self.target}]}
            )
            if kv_values:
                logger.info(
                    f'message=command_kv_values_found | Type:{self.insight_type}'
                    f' Target:{self.target} is found in the KV store with total events: {len(kv_values)}.'
                )
            else:
                logger.info(f'message=command_kv_values_not_found | Type:{self.insight_type}'
                            f' Target:{self.target} is not found in the KV store.')
                account_info = get_credentials(self.account_name, session_key)
                infoblox_config = {
                    "session_key": session_key
                }
                infoblox_config.update(account_info)

                rest_helper_obj = RestHelper(infoblox_config, logger)
                job_id = self.post_dossier(rest_helper_obj)
                self.get_job_status(rest_helper_obj, job_id)
                events = self.get_job_result(rest_helper_obj, job_id)
                events = events.get("results", [])
                total_kv_events = 0
                dict_soucre_sub_key = {
                    "atp": "threat",
                    "nameserver": "matches",
                    "rpz_feeds": "records",
                    "tld_risk": "matches",
                }
                kv_upsert_start_time = time.time()
                for event in events:
                    dossier_event = dict()
                    time_stamp = {"timestamp": datetime.now().isoformat()}
                    type_dossier = {"type": event.get("params", {}).get("type")}
                    target = {"target": event.get("params", {}).get("target")}
                    source_val = event.get("params", {}).get("source")
                    source = {"source": source_val}
                    if source_val in dict_soucre_sub_key.keys():
                        dossier_data = event.get("data", {}).get(dict_soucre_sub_key[source_val], [])
                    elif source_val == "dns":
                        dossier_data = self.transform_dns_data(event.get("data", {}))
                    else:
                        dossier_data = [event.get("data", {})]
                    dossier_event = [
                        dict({
                            "dossier_data": str(json.dumps(item, ensure_ascii=False))
                        }, **time_stamp, **type_dossier, **target, **source) for item in dossier_data
                    ]
                    kv_source_upsert_start_time = time.time()
                    dossier_lookup.upsert(dossier_event)
                    total_kv_events += len(dossier_event)
                    logger.info(
                        f'message=command_kv_write | Total events ingested in KV store for Type:{self.insight_type}'
                        f' Target:{self.target} Source:{source_val}: {len(dossier_event)} and time'
                        f' taken: elapsed_seconds={time.time() - kv_source_upsert_start_time}.')

                logger.info(
                    f'message=command_kv_write | Total events ingested in KV store for'
                    f' Type:{self.insight_type} Target:{self.target}: {total_kv_events} and total time'
                    f' taken: elapsed_seconds={time.time() - kv_upsert_start_time}.')

            yield {
                "_raw": {
                    "message": "ingested events in infoblox_dossier successfully"
                }
            }
        except Exception:
            logger.error(
                "message=unknown_error | Unknown error occured: {}".format(
                    traceback.format_exc()
                )
            )
            self.write_error(
                "Insufficient permissions to run custom commands or unexpected error."
                " Please see ta_infoblox_dossier_lookup_custom_command.log file for more information."
            )
            exit(0)
        finally:
            logger.info(
                'message=command_end_execution | End of the "{}" command execution.'
                " Total time taken: elapsed_seconds={:.3f}".format(
                    self.name, time.time() - start_time
                )
            )


dispatch(InfoBloxDossierLookup, sys.argv, sys.stdin, sys.stdout, __name__)
