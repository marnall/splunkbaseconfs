import json
import os.path
import os
import logging
import sys
import traceback
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
import time

import package_helper # keep for added paths
import beacon_utils as utils
import requests
from requests.auth import HTTPBasicAuth
from splunklib import modularinput as smi
from solnlib import conf_manager, log
import splunk.rest as rest

APP_NAME = __file__.split(os.path.sep)[-3]
GRAPHQL_PATH = "/gateway/api/graphql"
HTTP_REQUEST_FAILED = "post http request failed"

def _get_proxy_config(*, session_key, logger, input_name) -> dict:
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_beacon_settings",
        )
        conf = cfm.get_conf("splunk_beacon_settings")
        return conf.get("proxy") or {}
    except Exception:
        utils.log_warning(
            logger=logger,
            input_name=input_name,
            message="failed to read proxy settings",
            params={"error": traceback.format_exc()},
        )
        return {}

def build_proxies(*, logger, session_key, input_name):
    """
    Build a requests proxies dictionary from app-level proxy settings (HTTPS only).
    Returns None if proxy is disabled or not configured.
    """
    proxy_conf = _get_proxy_config(session_key=session_key, logger=logger, input_name=input_name)
    enabled = str(proxy_conf.get("enable_proxy", "0")).strip() == "1"
    if not enabled:
        return None
    proxy_url = (proxy_conf.get("https_proxy_url") or "").strip()
    proxy_username = (proxy_conf.get("proxy_username") or "").strip()
    proxy_password = (proxy_conf.get("proxy_password") or "").strip()
    # if proxy username and proxy password are filled in, override the proxy url 
    if proxy_username:
        if "://" not in proxy_url:
            proxy_url = f"https://{proxy_url}"
        scheme, rest = proxy_url.split("://", 1)
        # strip existing credentials if present
        hostAndPort = rest.split("@", 1)[1] if "@" in rest else rest
        userinfo = quote(proxy_username, safe="")
        if proxy_password:
            userinfo += f":{quote(proxy_password, safe='')}"
        proxy_url = f"{scheme}://{userinfo}@{hostAndPort}"
    # log configuration without secrets
    utils.log_debug(
        logger=logger,
        input_name=input_name,
        message="proxy enabled",
        params={
            "proxy_url_scheme": proxy_url.split("://")[0] if "://" in proxy_url else "",
            "proxy_url_hostport": proxy_url.split("://", 1)[1].split("@")[-1] if "://" in proxy_url else proxy_url,
        },
    )
    return {"https": proxy_url}

class WorkspaceManager:
    def __init__(self):
        self._workspace_id = ""
        self._cloud_id = ""

    @property
    def workspace_id(self):
        return self._workspace_id

    @property
    def cloud_id(self):
        return self._cloud_id

    def get_workspace_ari(self, workspace_id):
        if not self._cloud_id:
            return None
        return f"ari:cloud:beacon:{self._cloud_id}:workspace/{workspace_id}"

    def needs_update(self, workspace_id):
        return self._workspace_id != workspace_id or not self._cloud_id

    def update(self, workspace_id, cloud_id):
        self._workspace_id = workspace_id
        self._cloud_id = cloud_id

    def is_valid(self):
        return bool(self._cloud_id)

    def log_state(self, logger, input_name):
        utils.log_debug(
            logger=logger,
            input_name=input_name,
            message="workspace manager state",
            params={
                "workspace_id": self._workspace_id,
                "cloud_id": self._cloud_id
            }
        )

