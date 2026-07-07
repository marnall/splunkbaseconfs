import json
import sys
import time
from splunklib.six.moves.urllib.parse import quote as urlquote

import logger_manager as log
import splunk.Intersplunk
import threatq_utils as tq_utils
from threatq_const import VERIFY_SSL


def _consume_indicators(
    indicators, account_info, proxies, session_key, logger
):
    """Post events to the consume endpoint of ThreatQuotient.

    It is also useful to Add attributes to the indicator object
    """
    server_url = account_info["server_url"].strip("/")
    verify_cert = tq_utils.is_true(VERIFY_SSL)
    splunk_source_value = tq_utils.get_conf_info(
        session_key,
        'threatquotient_app_settings',
        'match_algo_detail',
        'hostname'
    )
    events = []
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
        splunk_url = (
            "{}/en-US/app/ThreatQAppforSplunk/search?q=search "
            "`threatq_match_indices` `threatq_match_sourcetypes` "
            'sourcetype!%3D"threatq:indicators" '
            '"{}"&earliest={}&latest={}'.format(
                splunk_web_url,
                urlquote(indicator.get("ioc_value")),
                indicator.get("first_seen"),
                indicator.get("last_seen"),
            )
        )
        first_seen_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(int(indicator.get("first_seen")))
        )
        last_seen_str = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.gmtime(int(indicator.get("last_seen")))
        )
        indicator_data["Match Count"] = indicator.get("match_count")
        indicator_data["First Seen"] = first_seen_str
        indicator_data["Last Seen"] = last_seen_str
        indicator_data["Splunk URL"] = splunk_url
        event["type"] = "Sighting"
        event["title"] = "Splunk sighting of indicator {}".format(
            indicator.get("ioc_value")
        )
        event["indicators"] = [{"id": indicator.get("ioc_id")}]
        event["happened_at"] = first_seen_str
        event["description"] = json.dumps(indicator_data).replace('\\"', '"')
        event["attributes"] = [
            {
                "name": "Match Count",
                "value": indicator.get("match_count"),
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
            },
        ]
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
        splunk_source,
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
    logger = log.setup_logging("ta_threatquotient_add_on_consume_indicators")
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
