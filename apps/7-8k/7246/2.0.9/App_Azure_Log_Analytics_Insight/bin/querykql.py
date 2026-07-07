# encoding = utf-8

import app_azure_log_analytics_insight_declare

import datetime
import json
import logging
import os
import re
import sys
import time
from logging.handlers import RotatingFileHandler
from urllib.parse import urlsplit

import requests
from msal import ConfidentialClientApplication
from solnlib import conf_manager
from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch
from splunklib.searchcommands.validators import Boolean, Integer


APP_NAME = "App_Azure_Log_Analytics_Insight"
ACCOUNT_CONF = "app_azure_log_analytics_insight_account"
ACCOUNT_REALM = "__REST_CREDENTIAL__#{}#configs/conf-{}".format(APP_NAME, ACCOUNT_CONF)

SERVICE_ALIASES = {
    "log_analytics": "log_analytics",
    "loganalytics": "log_analytics",
    "logs": "log_analytics",
    "azure_monitor": "log_analytics",
    "app_insights": "app_insights",
    "appinsights": "app_insights",
    "application_insights": "app_insights",
    "applicationinsights": "app_insights",
    "defender": "defender",
    "mde": "defender",
    "advanced_hunting": "defender",
    "advance_hunting": "defender",
    "defender_advanced_hunting": "defender",
}

TIME_FIELDS = (
    "TimeGenerated",
    "Timestamp",
    "timestamp",
    "EventTime",
    "CreatedDateTime",
    "LastSeen",
    "ReportTime",
)


class QueryKqlError(Exception):
    pass


def get_splunk_home():
    if os.name == "nt":
        return os.environ.get("SPLUNK_HOME", "C:\\Program Files\\Splunk")
    return os.environ.get("SPLUNK_HOME", "/opt/splunk")