def format_event(*, raw_event, domain, workspace_id, include_pii=False):
    def add_to_dict(src_dict, dst_dict, key):
        if src_dict.get(key, None):
            dst_dict[key] = src_dict[key]

    alert_id = raw_event["id"].split("/")[-1]
    dt_object = datetime.strptime(raw_event["createdOn"], "%Y-%m-%dT%H:%M:%S.%fZ")
    epoch = datetime.utcfromtimestamp(0)
    delta = dt_object - epoch
    epoch_milliseconds = int(delta.total_seconds() * 1000)

    formatted_event = {
        "id": alert_id,
        "type": "beacon:create:alert",
        "timestamp": epoch_milliseconds
    }

    formatted_event["alert"] = {
        "id": alert_id,
        "title": raw_event["title"],
        "created": raw_event["createdOn"],
        "url": utils.add_beacon_origin_tracing(f"https://{domain}/w/{workspace_id}/alerts/{alert_id}"),
        "time": {
            "start": raw_event["time"]["start"],
        },
        "type":  raw_event["type"],
    }
    add_to_dict(raw_event, formatted_event["alert"], "status")
    add_to_dict(raw_event, formatted_event["alert"], "product")
    add_to_dict(raw_event, formatted_event["alert"], "updatedOn")
    add_to_dict(raw_event, formatted_event["alert"], "statusUpdatedOn")
    add_to_dict(raw_event, formatted_event["alert"], "applicableSites")
    add_to_dict(raw_event, formatted_event["alert"], "replacementAlertId")
    add_to_dict(raw_event, formatted_event["alert"], "customFields")
    add_to_dict(raw_event["time"], formatted_event["alert"]["time"], "end")

    # Store top-level actor (replaces deprecated supportingData.highlight.actor)
    raw_actor = raw_event.get("actor") or {}
    actor_aaid = raw_actor.get("aaid")
    system_actor_name = raw_actor.get("name")
    actor_ip = raw_actor.get("ipAddress")
    if actor_aaid:
        formatted_event["actor"] = {
            "type": "actor",
            "accountId": actor_aaid,
            "url": utils.add_beacon_origin_tracing(f"https://{domain}/w/{workspace_id}/users/{actor_aaid}")
        }
        if include_pii:
            actor_user = raw_actor.get("user") or {}
            add_to_dict(actor_user, formatted_event["actor"], "name")
    elif system_actor_name:
        formatted_event["actor"] = {
            "type": "system",
            "name": system_actor_name,
        }
    elif actor_ip:
        formatted_event["actor"] = {
            "type": "anonymous",
            "ipAddress": actor_ip,
        }

    formatted_event["workspace"] = {
        "id": raw_event["workspaceId"],
    }
    add_to_dict(raw_event, formatted_event["workspace"], "orgId")

    # This is deprecated and will be removed
    # adding guard to the case when supportingData is defined as None
    support_data = raw_event.get("supportingData", {}) or {}
    highlight_data = support_data.get("highlight", {}) or {}
    if highlight_data:
        formatted_event["activity"] = {
            "time": {
                "start": highlight_data["time"]["start"],
            }
        }
        add_to_dict(highlight_data, formatted_event["activity"], "action")
        add_to_dict(highlight_data["time"], formatted_event["activity"]["time"], "end")
        subject_data = highlight_data.get("subject", {})
        if subject_data:
            formatted_event["activity"]["subject"] = {}
            add_to_dict(subject_data, formatted_event["activity"]["subject"], "ari")
            add_to_dict(subject_data, formatted_event["activity"]["subject"], "ati")
            add_to_dict(subject_data, formatted_event["activity"]["subject"], "containerAri")

    return formatted_event

