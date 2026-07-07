import json
import sys
import os
import time
from splunklib.six.moves.urllib.parse import quote as urlquote

import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from threatq_const import VERIFY_SSL

APP_NAME = __file__.split(os.sep)[-3]

def _consume_indicators(
    indicators, account_info, proxies, session_key, logger
):
    """Post events to the consume endpoint of ThreatQuotient.

    It is also useful to Add attributes to the indicator object
    """
    server_url = account_info["server_url"].strip("/")
    verify_cert = tq_utils.is_true(VERIFY_SSL)

    events = []
    splunk_source_value = tq_utils.get_conf_info(
        session_key,
        'threatquotient_app_settings',
        'match_algo_detail',
        'hostname'
    )
    splunk_source_value = tq_utils.get_conf_info(
        session_key,
        'threatquotient_app_settings',
        'match_algo_detail',
        'hostname'
    )
    if not splunk_source_value:
        splunk_source_value = "Splunk"

    splunk_source = [{"name": splunk_source_value}]
    threatq_splunk_url = account_info.get("threatq_splunk_url")
    include_port = tq_utils.is_true(account_info.get("include_port"))
    splunk_web_url = tq_utils.get_splunk_web_url(session_key, include_port, threatq_splunk_url)
    for indicator in indicators:
        event = {}
        indicator_data = {}

        is_last_run_attr_exists = (
            indicator.get("last_run_last_seen") is not None
        ) or False
        new_first_seen = (
            indicator.get("last_run_first_seen")
            if is_last_run_attr_exists
            else indicator.get("first_seen")
        )
        new_last_seen = (
            indicator.get("last_run_last_seen")
            if is_last_run_attr_exists
            else indicator.get("last_seen")
        )
        new_match_count = (
            indicator.get("last_run_match_count")
            if is_last_run_attr_exists
            else indicator.get("match_count")
        )

        splunk_url = (
            "{}/en-US/app/ThreatQAppforSplunk/search?q=search "
            "`threatq_match_indices` `threatq_match_sourcetypes` "
            'sourcetype!%3D"threatq:indicators" '
            '"{}"&earliest={}&latest={}'.format(
                splunk_web_url,
                urlquote(indicator.get("ioc_value")),
                new_first_seen,
                new_last_seen,
            )
        )
        first_seen_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(int(new_first_seen))
        )
        last_seen_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(int(new_last_seen))
        )

        indicator_data["Match Count"] = new_match_count
        indicator_data["First Seen"] = first_seen_str
        indicator_data["Last Seen"] = last_seen_str
        indicator_data["Splunk URL"] = splunk_url

        settings_conf_file = tq_utils.get_conf_file(session_key, APP_NAME, "threatquotient_app_settings")
        splunk_cust_fields = settings_conf_file.get("custom_splunk_fields", {}).get("splunk_additional_fields", "")
        matching_type = settings_conf_file.get("match_algo_detail").get("match_type")
        keys = None
        name_of_fields = []
        list_of_dicts = []
        dict_to_append = {}
        if splunk_cust_fields and splunk_cust_fields.strip():
            keys = splunk_cust_fields.split(",")
            keys = [key.strip() for key in keys]
            for key in keys:
                if indicator.get("datamodel_name"):
                    key1 = key.split('.')[-1]
                else:
                    key1 = key.replace(".", "_")
                if key1 in indicator and indicator.get(key1, "").strip() and indicator.get(key1) != "-":
                    name_of_fields.append(key1)
                    dict_to_append["name"] = key1
                    dict_to_append["value"] = indicator[key1].strip()
                    dict_to_append["sources"] = splunk_source
                    list_of_dicts.append(dict_to_append)
                    dict_to_append = {}

        event["type"] = "Sighting"
        extra_title = (
            " - {}".format(last_seen_str) if is_last_run_attr_exists else ""
        )
        event["title"] = "Splunk sighting of indicator {}{}".format(
            indicator.get("ioc_value"), extra_title
        )
        event["indicators"] = [{"id": indicator.get("ioc_id")}]
        event["happened_at"] = first_seen_str
        event["description"] = json.dumps(indicator_data).replace('\\"', '"')
        event["attributes"] = [
            {
                "name": "Match Count",
                "value": indicator.get("match_count", 0),
                "sources": splunk_source,
                "overwrite_existing": True,
            },
            {
                "name": "Event Count",
                "value": indicator.get("last_run_match_count", 0),
                "sources": splunk_source,
                "overwrite_existing": True,
            },
            {
                "name": "Splunk URL",
                "value": splunk_url,
                "sources": splunk_source,
                "overwrite_existing": True,
            },
            {
                "name": "First Seen",
                "value": first_seen_str,
                "sources": splunk_source,
            },
            {
                "name": "Last Seen",
                "value": last_seen_str,
                "sources": splunk_source,
                "overwrite_existing": True,
            }
        ]
        if indicator.get("datamodel_name"):
            logger.debug("Adding Datamodel name in attributes.")
            datamodel_attr = {
                "name": "Datamodel Name",
                "value": indicator.get("datamodel_name"),
                "sources": splunk_source
            }
            event["attributes"].append(datamodel_attr)
        if list_of_dicts:
            logger.debug("Sending following fields in attributes to ThreatQ: {}".format(name_of_fields))
            event["attributes"].extend(list_of_dicts)
        checkbox_value = settings_conf_file.get("match_algo_detail").get("send_raw_checkbox")
        checkbox_value = tq_utils.is_true(checkbox_value)
        if checkbox_value and indicator.get("raw_event") and matching_type == "raw":
            logger.debug("Sending Raw event as description to ThreatQ as checkbox is checked.")
            event["description"] = indicator.get("raw_event")
        event["sources"] = splunk_source
        events.append(event.copy())

    logger.info("Updating indicators details on the ThreatQuotient platform")
    tq_utils.update_indicators(
        indicators,
        server_url,
        verify_cert,
        account_info,
        proxies,
        session_key,
        logger,
        splunk_source
    )
    logger.info("Updated indicators details")
    logger.info("Creating events on the ThreatQuotient platform")
    tq_utils.create_events(
        events,
        server_url,
        verify_cert,
        account_info,
        proxies,
        session_key,
        logger,
    )
    logger.info("Created events on the ThreatQuotient platform")


def main_():
    """Excecution starts here."""
    logger = log.setup_logging("ta_threatquotient_add_on_consume_indicators_new")
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    if not results:
        sys.exit()
    session_key = settings.get("sessionKey")
    account_info = tq_utils.get_credentials(session_key)
    proxies = tq_utils.get_proxy_info(session_key)

    if not account_info:
        logger.error(
            "ThreatQuotient Error: Failed to obtain credentials required to "
            "execute the request"
        )
        splunk.Intersplunk.parseError(
            "Failed to obtain credentials required to execute the request"
        )
        sys.exit(-1)

    try:
        _consume_indicators(results, account_info, proxies, session_key, logger)
    except Exception as e:
        logger.error(
            "ThreatQuotient Error: Error calling consume endpoint. {}".format(e)
        )
        splunk.Intersplunk.parseError(
            "Error calling consume endpoint. {}".format(e)
        )
        sys.exit(-1)


if __name__ == "__main__":
    main_()
