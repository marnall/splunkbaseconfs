# encoding = utf-8
import base64
import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse


AUDIT_LOGS_LATEST_ACTIVITY_TIME_CHECK_POINT_STRING = "audit_logs_latest_activity_time_check_point_string"
VERSION = "5.1.0"
MAX_CHARS_IN_CVE_HASH = 8


def base64encode(_str):
    return base64.b64encode(_str.encode('utf-8')).decode('utf-8')

def base64decode(_str):
    return base64.b64decode(_str.encode('utf-8')).decode('utf-8')

def get_headers(helper):
    orca_api_key = helper.get_global_setting("orca_api_key")

    return {
        "Authorization": f"Token {orca_api_key}",
        "x-orca-integration": "splunk",
        "x-orca-integration-client": f"splunk-add-on-{VERSION}",
    }

def request(helper, method, url, parameters, headers, timeout=(10.0, 10.0)):
    response = helper.send_http_request(
        url,
        method=method,
        parameters=parameters,
        headers=headers,
        timeout=timeout,
    )

    if response.status_code != 200:
        raise Exception(
            f"Request method={method}, url={url} failed with response.status_code={response.status_code}"
        )

    response_json = response.json()

    return response_json

def audit_logs_get_total_count_from_response(response_json):
    return response_json.get("data", {}).get("total_count")

def audit_logs_get_entities_from_response(response_json): 
    return response_json.get("data", {}).get("items") or []

def audit_logs_get_entities_to_process(entities, latest_audit_log_activity_time):
    # The "from" filter works like ">=", so we have to filter out the "=" value.
    return [entity for entity in entities if datetime.fromisoformat(entity.get("activity_time")) > latest_audit_log_activity_time]

def audit_logs_get_api_url(helper):
    path = "/api/users/audit"
    global_orca_host_url = helper.get_global_setting("host_url")
    url = urljoin(global_orca_host_url, path)
    return urlparse(url)._replace(scheme="https").geturl() # TODO?

def audit_logs_get_latest_activity_time(helper):
    _encoded_iso = helper.get_check_point(AUDIT_LOGS_LATEST_ACTIVITY_TIME_CHECK_POINT_STRING)
    if not _encoded_iso:
        return None
    return datetime.fromisoformat(base64decode(_encoded_iso))

def audit_logs_set_latest_activity_time(helper, _datetime):
    _encoded = base64encode(_datetime.isoformat())
    helper.save_check_point(AUDIT_LOGS_LATEST_ACTIVITY_TIME_CHECK_POINT_STRING, _encoded)

def create_hash(data: bytes) -> str:
    _hash = hashlib.new('md5', usedforsecurity=False)
    _hash.update(data)
    md5_hash = _hash.digest()
    base64_encoded = base64.b64encode(md5_hash).decode('ascii')
    return base64_encoded.rstrip('=')


def _process_cves(cves, helper, ew):
    saved = 0
    updated = 0
    duplicated = 0
    failed = 0
    for cve in cves:
        try:
            installed_package = cve.get('InstalledPackage')

            if installed_package:
                package_str = f"{installed_package['Name']}-{installed_package['Version']}"
            else:
                package_str = cve['Name']
            cve_key = create_hash(
                (
                    cve['CveId'] +
                    cve['Inventory']['AssetUniqueId'] +
                    package_str
                ).encode('utf-8')
            )
            cve_state = helper.get_check_point(cve_key)
            inventory = cve.pop('Inventory') #  Don't use Inventory in hash calculation
            cve_hash = create_hash(json.dumps(cve, sort_keys=True).encode("utf-8"))[:MAX_CHARS_IN_CVE_HASH]
            cve['Inventory'] = inventory
            if cve_state and cve_state == cve_hash:
                # skip processing. check point already exists and object not changed
                duplicated += 1
                continue
            _write_event(cve, helper, ew, "cves", time=int(time.time()))
            helper.save_check_point(cve_key, cve_hash)
            if cve_state:
                updated += 1
            else:
                saved += 1
        except Exception as e:
            helper.log_error(f"Failed to process CVE {cve.get('CveId')} due to {str(e)}")
            failed += 1
            continue
    return saved, updated, duplicated, failed