def retrieve_last_date(*, session_key, index, host, source, logger, input_name):
    query = f'search index="{index}" host="{host}" source="{source}" earliest=0 | sort -_time | head 1 | fields timestamp'
    params = {
        'search': query,
        'exec_mode': 'oneshot',
        'output_mode': 'json',
    }

    try:
        response, content = rest.simpleRequest(
            "search/jobs",
            sessionKey=session_key,
            method='POST',
            postargs=params
        )
        decoded_content = content.decode("utf-8") if isinstance(content, bytes) else content
        status = str(response.get("status", ""))

        if status == "200":
            payload = json.loads(decoded_content)
            if not isinstance(payload, dict):
                message = "failed to query"
                error = f"unexpected Splunk search JSON type: {type(payload).__name__}"
                params = {"index": index, "response_preview": decoded_content[:500]}
            elif "results" not in payload:
                message = "failed to query"
                keys = list(payload.keys()) if isinstance(payload, dict) else []
                error = (
                    "Splunk oneshot response missing 'results' key "
                    f"(top-level keys: {keys})"
                )
                params = {
                    "index": index,
                    "response_preview": decoded_content[:2000],
                }
            else:
                results = payload["results"]
                event = json.loads(results[0]["_raw"]) if results else None
                date = event["timestamp"] if event else None
                return date
        else:
            message = "failed to query"
            try:
                err_body = json.loads(decoded_content)
                errs = err_body.get("messages") or err_body.get("errors") or []
                if isinstance(errs, list):
                    error = json.dumps(
                        [e.get("text", e) if isinstance(e, dict) else e for e in errs]
                    )
                else:
                    error = decoded_content[:1000]
            except json.JSONDecodeError:
                error = decoded_content[:1000]
            params = {
                "index": index,
                "status_code": status,
            }
    except Exception:
        message = "failed to query"
        error = traceback.format_exc()
        params = {
            "index": index,
        }
    utils.log_error(
        logger=logger,
        input_name=input_name,
        message=message,
        error=error,
        params=params
    )
    sys.exit("Error while fetching last event date. Terminating the modular input.")

def fetch_cloud_id_for_workspace(*, domain, workspace_id, username, token, logger, input_name, proxies=None):
    url = f"https://{domain}{GRAPHQL_PATH}"
    query = """
        query getCloudIdByActivationId($workspaceId: ID!) {
            tenantContexts(activationIds: [$workspaceId]) {
                cloudId
            }
        }
     """
    variables = {
        "workspaceId": workspace_id,
    }

    try:
        r = requests.post(
            url=url,
            headers={"Accept": "application/json"},
            auth=HTTPBasicAuth(username, token),
            json={"query": query, "variables" : variables},
            proxies=proxies,
        )
        if r.status_code == 200:
            content = r.json()
            if "errors" not in content:
                tenant_contexts = content["data"]["tenantContexts"]
                if len(tenant_contexts) > 0:
                    cloud_id = tenant_contexts[0]["cloudId"]
                    utils.log_debug(
                        logger=logger,
                        input_name=input_name,
                        message="Found cloud ID for workspace",
                        params={
                            "workspace_id": workspace_id,
                            "cloud_id": cloud_id
                        }
                    )
                    return cloud_id
                else:
                    message = "No cloud ID found for workspace"
                    error = "Empty tenant contexts response"
                    params = {"url": url, "workspace_id": workspace_id}
            else:
                message = "tenant GraphQL query failed"
                error = json.dumps([error["message"] for error in content["errors"]])
                params = {"url": url, "workspace_id": workspace_id}
        else:
            message = HTTP_REQUEST_FAILED
            error = r.reason
            params = {
                "status_code": r.status_code,
                "url": url,
                "workspace_id": workspace_id
            }
    except Exception:
        message = HTTP_REQUEST_FAILED
        error = traceback.format_exc()
        params = {"url": url}
    utils.log_error(
        logger=logger,
        input_name=input_name,
        message=message,
        error=error,
        params=params
    )
    sys.exit("Error while fetching cloudId. Terminating the modular input.")


