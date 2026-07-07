# encoding = utf-8

import copy
import json
import textwrap
from datetime import datetime

import requests

TRINITY_PORTAL_API_URL = "https://portal.trinitycyber.com/graphql"
API_TIMEOUT_SECONDS = 60

validate_api_key_query = """
    query SplunkValidateApiKey {
      events(first: 0) {
        pageInfo {
          hasNextPage
        }
      }
    }
"""

events_query = textwrap.dedent("""
    query SplunkEvents($after: String, $filter: EventFilter) {
      events(
        first: 1000
        after: $after
        filter: $filter
        sortBy: {field: INGEST_TIME, direction: ASC}
      ) {
        pageInfo {
          hasNextPage
          endCursor
        }
        edges {
          node {
            id
            portalUrl
            actionTime
            ingestTime
            sourceIp: source
            destinationIp: destination
            sourcePort
            destinationPort
            transportProtocol
            direction
            trustInitiated
            customer {
              name
            }
            connector {
              name
            }
            device {
              id
              clientDeviceId
              deviceName
              deviceType
            }
            formulaMatches {
              action {
                response
              }
              formula {
                formulaId
                title
                background
                tags {
                  category
                  value
                }
              }
            }
            applicationProtocol
            firstPayloadsSha256
            firstPayloadsFilename
            forwardProxyClientIdentifier
            forwardProxyClientIp
            applicationData {
              protocol: __typename
              ... on HttpRequestData {
                method
                path
                host
                userAgent
              }
              ... on HttpResponseData {
                statusCode
                statusString
                server
                contentType
              }
              ... on DnsData {
                host
              }
              ... on TlsData {
                sniHost
              }
              ... on DtlsData {
                sniHost
              }
              ... on SmtpData {
                smtpServerBannerMessage
                smtpServerBannerStatusCode
                smtpMailFrom
                smtpRcptTo
                emailFrom
                emailTo
                emailSubject
                emailMessageId
                emailReplyTo
                emailDate
                emailXmailer
              }
            }
          }
        }
      }
    }
""")


def validate_input(helper, definition):
    """Make a dummy request to the API to validate the API key"""
    # TODO: Splunk returns the API key as "*****", so we can't validate it against the server
    # api_key = definition.parameters.get('api_key', None)
    # headers = {
    #     "Content-Type": "application/json",
    #     "Authorization": f"Bearer {api_key}",
    # }
    # rv = requests.post(TRINITY_PORTAL_API_URL, json={"query": validate_api_key_query}, headers=headers)
    # if rv.status_code in (401, 403):
    #     raise ValueError('Invalid API key')


def collect_events(helper, ew):
    """Implement your data collection logic here"""

    api_key = helper.get_arg("api_key")
    min_event_time = helper.get_arg("min_event_time")
    event_filter = {"fromTime": min_event_time}

    try:
        for tc_event in get_events_from_api(helper, api_key, event_filter):
            data = json.dumps(tc_event)
            event_time = datetime.strptime(tc_event["actionTime"], "%Y-%m-%dT%H:%M:%S.%f+00:00").timestamp()
            sp_event = helper.new_event(data, time=event_time)
            ew.write_event(sp_event)
    except requests.HTTPError as ex:
        if ex.response.status_code in (403, 403):
            helper.log_error("Could not authenticate to API.  Please check your API key.")
        else:
            helper.log_error(
                f"The Trinity Cyber API return an error ({ex.response.status_code}: {ex.response.reason}). "
                "If this issue persists, please contact Trinity Cyber customer support for assistance."
            )


def get_events_from_api(helper, api_key, event_filter):
    """Returns a generator that iterates over all events since the marker"""
    have_more_pages = True
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    checkpoint_name = list(helper.get_input_stanza().keys())[0] + "_checkpoint"
    variables = dict(after=helper.get_check_point(checkpoint_name), filter=event_filter)
    while have_more_pages:
        request_json = {"query": events_query, "variables": variables}

        rv = helper.send_http_request(
            TRINITY_PORTAL_API_URL,
            "POST",
            parameters=None,
            payload=json.dumps(request_json),
            headers=headers,
            verify=True,
            timeout=API_TIMEOUT_SECONDS,
        )
        rv.raise_for_status()
        result_json = rv.json()

        for edge in result_json["data"]["events"]["edges"]:
            yield from flatten_event(edge["node"])

        end_cursor = result_json["data"]["events"]["pageInfo"]["endCursor"]
        have_more_pages = result_json["data"]["events"]["pageInfo"]["hasNextPage"]
        if end_cursor is not None:
            variables["after"] = end_cursor
            helper.save_check_point(checkpoint_name, end_cursor)
            helper.log_debug(f"Saved {end_cursor} to {checkpoint_name}")


def flatten_event(event):
    """Creates separate events for each formula match in a single Trinity Cyber event"""

    # Flatten application data
    new_data = {}
    for protocol_data in event.pop("applicationData"):
        protocol = protocol_data.pop("protocol")
        for field, value in protocol_data.items():
            if protocol == "SmtpData":
                # SMTP fields are already prefixed with "smtp" / "email", so use as-is
                key = field
            else:
                # Prefix everything else with protocol name (e.g. "host" -> "httpHost")
                key = protocol[0].lower() + protocol[1:].replace("Data", "") + field[0].upper() + field[1:]
            new_data[key] = value
    event.update(new_data)

    # Flatten formula matches into separate events
    formula_matches = event.pop("formulaMatches")
    for match in formula_matches:
        event_copy = copy.deepcopy(event)
        event_copy["formula"] = copy.deepcopy(match["formula"])
        event_copy["formula"]["response"] = match["action"]["response"]
        tags = event_copy["formula"].pop("tags")
        event_copy["formula"]["tags"] = {}
        for tag in tags:
            category = tag["category"]
            value = tag["value"]
            if category in event_copy["formula"]["tags"]:
                event_copy["formula"]["tags"][category] += f"; {value}"
            else:
                event_copy["formula"]["tags"][category] = value
        event_copy["id"] = f'{event_copy["id"]}_{match["formula"]["formulaId"]}'
        yield event_copy