def _process_audit_logs(entities, helper, ew):
    for entity in entities:
        # CHECK

        entity_key = uuid.uuid3(
            uuid.NAMESPACE_DNS,
            f"{str(entity.get('user_name')) + str(entity.get('activity_time')) + str(entity.get('action'))}",
        )

        # check
        entity_state = helper.get_check_point(str(entity_key))
        # check
        _hash = hashlib.new('md5', usedforsecurity=False)
        _hash.update(json.dumps(entity, sort_keys=True).encode("utf-8"))
        entity_md5 = _hash.hexdigest()

        if not entity_state or entity_state != entity_md5:
            # create new check point
            helper.save_check_point(str(entity_key), entity_md5)
        if entity_state == entity_md5:
            # skip processing. check point already exists
            continue


        activity_time = entity.get("activity_time")
        try:
            ts = int(datetime.fromisoformat(activity_time).timestamp()) if activity_time else None
        except Exception:
            ts = None
        _write_event(entity, helper, ew, "audit_logs", time=ts)


def _write_event(entity, helper, ew, source, time=None):
    try:
        source_type = f"{helper.get_sourcetype()}:{source}"
        event = helper.new_event(
            source=helper.get_input_type(),
            index=helper.get_output_index(),
            sourcetype=source_type,
            data=json.dumps(entity),
            time=time,
        )
        ew.write_event(event)
    except ValueError:
        raise Exception("Failed to write event")


def validate_input(helper, definition):
    interval = int(definition.parameters.get("interval"))
    if interval > 86400 or interval < 300:
        raise ValueError("Interval should be between 300 and 86400 seconds.")
    pass


# sumologic, sentinel, datadog, splunk

def get_orca_host_url(host_url, path):
    url = urljoin(host_url, path)
    return urlparse(url)._replace(scheme="https").geturl()


def collect_cves_new_flow(helper, ew):
    global_orca_host_url = helper.get_global_setting("host_url")
    r_headers = get_headers(helper)

    serving_layer_base = get_orca_host_url(global_orca_host_url, "/api/serving-layer")
    datasets_url = f"{serving_layer_base}/datasets"
    body = {
        "query": {
            "models": ["VulnerabilityV2"],
            "type": "object_set",
            "with": {
                "keys": ["Inventory"],
                "models": ["Inventory"],
                "type": "object",
                "operator": "has",
            },
        },
        "additional_models[]": ["InstalledPackage", "Inventory"],
        "flat_json": True,
        "full_graph_fetch": {"enabled": True},
        "max_tier": 2,
    }

    create_response = helper.send_http_request(
        datasets_url,
        payload=body,
        headers=r_headers,
        method="POST",
        timeout=30.0,
    )
    if create_response.status_code >= 400:
        helper.log_error(
            f"CVE new flow: dataset creation failed, status_code={create_response.status_code}"
        )
        raise Exception(
            f"Failed to create dataset, status_code={create_response.status_code}"
        )

    dataset_id = create_response.json().get("dataset_id")
    if not dataset_id:
        helper.log_error("CVE new flow: create dataset response missing dataset_id")
        raise Exception("Create dataset response missing dataset_id")
    helper.log_info(f"CVE new flow: created dataset_id={dataset_id}")

    dataset_url = f"{datasets_url}/{dataset_id}"

    status = None
    status_json = None
    poll_interval = 30
    max_polls = 30
    for i in range(1, max_polls + 1):
        status_response = helper.send_http_request(
            dataset_url,
            headers=r_headers,
            method="GET",
            timeout=30.0,
        )
        if status_response.status_code == 404:
            # Dataset is not queryable for a short window right after creation.
            # Treat 404 as "not ready yet" and keep polling until the timeout.
            time.sleep(poll_interval)
            continue
        if status_response.status_code >= 400:
            helper.log_error(
                f"CVE new flow: poll failed, status_code={status_response.status_code}"
            )
            raise Exception(
                f"Failed to poll dataset {dataset_id}, status_code={status_response.status_code}"
            )
        status_json = status_response.json()
        status = status_json.get("status")
        if status in ("ready", "failed", "expired", "deleted"):
            break
        time.sleep(poll_interval)

    if status != "ready":
        helper.log_error(
            f"CVE new flow: dataset_id={dataset_id} did not reach ready (final status={status}), attempting cleanup"
        )
        try:
            helper.send_http_request(
                dataset_url, headers=r_headers, method="DELETE", timeout=30.0
            )
        except Exception as cleanup_err:
            helper.log_error(
                f"CVE new flow: failed to clean up dataset {dataset_id} after non-ready status: {cleanup_err}"
            )
        raise Exception(
            f"Dataset {dataset_id} did not reach ready (final status: {status})"
        )

    total_pages = status_json.get("total_pages", 0) or 0

    saved = 0
    updated = 0
    duplicated = 0
    failed = 0

    try:
        for page in range(total_pages):
            page_url = f"{dataset_url}/pages/{page}"
            page_data = None
            for attempt in range(1, 6):
                try:
                    page_response = helper.send_http_request(
                        page_url,
                        headers=r_headers,
                        method="GET",
                        timeout=180.0,
                    )
                    if page_response.status_code < 400:
                        page_data = page_response.json()
                        break
                    helper.log_error(
                        f"CVE new flow: page {page} attempt {attempt} failed, status_code={page_response.status_code}"
                    )
                except Exception as e:
                    helper.log_error(
                        f"CVE new flow: page {page} attempt {attempt} failed: {e}"
                    )
                time.sleep(attempt * 2)

            page_saved, page_updated, page_duplicated, page_failed = _process_cves(
                page_data, helper, ew
            )
            saved += page_saved
            updated += page_updated
            duplicated += page_duplicated
            failed += page_failed
    finally:
        try:
            delete_response = helper.send_http_request(
                dataset_url,
                headers=r_headers,
                method="DELETE",
                timeout=30.0,
            )
            helper.log_info(
                f"CVE new flow: deleted dataset_id={dataset_id}, status_code={delete_response.status_code}"
            )
        except Exception as e:
            helper.log_error(
                f"CVE new flow: failed to delete dataset {dataset_id}: {e}"
            )

    helper.log_info(
        f"CVE new flow: collection summary - saved={saved}, updated={updated}, "
        f"duplicated={duplicated}, failed={failed}"
    )


