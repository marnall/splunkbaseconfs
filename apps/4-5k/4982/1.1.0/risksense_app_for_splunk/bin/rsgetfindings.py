# encoding utf-8
import rs_declare

import sys
import json
import time

from splunklib.searchcommands import dispatch, Configuration, Option

from rs_base_command_handler import BaseCommandHandler
import rs_utility as util
from rs_connect import RisksenseConnect


def response_scroller(api_client, logger):
    """
    Use the api_client instance to fetch Findings and traverse through the pages.

    :param api_client: RiskSense_Connect Object
    :param logger: Logger Object

    :return : Return Findings event
    """
    # For debugging purposes
    start_time  = time.time()
    # Page counter
    page = 0
    # Processed events counter
    total_processed_events = 0
    # Total events counter
    total_events = 0
    # Events per page counter
    events_per_page = 0

    err_message = ''
    api_client.payload["page"] = page

    while not total_events or total_processed_events < total_events:

        # Iterate through all pages until all events are collected
        api_client.payload["page"] = page
        events_per_page = 0

        try:
            response = api_client.session.request(method="POST", url=api_client.url, headers=api_client.headers, data=json.dumps(
                api_client.payload), verify=util.VERIFY_SSL, proxies=api_client.proxies, timeout=util.REQUESTS_TIMEOUT)

            # Create a copy of response to raise status error after converted to json
            res = response
            response = response.json()

            # If error given by API, log that error else raise_for_status
            if len(response.get("errors", [])):
                err_message = "API error : {}".format(response.get("errors")[0]["defaultMessage"])
                raise Exception(err_message)

            res.raise_for_status()

            if not total_events:
                total_events = response["page"]["totalElements"]
                logger.info(
                    "Total {} Findings available in platform".format(total_events))
            if not total_events:
                break

            for event in response["_embedded"][api_client.asset_type]:
                total_processed_events += 1
                splunk_event = {
                    "_time": time.time(),
                    "_raw": event,
                    "source": "risksense"
                }
                splunk_event.update(event)
                # Yield this event to caller function
                yield splunk_event
                events_per_page += 1

            page += 1
            logger.info(
                "{} Findings collected from page {}".format(events_per_page, page))

        except Exception as e:
            err_message = "Error occurred while collecting Findings. Error -> {}".format( e)
            logger.error(err_message)
            raise Exception(err_message)

    end_time = time.time()
    logger.debug("Time taken to collect all Findings {}".format(end_time - start_time))

    logger.info(
        "Total {} Findings collected are {}".format(api_client.asset_type, total_processed_events))

@Configuration()
class FindingsCommand(BaseCommandHandler):
    """
    Generating command that returns the Findings information of an asset,
    Data pulled from /api/v1/client/{client_id}/{assetFinding}/search

    **Syntax**::
    `| rsGetFindings client_id="xxx" asset_type="hostFindings" severity="critical" asset_id="xxxxxx" filters="field1=vaule1:OPERATOR1" `
    
    **Description**::
    The `rsgetfindings` command uses the client_id, asset_type, severity, asset_id and filters to get the corresponding findings
    """

    client_id = Option(
        doc='''**Syntax:** **client_id=***<client id>*
        **Description:** Client id for which findings data is collected.''',
        name='client_id', require=True
    )

    severity = Option(
        doc='''**Syntax:** **severity=***<severity>*
        **Description:** Severity for findings. CRITICAL | HIGH | MEDIUM | LOW | INFO | TOTAL''',
        name='severity', require=True
    )

    asset_type = Option(
        doc='''**Syntax:** **asset_type=***<asset_type>*
        **Description:** Type of assest HOSTS | APPS ''',
        name='asset_type', require=True
    )

    asset_id = Option(
        doc='''**Syntax:** **asset_id=***<asset_id>*
        **Description:** HostId | AppId ''',
        name='asset_id', require=False
    )

    filters = Option(
        doc='''**Syntax:** **filters=***<field1=value1:OPERATOR1;field2=value2:OPERATOR2>*
        **Description:** Additional filters ''',
        name='filters', require=False
    )

    host_name = Option(
        doc='''**Syntax:** **host_name=***<host1>*
        **Description:** For host Findings filter by hostname ''',
        name='host_name', require=False
    )

    application_name = Option(
        doc='''**Syntax:** **application_name=***<App Name>*
        **Description:** For Application Findings filter by Application Name ''',
        name='application_name', require=False
    )

    operator = Option(
        doc='''**Syntax:** **operator=***<App Name>*
        **Description:** To match application_name / host_name using "EXACT"/ "WILDCARD" operator ''',
        name='operator', require=False
    )
    
    def do_generate(self, session_key, logger, proxies):

        client_id = self.client_id.strip()
        asset_id = self.asset_id.strip() if self.asset_id else self.asset_id
        severity = self.severity.strip().upper()
        asset_type = self.asset_type.strip().upper()
        filters = self.filters.strip() if self.filters else self.filters
        host_name = self.host_name.strip().strip("\"") if self.host_name else self.host_name
        application_name = self.application_name.strip().strip("\"") if self.application_name else self.application_name
        operator = self.operator.strip().upper() if self.operator else self.operator

        # Validate input params
        util.validate_client_and_asset_id("client_id", client_id)
        util.validate_client_and_asset_id("asset_id", asset_id)
        util.validate_asset_names(host_name, application_name)
        util.validate_operator(operator)
        util.validate_severity(severity)
        util.validate_asset_type(asset_type)
        util.validate_filters(filters)

        token, platform_url = util.get_account_details(session_key, logger, client_id)
        filters = util.prepare_filters(logger, severity, asset_id, asset_type, host_name, application_name, operator, filters)
        RS_Connect = RisksenseConnect(logger, client_id, token, platform_url, asset_type, filters, proxies)

        for event in response_scroller(RS_Connect, logger):
            yield event

    def __init__(self):
        super(FindingsCommand, self).__init__()

dispatch(FindingsCommand, sys.argv, sys.stdin, sys.stdout, __name__)