def get_logger():
    logger = logging.getLogger("querykql")
    if logger.handlers:
        return logger

    log_directory = os.path.join(get_splunk_home(), "var", "log", "splunk")
    try:
        os.makedirs(log_directory, exist_ok=True)
    except Exception:
        log_directory = os.path.dirname(__file__)

    handler = RotatingFileHandler(
        os.path.join(log_directory, "querykql.log"),
        maxBytes=1048576,
        backupCount=2,
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOGGER = get_logger()


def log(level, **fields):
    fields["time"] = datetime.datetime.utcnow().isoformat() + "Z"
    LOGGER.log(level, json.dumps(fields, sort_keys=True))


def normalize_host(value):
    value = (value or "").strip()
    if not value:
        raise QueryKqlError("Azure environment/endpoint is empty in the selected account.")

    parsed = urlsplit(value if "://" in value else "//" + value)
    host = parsed.netloc or parsed.path
    host = host.strip("/")
    if not host:
        raise QueryKqlError("Azure environment/endpoint is invalid: {}".format(value))
    return host


def normalize_service(value):
    normalized = SERVICE_ALIASES.get((value or "").strip().lower())
    if not normalized:
        raise QueryKqlError(
            "Unsupported service '{}'. Use one of: log_analytics, app_insights, defender.".format(value)
        )
    return normalized


def strip_wrapping_quotes(value):
    if not isinstance(value, str) or len(value) < 2:
        return value
    if value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def expected_host_fragment(service):
    if service == "log_analytics":
        return "loganalytics"
    if service == "app_insights":
        return "applicationinsights"
    return "security"


def ensure_service_matches_endpoint(service, endpoint_host):
    fragment = expected_host_fragment(service)
    if fragment not in endpoint_host:
        raise QueryKqlError(
            "The selected creds point to '{}', which does not look like a {} endpoint. "
            "Use an account configured for this service or pass endpoint=<host>.".format(
                endpoint_host, service
            )
        )


def make_scope(resource):
    resource = (resource or "").strip()
    if not resource:
        raise QueryKqlError("Token resource is empty.")
    if resource.endswith("/.default"):
        return resource
    if resource.startswith("https://") or resource.startswith("http://"):
        return resource.rstrip("/") + "/.default"
    return "https://" + normalize_host(resource) + "/.default"


def default_token_resource(service, endpoint_host):
    return endpoint_host


def acquire_access_token(account, service, endpoint_host, token_resource=None):
    tenant_id = account.get("tenant_id")
    client_id = account.get("username")
    client_secret = account.get("password")
    auth_host = normalize_host(account.get("azure_auth") or "login.microsoftonline.com")

    missing = [
        name
        for name, value in (
            ("tenant_id", tenant_id),
            ("username/client_id", client_id),
            ("password/client_secret", client_secret),
        )
        if not value
    ]
    if missing:
        raise QueryKqlError("Selected creds are missing required fields: {}".format(", ".join(missing)))

    authority_url = "https://{}/{}".format(auth_host, tenant_id)
    scope = make_scope(token_resource or default_token_resource(service, endpoint_host))

    app = ConfidentialClientApplication(
        client_id,
        authority=authority_url,
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(scopes=[scope])
    access_token = result.get("access_token")
    if access_token:
        return access_token

    error_description = result.get("error_description") or result.get("error") or "unknown token error"
    raise QueryKqlError("Unable to acquire Azure token for scope '{}': {}".format(scope, error_description))


def get_retry_delay(response, attempt):
    retry_after = response.headers.get("Retry-After") if response is not None else None
    try:
        delay = int(retry_after)
    except (TypeError, ValueError):
        delay = min(60, 2 ** attempt)
    return max(1, delay)


def post_json(url, headers, payload, timeout, max_retries):
    last_error = None
    for attempt in range(max_retries + 1):
        response = None
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < max_retries:
                    time.sleep(get_retry_delay(response, attempt))
                    continue

            if not response.ok:
                response_text = (response.text or "").replace("\n", " ")[:1000]
                raise QueryKqlError(
                    "Azure API request failed with HTTP {}: {}".format(
                        response.status_code,
                        response_text,
                    )
                )

            return response
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(get_retry_delay(response, attempt))
                continue
            raise QueryKqlError("Azure API request failed: {}".format(exc))

    raise QueryKqlError("Azure API request failed after retries: {}".format(last_error))


def trim_datetime_fraction(value):
    return re.sub(r"(\.\d{6})\d+([+-]\d{2}:?\d{2})?$", r"\1\2", value)


def parse_time(value):
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    candidate = trim_datetime_fraction(candidate)

    try:
        parsed = datetime.datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.timestamp()


def coerce_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    return value


def unique_field_name(name, seen):
    field_name = str(name or "field")
    if field_name not in seen:
        seen[field_name] = 1
        return field_name

    seen[field_name] += 1
    return "{}_{}".format(field_name, seen[field_name])


def add_common_fields(record, set_time):
    if set_time and "_time" not in record:
        for field_name in TIME_FIELDS:
            epoch = parse_time(record.get(field_name))
            if epoch is not None:
                record["_time"] = epoch
                break
    record["_raw"] = json.dumps(record, default=str, separators=(",", ":"), sort_keys=True)
    return record


def records_from_log_tables(data, result_table, max_rows, set_time):
    tables = data.get("tables") or []
    if not tables:
        return []

    table = None
    if result_table:
        try:
            table = tables[int(result_table)]
        except (ValueError, IndexError):
            for candidate in tables:
                if candidate.get("name") == result_table:
                    table = candidate
                    break
            if table is None:
                raise QueryKqlError("Result table '{}' was not found in Azure response.".format(result_table))
    else:
        table = tables[0]

    columns = table.get("columns") or []
    rows = table.get("rows") or []
    records = []
    column_names = [column.get("name") for column in columns]

    for row in rows:
        seen = {}
        record = {}
        for index, column_name in enumerate(column_names):
            field_name = unique_field_name(column_name, seen)
            value = row[index] if index < len(row) else None
            record[field_name] = coerce_value(value)
        records.append(add_common_fields(record, set_time))
        if max_rows and len(records) >= max_rows:
            break

    return records


def records_from_defender(data, max_rows, set_time):
    rows = data.get("Results") or data.get("results") or []
    schema = data.get("Schema") or data.get("schema") or []
    schema_names = [column.get("Name") or column.get("name") for column in schema]
    records = []

    for row in rows:
        record = {}
        if isinstance(row, dict):
            if schema_names:
                for column_name in schema_names:
                    if column_name in row:
                        record[column_name] = coerce_value(row.get(column_name))
                for column_name, value in row.items():
                    if column_name not in record:
                        record[column_name] = coerce_value(value)
            else:
                record = {key: coerce_value(value) for key, value in row.items()}
        else:
            seen = {}
            for index, column_name in enumerate(schema_names):
                field_name = unique_field_name(column_name, seen)
                value = row[index] if index < len(row) else None
                record[field_name] = coerce_value(value)

        records.append(add_common_fields(record, set_time))
        if max_rows and len(records) >= max_rows:
            break

    return records


def build_url(service, endpoint_host, target_id=None):
    if service == "log_analytics":
        return "https://{}/v1/workspaces/{}/query".format(endpoint_host, target_id)
    if service == "app_insights":
        return "https://{}/v1/apps/{}/query".format(endpoint_host, target_id)
    return "https://{}/api/advancedhunting/run".format(endpoint_host)


def build_payload(service, query, timespan=None):
    if service == "defender":
        return {"Query": query}

    payload = {"query": query}
    if timespan:
        payload["timespan"] = timespan
    return payload


def validate_target_id(service, target_id):
    if service == "log_analytics" and not target_id:
        raise QueryKqlError("workspace_id=<workspace-id> is required for service=log_analytics.")
    if service == "app_insights" and not target_id:
        raise QueryKqlError("app_id=<application-id> is required for service=app_insights.")


def format_message_text(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, separators=(",", ":"), sort_keys=True)
    return str(value)


@Configuration(type="events", retainsevents=True, streaming=False)
class QuerykqlCommand(GeneratingCommand):
    creds = Option(
        doc=""" **Syntax:** **creds=***<account-name>*
        **Description:** Name of the Azure account configured in this app. The command reads the tenant ID, client ID, client secret, authority host, and service endpoint from that stored account.
        **Example:** creds=azure_app
        """,
        require=True,
    )
    service = Option(
        doc=""" **Syntax:** **service=***<service-name>*
        **Description:** Azure service to query. Use log_analytics for Azure Log Analytics, app_insights for Application Insights, or defender for Microsoft Defender Advanced Hunting.
        **Example:** service=defender
        """,
        require=True,
    )
    query = Option(
        doc=""" **Syntax:** **query=***<kql>*
        **Description:** KQL query to send to the selected Azure service. Quote the value when the query contains spaces, pipes, or comparison operators.
        **Example:** query="DeviceProcessEvents | take 10"
        """,
        require=True,
    )
    workspace_id = Option(
        doc=""" **Syntax:** **workspace_id=***<workspace-id>*
        **Description:** Required only for service=log_analytics. This is the Azure Log Analytics Workspace ID used in the /v1/workspaces/<workspace-id>/query API path.
        **Example:** workspace_id=00000000-0000-0000-0000-000000000000
        """,
    )
    app_id = Option(
        doc=""" **Syntax:** **app_id=***<application-id>*
        **Description:** Required only for service=app_insights. This is the Application Insights Application ID used in the /v1/apps/<app-id>/query API path.
        **Example:** app_id=00000000-0000-0000-0000-000000000000
        """,
    )
    endpoint = Option(
        doc=""" **Syntax:** **endpoint=***<host>*
        **Description:** Optional override for the service endpoint host. Normally this comes from the selected stored account's azure_environment value.
        **Examples:** endpoint=api.security.microsoft.com, endpoint=api.loganalytics.io, endpoint=api.applicationinsights.io
        """,
    )
    token_resource = Option(
        doc=""" **Syntax:** **token_resource=***<resource-host-or-url>*
        **Description:** Optional advanced override for the Microsoft identity token resource. Leave unset unless a sovereign cloud or custom endpoint requires a different token audience.
        **Example:** token_resource=api.loganalytics.io
        """,
    )
    timespan = Option(
        doc=""" **Syntax:** **timespan=***<duration-or-range>*
        **Description:** Optional Log Analytics/Application Insights query timespan passed to Azure Monitor Query APIs. Defender ignores this option; include time filters in Defender KQL instead.
        **Example:** timespan=PT1H
        """,
    )
    result_table = Option(
        doc=""" **Syntax:** **result_table=***<index-or-name>*
        **Description:** Optional Log Analytics/Application Insights response table selector. Defaults to the first table, 0.
        **Example:** result_table=0
        """,
        default="0",
    )
    timeout = Option(
        doc=""" **Syntax:** **timeout=***<seconds>*
        **Description:** HTTP request timeout in seconds for the Azure API call. Default is 120 seconds.
        **Example:** timeout=180
        """,
        default=120,
        validate=Integer(1, 600),
    )
    max_retries = Option(
        doc=""" **Syntax:** **max_retries=***<count>*
        **Description:** Number of retries for Azure throttling or transient 5xx responses. Default is 2.
        **Example:** max_retries=3
        """,
        default=2,
        validate=Integer(0, 5),
    )
    max_rows = Option(
        doc=""" **Syntax:** **max_rows=***<count>*
        **Description:** Maximum rows to return to Splunk after Azure responds. Use 0 for no command-side row limit.
        **Example:** max_rows=1000
        """,
        default=0,
        validate=Integer(0),
    )
    set_time = Option(
        doc=""" **Syntax:** **set_time=***<bool>*
        **Description:** When true, the command maps a recognized Azure timestamp field such as TimeGenerated or Timestamp into Splunk _time.
        **Example:** set_time=false
        """,
        default=True,
        validate=Boolean(),
    )

    def write_safe_error(self, message):
        self.write_error("{}", format_message_text(message))

    def write_safe_warning(self, message):
        self.write_warning("{}", format_message_text(message))

    def load_account(self, creds):
        if self.metadata is None or not getattr(self.metadata, "searchinfo", None):
            raise QueryKqlError("Splunk search metadata is unavailable. Check querykql commands.conf.")

        searchinfo = self.metadata.searchinfo
        session_key = getattr(searchinfo, "session_key", None)
        splunkd_uri = getattr(searchinfo, "splunkd_uri", None)
        if not session_key or not splunkd_uri:
            raise QueryKqlError("querykql requires enableheader=true and requires_srinfo=true in commands.conf.")

        uri = urlsplit(splunkd_uri)
        manager = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            owner="nobody",
            scheme=uri.scheme,
            host=uri.hostname,
            port=uri.port,
            realm=ACCOUNT_REALM,
        )
        conf = manager.get_conf(ACCOUNT_CONF)
        return conf.get(creds)

    def target_id(self, service):
        if service == "log_analytics":
            value = strip_wrapping_quotes(self.workspace_id)
        elif service == "app_insights":
            value = strip_wrapping_quotes(self.app_id)
        else:
            value = None
        validate_target_id(service, value)
        return value

    def generate(self):
        start = time.time()
        rows = 0
        try:
            service = normalize_service(strip_wrapping_quotes(self.service))
            query = (strip_wrapping_quotes(self.query) or "").strip()
            if not query:
                raise QueryKqlError("query=<KQL> is required.")

            creds = strip_wrapping_quotes(self.creds)
            account = self.load_account(creds)
            endpoint_host = normalize_host(strip_wrapping_quotes(self.endpoint) or account.get("azure_environment"))
            ensure_service_matches_endpoint(service, endpoint_host)
            target_id = self.target_id(service)

            access_token = acquire_access_token(
                account,
                service,
                endpoint_host,
                token_resource=strip_wrapping_quotes(self.token_resource),
            )
            url = build_url(service, endpoint_host, target_id)
            payload = build_payload(service, query, timespan=strip_wrapping_quotes(self.timespan))
            headers = {
                "Authorization": "Bearer {}".format(access_token),
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if service in ("log_analytics", "app_insights"):
                headers["Prefer"] = "response-v1=true"

            log(logging.INFO, action="query_start", service=service, creds=creds, endpoint=endpoint_host)
            response = post_json(url, headers, payload, self.timeout, self.max_retries)
            data = response.json()

            if service == "defender":
                records = records_from_defender(data, self.max_rows, self.set_time)
            else:
                if "error" in data and data["error"]:
                    self.write_safe_warning(
                        "Azure returned a partial query error: {}".format(format_message_text(data["error"]))
                    )
                records = records_from_log_tables(data, self.result_table, self.max_rows, self.set_time)

            for record in records:
                rows += 1
                yield record

            log(
                logging.INFO,
                action="query_success",
                service=service,
                creds=creds,
                endpoint=endpoint_host,
                rows=rows,
                duration_seconds=round(time.time() - start, 3),
            )
        except conf_manager.ConfStanzaNotExistException:
            message = "Creds '{}' were not found in {}.".format(strip_wrapping_quotes(self.creds), ACCOUNT_CONF)
            log(logging.ERROR, action="query_error", error=message)
            self.write_safe_error(message)
            return
        except Exception as exc:
            message = str(exc)
            log(logging.ERROR, action="query_error", error=message, duration_seconds=round(time.time() - start, 3))
            self.write_safe_error(message)
            return


dispatch(QuerykqlCommand, sys.argv, sys.stdin, sys.stdout, __name__)