def collect_audit_logs_legacy(helper, ew):
    latest_audit_log_activity_time = None
    total_check_point_string = "audit_logs_total_parsed"

    audit_logs_api_url = audit_logs_get_api_url(helper)
    r_headers = get_headers(helper)

    bunch_size = 100
    index = 0
    collecting = True

    r_parameters = {"limit": 1, "start_at_index": 0 }
    orca_total = audit_logs_get_total_count_from_response(request(helper, method="GET", url=audit_logs_api_url, parameters=r_parameters, headers=r_headers))

    splunk_total = helper.get_check_point(total_check_point_string) or 0

    # we can't parse more then we have
    # maybe some audit logs were deleted
    if orca_total < splunk_total:
        splunk_total = 0
        helper.save_check_point(total_check_point_string, 0)

    while collecting:
        skip = bunch_size * index
        r_parameters = {"limit": bunch_size, "start_at_index": skip}
        index += 1

        entities = audit_logs_get_entities_from_response(request(helper=helper, method="GET", url=audit_logs_api_url, parameters=r_parameters, headers=r_headers))
        activity_times = list(map(lambda e: datetime.fromisoformat(e.get('activity_time')), entities))

        if latest_audit_log_activity_time:
            activity_times.append(latest_audit_log_activity_time)

        latest_audit_log_activity_time = max(activity_times)

        _process_audit_logs(entities, helper, ew)

        if len(entities) < bunch_size or skip >= (orca_total - splunk_total):
            collecting = False
            helper.save_check_point(total_check_point_string, orca_total)
            audit_logs_set_latest_activity_time(helper, latest_audit_log_activity_time)


def collect_audit_logs(helper, ew):
    latest_audit_log_activity_time = audit_logs_get_latest_activity_time(helper)

    if not latest_audit_log_activity_time:
        collect_audit_logs_legacy(helper, ew)
    else:
        process = True
        limit, offset = 100, 0
        audit_logs_api_url = audit_logs_get_api_url(helper)
        r_headers = get_headers(helper)

        current_audit_log_activity_time = latest_audit_log_activity_time

        while process:
            r_parameters = {"limit": limit, "start_at_index": offset, "ordering": "create_time", "from": current_audit_log_activity_time.isoformat()}
            response = request(helper=helper, url=audit_logs_api_url, method="GET", headers=r_headers, parameters=r_parameters)

            entities = audit_logs_get_entities_from_response(response)
            entities_to_process = audit_logs_get_entities_to_process(entities, current_audit_log_activity_time)

            if len(entities_to_process) == 0:
                process = False
                if current_audit_log_activity_time > latest_audit_log_activity_time:
                    audit_logs_set_latest_activity_time(helper, current_audit_log_activity_time)
            
            else:
                current_audit_log_activity_time = max(list(map(lambda entity: datetime.fromisoformat(entity.get("activity_time")), entities_to_process)))
                for entity in entities_to_process:
                    activity_time = entity.get("activity_time")
                    try:
                        ts = int(datetime.fromisoformat(activity_time).timestamp()) if activity_time else None
                    except Exception:
                        ts = None
                    _write_event(entity, helper, ew, "audit_logs", time=ts)


def collect_events(helper, ew):
    opt_data_type = helper.get_arg("data_type")
    if opt_data_type == "cves":
        collect_cves_new_flow(helper, ew)
    if opt_data_type == "audit_logs":
        collect_audit_logs(helper, ew)