def send_alert_query(
    *,
    domain,
    workspace_ari,
    username,
    token,
    logger,
    limit,
    input_name,
    endCursor="",
    proxies=None
):
    url = f"https://{domain}{GRAPHQL_PATH}"
    query = """
        query get_alerts_from_workspace_v2($id: ID!, $limit: Int, $cursor: String) {
            shepherd {
                alert {
                    byWorkspace(workspaceId: $id first: $limit, after: $cursor) {
                        ... on ShepherdAlertsConnection {
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                            edges {
                                node {
                                    id
                                    workspaceId
                                    title
                                    type
                                    status
                                    product
                                    orgId
                                    createdOn
                                    updatedOn
                                    statusUpdatedOn
                                    applicableSites
                                    replacementAlertId
                                    time {
                                        start
                                        end
                                    }
                                    actor {
                                        ... on ShepherdActor {
                                            aaid
                                            user {
                                              name
                                            }
                                        }
                                        ... on ShepherdAtlassianSystemActor {
                                            name
                                        }
                                        ... on ShepherdAnonymousActor {
                                            ipAddress
                                        }
                                    }
                                    customFields
                                    supportingData {
                                        highlight {
                                            ... on ShepherdActivityHighlight {
                                                action
                                                actor {
                                                    aaid
                                                    user {
                                                        name
                                                    }
                                                }
                                                subject {
                                                    ari
                                                    ati
                                                    containerAri
                                                }
                                                time {
                                                    start
                                                    end
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    variables = {
        "limit": limit,
        "id": workspace_ari,
        "cursor": endCursor,
    }

    try:
        r = requests.post(
            url=url,
            headers={"Accept": "application/json"},
            auth=HTTPBasicAuth(username, token),
            json={"query": query, "variables" : variables},
            proxies=proxies
        )
        if r.status_code == 200:
            content = r.json()
            if "errors" not in content:
                return content["data"]["shepherd"]["alert"]["byWorkspace"]
            else:
                message = "alert GraphQL query failed"
                error = json.dumps([error["message"] for error in content["errors"]])
                params = {"url": url}
        else:
            message = HTTP_REQUEST_FAILED
            error = r.reason
            params = {
                "status_code": r.status_code,
                "url": url
            }
    except Exception:
        message = HTTP_REQUEST_FAILED
        error = traceback.format_exc()
        params = {"url": url}
    utils.log_error(
        logger=logger,
        input_name=input_name,
        message=message,
        error=error,
        params=params
    )
    sys.exit("Error while fetching alert data. Terminating the modular input.")

def filter_alerts(*, alerts, last_date):
    while alerts and alerts[-1]["timestamp"] <= last_date:
        alerts.pop()
    return alerts

def request_alerts(
    *,
    domain,
    workspace_ari,
    workspace_id,
    username,
    token,
    logger,
    limit,
    last_date,
    input_name,
    include_pii=False,
    alerts=[],
    endCursor="",
    proxies=None
):
    if len(alerts) >= 500:
        utils.log_warning(
            logger=logger,
            input_name=input_name,
            message="reached maximum amount of alerts that can be retrieved",
            params={
                "total": len(alerts)
            }
        )
        return alerts

    response_json = send_alert_query(
        domain=domain,
        workspace_ari=workspace_ari,
        username=username,
        token=token,
        logger=logger,
        limit=limit,
        endCursor=endCursor,
        input_name=input_name,
        proxies=proxies
    )

    endCursor = response_json["pageInfo"]["endCursor"]
    has_next_page = response_json["pageInfo"]["hasNextPage"]

    new_alerts = [
        format_event(
            raw_event=alert["node"],
            domain=domain,
            workspace_id=workspace_id,
            include_pii=include_pii
        )
        for alert in response_json["edges"]
    ]

    alerts += filter_alerts(alerts=new_alerts, last_date=last_date)

    if len(new_alerts) == limit and has_next_page:
        utils.log_debug(
            logger=logger,
            input_name=input_name,
            message="searching next page for more alerts",
            params={
                "current_total": len(alerts)
            }
        )
        return request_alerts(
            domain=domain,
            workspace_ari=workspace_ari,
            workspace_id=workspace_id,
            username=username,
            token=token,
            logger=logger,
            limit=limit,
            last_date=last_date,
            input_name=input_name,
            include_pii=include_pii,
            alerts=alerts,
            endCursor=endCursor,
            proxies=proxies
        )
    else:
        return alerts

def write_event(
    *,
    event_writer,
    event,
    source,
    index,
    host,
    logger,
    input_name
):
    event_epoch_time = (
        (
            datetime.strptime(event["alert"]["created"][:-1], "%Y-%m-%dT%H:%M:%S.%f")
            - datetime(1970, 1, 1)
        )
        / timedelta(milliseconds=1)
        / 1000
    )

    smi_event = smi.Event(
        data=json.dumps(event),
        source=source,
        index=index,
        time=event_epoch_time,
        host=host
    )

    try:
        event_writer.write_event(smi_event)
        utils.log_debug(
            logger=logger,
            input_name=input_name,
            message=f"successfully wrote event",
            params={
                "index": index,
                "host": host,
                "event": event
            }
        )
    except Exception:
        utils.log_warning(
            logger=logger,
            input_name=input_name,
            message=f"event could not be written",
            params={
                "index": index,
                "host": host,
                "event": event,
                "error": traceback.format_exc()
            }
        )

def collect_events(
    *,
    event_writer,
    session_key,
    index,
    logger,
    domain,
    workspace_ari,
    workspace_id,
    username,
    token,
    limit,
    source,
    input_name,
    include_pii=False,
    proxies=None
):
    host = f"{domain}/w/{workspace_id}"

    last_date = retrieve_last_date(
        session_key=session_key,
        index=index,
        host=host,
        source=source,
        logger=logger,
        input_name=input_name
    )

    if last_date:
        utils.log_debug(
            logger=logger,
            input_name=input_name,
            message=f"recent event found",
            params={
                "index": index,
                "host": host,
                "timestamp": last_date
            }
        )

        alerts = request_alerts(
            domain=domain,
            workspace_ari=workspace_ari,
            workspace_id=workspace_id,
            username=username,
            token=token,
            logger=logger,
            limit=limit,
            last_date=last_date,
            input_name=input_name,
            include_pii=include_pii,
            proxies=proxies
        )

        last_date = retrieve_last_date(
            session_key=session_key,
            index=index,
            host=host,
            source=source,
            logger=logger,
            input_name=input_name
        )

        alerts = filter_alerts(
            alerts=alerts,
            last_date=last_date
        )

        if len(alerts) > 0:
            utils.log_debug(
                logger=logger,
                input_name=input_name,
                message="found new alerts",
                params={
                    "workspace_ari": workspace_ari,
                    "total": len(alerts)
                }
            )

        for alert in alerts:
            write_event(
                event_writer=event_writer,
                event=alert,
                source=source,
                index=index,
                host=host,
                logger=logger,
                input_name=input_name
            )
    else:
        utils.log_debug(
            logger=logger,
            input_name=input_name,
            message=f"recent event not found",
            params={
                "workspace_ari": workspace_ari,
                "index": index,
                "host": host
            }
        )

        response_json = send_alert_query(
            domain=domain,
            workspace_ari=workspace_ari,
            username=username,
            token=token,
            logger=logger,
            limit=1,
            input_name=input_name,
            proxies=proxies
        )

        event = format_event(
            raw_event=response_json["edges"][0]["node"],
            domain=domain,
            workspace_id=workspace_id,
            include_pii=include_pii
        )

        write_event(
            event_writer=event_writer,
            event=event,
            source=source,
            index=index,
            host=host,
            logger=logger,
            input_name=input_name
        )

    utils.log_info(
        logger=logger,
        input_name=input_name,
        message="input ran successfully",
    )

def get_api_token(*, logger, session_key, token_label, input_name):
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_beacon_api_token",
        )
        data = cfm.get_conf("splunk_beacon_api_token").get(token_label)
        return data["token"], data["username"]
    except Exception:
        utils.log_error(
            logger=logger,
            input_name=input_name,
            message="failed to fetch token details",
            error=traceback.format_exc()
        )
        sys.exit("Error while fetching API token details. Terminating the modular input.")

def validate_url(url, logger, input_name):
    """Validate the URL format and domain.

    Args:
        url: The URL to validate
        logger: Logger instance
        input_name: Name of the input

    Returns:
        tuple: (is_valid, parsed_url, workspace_id) or (False, None, None) if invalid
    """
    parsed_url = urlparse(url)
    parsed_path = parsed_url.path.split("/")
    expected_url_message = "Expected URL Format: https://detect.atlassian.com/w/workspace-id/alerts"

    if len(parsed_path) < 3:
        utils.log_error(
            logger=logger,
            input_name=input_name,
            message=expected_url_message,
            error="URL path too short",
            params={"url": url}
        )
        return False, None, None

    workspace_id = parsed_path[2]

    if parsed_url.hostname not in ("beacon.atlassian.com", "detect.atlassian.com", "beacon.stg.atlassian.com", "detect.stg.atlassian.com"):
        utils.log_error(
            logger=logger,
            input_name=input_name,
            message=expected_url_message,
            error="Domain not in allowed list",
            params={"url": url, "domain": parsed_url.hostname}
        )
        return False, None, None

    if not workspace_id:
        utils.log_error(
            logger=logger,
            input_name=input_name,
            message=expected_url_message,
            error="Workspace ID is empty",
            params={"url": url}
        )
        return False, None, None

    return True, parsed_url, workspace_id

class BaseScript(smi.Script):
    def __init__(self):
        super().__init__()
        self.workspace_manager = WorkspaceManager()

    def get_scheme(self):
        pass

    def stream_events(self, inputs, event_writer):
        try:
            session_key = self._input_definition.metadata["session_key"]
            input_name = list(inputs.inputs.keys())[0].split("//")[1]

            logger = log.Logs().get_logger("splunk_beacon_input")
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=APP_NAME,
                conf_name="splunk_beacon_settings",
                default_log_level="INFO",
            )
            logger.setLevel(log_level)

            # Add file handler to also write logs to $SPLUNK_HOME/var/log/guard_detect/ta_guard_detect.log
            try:
                splunk_home = os.environ.get("SPLUNK_HOME", "/Applications/Splunk")
                log_dir = os.path.join(splunk_home, "var", "log", "guard_detect")
                os.makedirs(log_dir, exist_ok=True)
                file_path = os.path.join(log_dir, "ta_guard_detect.log")
                if not any(getattr(h, "baseFilename", None) == file_path for h in logger.handlers):
                    file_handler = logging.FileHandler(file_path)
                    file_handler.setLevel(log_level)
                    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                    logger.addHandler(file_handler)
                    utils.log_debug(
                        logger=logger,
                        input_name=input_name,
                        message="file handler added",
                        params={"path": file_path}
                    )
            except Exception:
                # If file handler fails (e.g., permissions), continue with Splunk internal logging only
                utils.log_warning(
                    logger=logger,
                    input_name=input_name,
                    message="failed to add file handler",
                    params={"error": traceback.format_exc()}
                )

            for input_name, input_items in inputs.inputs.items():
                input_items["input_name"] = input_name
            token, username = get_api_token(
                logger=logger,
                session_key=session_key,
                token_label=input_items.get("api_token"),
                input_name=input_name
            )
            limit = min(50, 10 + ((int(input_items.get("interval")) // 60) - 1))

            is_valid, parsed_url, workspace_id = validate_url(
                input_items.get("url"),
                logger,
                input_name
            )

            if not is_valid:
                return

            source = input_items.get("source", input_items.get('input_name'))

            proxies = build_proxies(logger=logger, session_key=session_key, input_name=input_name)

            if self.workspace_manager.needs_update(workspace_id):
                self.workspace_manager.update(workspace_id, fetch_cloud_id_for_workspace(
                    domain=parsed_url.hostname,
                    workspace_id=workspace_id,
                    username=username,
                    token=token,
                    logger=logger,
                    input_name=input_name,
                    proxies=proxies
                ))

            if not self.workspace_manager.is_valid():
                return

            workspace_ari = self.workspace_manager.get_workspace_ari(workspace_id)

            include_pii = str(input_items.get("include_pii", "0")).strip() == "1"

            collect_events(
                event_writer=event_writer,
                session_key=session_key,
                index=input_items.get("index"),
                logger=logger,
                domain=parsed_url.hostname,
                workspace_ari=workspace_ari,
                workspace_id=workspace_id,
                username=username,
                token=token,
                limit=limit,
                source=source,
                input_name=input_name,
                include_pii=include_pii,
                proxies=proxies
            )
        except Exception:
            utils.log_error(
                logger=logger,
                input_name=input_name,
                message="error while streaming events",
                error=traceback.format_exc()
            )
            sys.exit("Error while streaming events. Terminating the modular input.")

class BeaconInput(BaseScript):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("Beacon Input")
        scheme.description = "Collect and index data from a Beacon workspace."
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        return scheme

if __name__ == "__main__":
    exit_code = BeaconInput().run(sys.argv)
    sys.exit(exit_code)
