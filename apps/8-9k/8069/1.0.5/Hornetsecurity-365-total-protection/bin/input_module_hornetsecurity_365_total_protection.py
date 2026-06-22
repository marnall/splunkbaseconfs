# encoding = utf-8

import os
import sys
import time
import datetime
import json
from email.header import decode_header

def validate_input(helper, definition):
    opt_apikey = definition.parameters.get('apikey', None)
    opt_domain_or_email_address = definition.parameters.get('domain_or_email_address', None)
    opt_direction = definition.parameters.get('direction', None)

    if not opt_apikey:
        raise ValueError("ApiKey is required")
    if not opt_domain_or_email_address:
        raise ValueError("Domain or Email Address is required")
    if opt_direction and opt_direction not in ("inbound_outbound", "inbound", "outbound"):
        raise ValueError("Direction must be one of: Inbound/Outbound, Inbound, Outbound")

    return True

def collect_events(helper, ew):
    api_key = helper.get_arg('apikey')
    scope = helper.get_arg('domain_or_email_address')
    direction = helper.get_arg('direction')
    interval = int(helper.get_arg('interval'))
    limit = 5000
    base_url = "https://cp.hornetsecurity.com/api/v0"

    stanza_name = helper.get_input_stanza()
    try:
        stanza_names = helper.get_input_stanza_names()
        stanza_key = stanza_names[0] if stanza_names else str(scope)
    except Exception:
        stanza_key = str(scope)

    checkpoint_key = f"hornet_last_fetch_time::{stanza_key}"

    def get_headers():
        return {
            'Content-Type': 'application/json',
            'App-ID': '2539799398',
            'Authorization': f"Token {api_key}"
        }

    def send_post(path, payload):
        url = f"{base_url}{path}"
        try:
            response = helper.send_http_request(url, method="POST", payload=payload, headers=get_headers(), use_proxy=True)
            status = response.status_code
            text = response.text
            try:
                resp_json = response.json()
            except Exception:
                resp_json = None
            return status, resp_json, text
        except Exception as exc:
            helper.log_error(f"HTTP POST error for {url}: {exc}")
            return None, None, None

    def send_get(path, params=None):
        url = f"{base_url}{path}"
        try:
            response = helper.send_http_request(url, method="GET", parameters=params, headers=get_headers(), use_proxy=True)
            status = response.status_code
            try:
                resp_json = response.json()
            except Exception:
                resp_json = None
            return status, resp_json
        except Exception as exc:
            helper.log_error(f"HTTP GET error for {url}: {exc}")
            return None, None

    def get_object_id(obj):
        # IF OBJ DIGITS -> RETURN INT
        if str(obj).isdigit():
            return int(obj)
        # ELSE GET ID FROM NAME
        status, resp_json = send_get("/object/", params={"name": obj})
        if status == 200 and resp_json:
            return resp_json.get('object_id', 0)
        else:
            helper.log_warning(f"get_object_id failed for {obj} status={status} resp={resp_json}")
        return 0

    def get_direction_payload(direction):
        if str(direction).lower() == "inbound_outbound":
            return ""
        elif str(direction).lower() == "inbound":
            return '"direction": [1],'
        elif str(direction).lower() == "outbound":
            return '"direction": [2],'
        return ""



    def decode_subject(raw_subject):
        parts = decode_header(raw_subject)
        decoded = []
        for part, enc in parts:
            if isinstance(part, bytes):
                enc = enc or 'utf-8'
                decoded.append(part.decode(enc, errors='replace'))
            else:
                decoded.append(part)
        return ''.join(decoded)

    def build_email_event(object_id, email):
        # ATTACHMENTS
        attachments_text = "yes" if email.get('attachments') else "no"
        size_value = None
        size_unit = None
        try:
            size_value = email.get('size', {}).get('value')
            size_unit = email.get('size', {}).get('unit')
        except Exception:
            pass

        # ACTION
        action_text = "no action"
        try:
            if email.get('last_remediation_actions'):
                # IF LIST, TAKE FIRST
                first = email['last_remediation_actions'][0] if len(email['last_remediation_actions']) > 0 else None
                if first:
                    action_text = first
        except Exception:
            action_text = "no action"

        # STATUS
        status_text = ""
        try:
            if email.get('status') and email['status'].get('text'):
                if email['status'].get('text') == "No status":
                    status_text = "None"
                else:
                    status_text = email['status'].get('text')
            else:
                status_text = (email.get('status') and email.get('status').get('text')) or ""
        except Exception:
            status_text = ""

        # DATE FORMATTING
        formatted_date = email.get('date', '')
        if formatted_date:
            formatted_date = formatted_date.replace("T", " ").split("Z")[0][:-3]

        # DIRECTION/FROM/TO
        direction_text = "Inbound" if email.get('direction') == 1 else "Outbound"
        if direction_text == "Inbound":
            from_text = email.get('comm_partner', '')
            to_text = email.get('owner', '')
        else:
            from_text = email.get('owner', '')
            to_text = email.get('comm_partner', '')

        # CLASSIFICATION
        classification_text = "Unknown"
        try:
            if email.get('classification'):
                classification_text = email['classification'].get('text', '').capitalize()
        except Exception:
            classification_text = "Unknown"

        # EMAIL SIZE
        size_str = "Unknown"
        if size_value is not None and size_unit:
            try:
                size_str = f"{round(float(size_value), 2)} {size_unit}"
            except Exception:
                size_str = f"{size_value} {size_unit}"

        # EMAIL DATA
        email_data = {
            "msg_id": email.get('msg_id', ''),
            "message_id": email.get('message_id', ''),
            "date": formatted_date,
            "direction": direction_text,
            "from": from_text,
            "to": to_text,
            "subject": decode_subject(email.get('subject', '')),
            "action": (action_text.capitalize() if action_text else "No action"),
            "attachments": attachments_text,
            "attachmentsList": email.get('attachments', []),
            "classification": classification_text,
            "reason": email.get('reason', ''),
            "reason_intern": email.get('reason_intern', ''),
            "gateway": email.get('gateway', ''),
            "source_hostname": email.get('source_hostname', ''),
            "source_ip": email.get('source_ip', ''),
            "destination_hostname": email.get('destination_hostname', ''),
            "destination_ip": email.get('destination_ip', ''),
            "incoming_encryption": (email.get('crypt_type_in') or {}).get('text', '') if email.get('crypt_type_in') else "None",
            "outgoing_encryption": (email.get('crypt_type_out') or {}).get('text', '') if email.get('crypt_type_out') else "None",
            "private": email.get('private', False),
            "smtp_dialog": email.get('smtp_dialog', ''),
            "smtp_status": email.get('smtp_status', ''),
            "smtp_status_code": email.get('smtp_status_code', ''),
            "has_url_rewritten": email.get('has_url_rewritten', False),
            "status": (status_text.capitalize() if status_text else "None"),
            "is_archived": email.get('is_archived', False),
            "size": size_str
        }

        return email_data

    #* BEGIN COLLECTION FLOW
    try:
        # LOAD CHECKPOINT
        last_fetch = helper.get_check_point(checkpoint_key)
        if last_fetch:
            try:
                checkpoint_data = json.loads(last_fetch)
                last_seen_time = checkpoint_data.get("last_time")
                previous_ids = set(checkpoint_data.get("last_ids", []))
            except Exception:
                last_seen_time = None
                previous_ids = set()
        else:
            last_seen_time = None
            previous_ids = set()

        # IF NO LAST FETCH TIME
        if not last_seen_time:
            last_seen_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
            helper.log_info(f"No checkpoint found for {checkpoint_key}, starting from last 2h: {last_seen_time}")
            previous_ids = set()

        # RESOLVE OBJECT_ID
        object_id = get_object_id(scope)
        if object_id == 0:
            helper.log_error(f"Could not resolve object_id for scope '{scope}'. Aborting this run.")
            return

        last_dt = datetime.datetime.strptime(last_seen_time, "%Y-%m-%dT%H:%M:%SZ")
        last_dt = last_dt.replace(tzinfo=datetime.timezone.utc)

        # SET DATE WINDOW
        lag = datetime.timedelta(seconds=interval + 300)
        date_from = (last_dt - lag).strftime("%Y-%m-%dT%H:%M:%SZ")
        date_to = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        helper.log_info(f"Fetching emails for object_id={object_id} from {date_from} UTC "
                        f"(local: {(last_dt - lag).astimezone()}) to {date_to} UTC "
                        f"(local: {datetime.datetime.now(datetime.timezone.utc).astimezone()})")

        # LOOP
        offset = 0
        all_fetched = 0
        new_last_seen_time = last_seen_time
        seen_ids = set(previous_ids)  

        while True:
            direction_payload = get_direction_payload(direction)
            payload = '{' + f'{direction_payload}"classification":[1,2,3,5,8,11,12],"date_from":"{date_from}","date_to":"{date_to}","cluster_id":0,"offset":{offset},"limit":{limit}' + '}'

            status, resp_json, _ = send_post(f"/emails/_search/?object_id={object_id}", payload)
            if status != 200 or not resp_json:
                helper.log_error(f"emails/_search failed status={status} resp={resp_json}")
                break

            emails = resp_json.get('emails', [])
            num_found = resp_json.get('num_found_items', 0)

            if not emails:
                helper.log_info("No emails in response; breaking pagination loop.")
                break

            # LOOP ON ALL EMAILS
            for email in emails:
                msg_id = email.get("msg_id")
                
                if not msg_id:
                    helper.log_warning("Email skipped: no ID")
                    continue

                if msg_id in seen_ids or msg_id in previous_ids:
                    helper.log_info(f"Email skipped (duplicate): {msg_id}")
                    continue

                seen_ids.add(msg_id)

                # BUILD EVENT
                try:
                    email_event = build_email_event(object_id, email)
                except Exception as e:
                    helper.log_error(f"Error building email event for ID {msg_id}: {e}")
                    continue

                # CREATE SPLUNK EVENT
                try:
                    event_data = json.dumps(email_event, ensure_ascii=False)
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype(),
                        data=event_data
                    )
                    ew.write_event(event)
                    all_fetched += 1
                except Exception as e:
                    helper.log_error(f"Error writing event to Splunk for ID {msg_id}: {e}")
                    continue

                # UPDATE LAST SEEN EMAIL TIME
                email_time = email.get("date")
                if email_time and (new_last_seen_time is None or email_time > new_last_seen_time):
                    new_last_seen_time = email_time

            offset += limit
            if offset >= num_found or len(emails) < limit:
                break

        # SAVE CHECKPOINT
        checkpoint_data = {
            "last_time": new_last_seen_time or date_to,
            "last_ids": list(seen_ids)[-1000:]
        }
        helper.save_check_point(checkpoint_key, json.dumps(checkpoint_data))
        helper.log_info(f"Total emails fetched this run: {all_fetched}")

    except Exception as e:
        helper.log_error(f"Unexpected error in collect_events: {e}")
        return