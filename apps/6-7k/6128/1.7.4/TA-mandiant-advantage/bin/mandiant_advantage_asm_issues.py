import import_declare_test

import json
import sys
import logging
import time
import traceback

from mandiant_utils import get_credentials
from common.asm_helper import AsmHelper
from common.collections import CollectionManager
from common.proxy import transform_proxy_config
from common.utility import get_app_version, create_start_date, get_base64_string
import common.log as log
from solnlib.modular_input import checkpointer

logger = log.get_logger(__file__)

from requests.exceptions import RequestException

from splunklib import modularinput as smi


class MANDIANT_ADVANTAGE_ASM_ISSUES(smi.Script):
    def __init__(self):
        super(MANDIANT_ADVANTAGE_ASM_ISSUES, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('mandiant_advantage_asm_issues')
        scheme.description = 'Mandiant Attack Surface Management Issues'
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
                'mandiant_advantage_account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'asm_project',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'issue_severity',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'lookback_days',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        
        success = True
        start = int(time.time())

        # Counters for logging
        ingested = 0
        skipped = 0
        ingest_errors = 0

        while True:
            # Get session key
            meta_configs = self._input_definition.metadata
            session_key = meta_configs.get("session_key")

            # Get App Version
            app_version = get_app_version(session_key)
            input_name = input_items[1]["name"]
            input_name = input_name.split("//")[1]
            logger.info(
                f"{input_name} | Starting Mandiant ASM Issue data "
                f"collection. App Version: {app_version}"
            )

            # Load settings
            index = input_items[1]["index"]
            # source = helper.get_input_type()
            # sourcetype = helper.get_sourcetype()
            asm_project = input_items[1]["asm_project"]
            issue_severity = input_items[1]["issue_severity"]
            lookback_days = input_items[1]["lookback_days"]
            account = get_credentials(input_items[1]['mandiant_advantage_account'], session_key)
            endpoint_url = f"https://{account.get('endpoint_url')}"
            access_key = account.get("access_key")
            secret_key = account.get("secret_key")
            proxy_config = {
                "proxy_enabled": account.get("proxy_enabled"),
                "proxy_username": account.get("proxy_username"),
                "proxy_port": account.get("proxy_port"),
                "proxy_type": account.get("proxy_type"),
                "proxy_password": account.get("proxy_password"),
                "proxy_url": account.get("proxy_url"),
            }
            proxies = transform_proxy_config(proxy_config)
            if account.get("validation_verify_ssl") == 1:
                verify_ssl = True
            else:
                verify_ssl = False

            # Load collection manager for issue cache
            issue_cache_collection = CollectionManager(
                session_key, "mandiant_asm_issue_cache"
            )
            issue_cache = issue_cache_collection._collection_as_dict()

            logger.info(
                f"{input_name} | Issue cache loaded successfully, "
                f"{len(issue_cache)} issues in cache"
            )

            # Load checkpoint
            checkpoint_key = "last_seen_after"
            checkpoint_collection = checkpointer.KVStoreCheckpointer(
                "TA_mandiant_advantage_checkpointer", session_key, 'TA-mandiant-advantage'
            )
            last_seen_after = checkpoint_collection.get(checkpoint_key)

            # If checkpoint is None, calc start date and update checkpoint for next run
            if not last_seen_after:
                logger.info(
                    f"{input_name} | Checkpoint not found, calculating date "
                    f"to start data collection from"
                )
                last_seen_after = create_start_date(int(lookback_days))
                checkpoint_collection.update(checkpoint_key, last_seen_after)
                logger.info(
                    f"{input_name} | Collection start date calculated as "
                    f"{last_seen_after}. Checkpoint updated"
                )
            else:
                logger.info(
                    f"{input_name} | Collection start date collected from "
                    f"checkpoint: {last_seen_after}"
                )

            # Initialize AsmHelper Class
            asm_helper = AsmHelper(
                access_key, secret_key, endpoint_url, verify_ssl, proxies
            )

            # Get project and collection friendly names
            project_name, collection_name = asm_helper.get_project_and_collection_names(
                asm_project
            )
            logger.info(
                f"{input_name} | Project name: {project_name}, Collection "
                f"Name: {collection_name}"
            )

            # Get project id from friendly name
            try:
                project_id = asm_helper.get_project_id(project_name)
                if not project_id:
                    logger.error(
                        f"{input_name} | Project ID not found for "
                        f"{project_name}: {project_name}. Please check input "
                        "settings and retry"
                    )
                    success = False
                    break
                logger.info(f"{input_name} | Project ID found: {project_id}")
            except RequestException as ex:
                logger.error(f"{input_name} | Error getting project id: {str(ex)}")
                success = False
                break

            # Get collection name for query
            try:
                collection_query = asm_helper.get_collection_name(
                    project_id, collection_name
                )
                if not collection_query:
                    logger.error(
                        f"{input_name} | Collection Name not found for "
                        f"{collection_name}. Please check input settings and "
                        "retry"
                    )
                    success = False
                    break
                logger.info(f"{input_name} | Collection found: {collection_query}")
            except RequestException as ex:
                logger.error(f"{input_name} | Error getting collection name: {str(ex)}")
                success = False
                break

            # Get issue severity filter
            issue_severity_filter = asm_helper.issue_severity_map.get(issue_severity)
            logger.info(
                f"{input_name} | Severity filter: {issue_severity}"
                f"({issue_severity_filter})"
            )

            # Get issues -> For each issue
            try:
                logger.info(f"{input_name} | Collecting issue list...")
                issues = []
                for issue in asm_helper.get_issues(
                    project_id,
                    collection_query,
                    last_seen_after,
                    issue_severity_filter,
                    1000,
                    logger
                ):
                    issues.append(issue)

                logger.info(
                    f"{input_name} | Issue list collected. {len(issues)} issues"
                )

                logger.info(f"{input_name} | Processing collected issue list...")
                for issue in issues:
                    # if issue in cache and not changed skip
                    issue_b64 = get_base64_string(str(issue))
                    if issue.get("id") in issue_cache:
                        cached_issue = issue_cache.get(issue.get("id")).get("base64")

                        if cached_issue == issue_b64:
                            logger.debug(
                                f"{input_name} | Issue ID: {issue.get('id')} not "
                                "changed, skipping"
                            )
                            skipped += 1
                            continue

                    # Get issue detail and add collection name, issue link
                    logger.debug(f"Processing issue id: {issue.get('id')}...")
                    issue_detail = asm_helper.get_issue(issue.get("id")).get("result")
                    issue_detail["collection_name"] = collection_name
                    issue_detail["issue_link"] = (
                        "https://asm.advantage.mandiant.com/issues/" f"{issue.get('id')}"
                    )
                    # Add id field for Splunk dashboard backward compatibility
                    issue_detail["id"] = issue.get("id")

                    # Ingest issue
                    try:
                        event = smi.Event(
                            data=json.dumps(issue_detail),
                            sourcetype='mandiant:advantage:asm:issues',
                            index=index
                        )
                        ew.write_event(event)

                        # Update cache
                        issue_cache_collection._batch_save(
                            [{"_key": issue.get("id"), "base64": issue_b64}]
                        )
                        ingested += 1
                        logger.debug(f"Ingested issue id: {issue.get('id')}")
                    except Exception as ex:
                        logger.error(f"{input_name} | Error ingesting event: {str(ex)}")
                        success = False
                        ingest_errors += 1
            except RequestException as ex:
                logger.error(f"Error collecting issues from ASM: {str(ex)}")
                success = False
            except Exception as ex:
                logger.error(
                    f"unexpected error processing issues: {str(ex)} \n"
                    f"{traceback.format_exc()}"
                )
                success = False

            # break loop to end execution
            break

        # log result
        logger.info(
            f"Issues ingested: {ingested}, Issues skipped (previously "
            f"indexed): {skipped}, Ingest errors: {ingest_errors}"
        )
        end = int(time.time())
        if success:
            logger.info(
                f"{input_name} | Data collection completed successfully in"
                f" {end - start} seconds"
            )
        else:
            logger.error(
                f"{input_name} | Data collection completed with errors in"
                f" {end - start} seconds"
            )


if __name__ == '__main__':
    exit_code = MANDIANT_ADVANTAGE_ASM_ISSUES().run(sys.argv)
    sys.exit(exit_code)