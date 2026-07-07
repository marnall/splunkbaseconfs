""" Module for utility"""

import base64
import datetime
import hashlib
import json
import time

import requests
import seccure
from config import (LOG_TYPE_CHECKPOINT_KEY, LOG_TYPE_MIN_COUNT, LOG_TYPE_UPDATE_INTERVAL_SECONDS,
                    cim_map_dict, log_type_list)
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from silo_exceptions import (InvalidAPIKeyError, InvalidJSONError, ResourceNotFoundError, ServerError)

API_HEADERS = {
    'Content-Type': 'application/json',
    'X-SSC-Application-Name': 'Splunk',
    'X-SSC-Application-Version': '1.0',
}


def make_api_payload(token, command_dict):
    """Build an API payload with setauth and a command.
    :param token: str, auth token.
    :param command_dict: dict, the command to include after setauth.
    :return: list of command dicts.
    """
    return [{"command": "setauth", "data": token}, command_dict]


def get_checkpoint_key(helper, log_type, options=None):
    """Generate input-specific checkpoint key.
    Format: {stanza[:15]}_{org[:15]}_{LOG_TYPE}_{hash6}_seq_id
    Includes 6-char hash of full stanza+org+type to guarantee uniqueness.
    """
    stanza_name = helper.get_input_stanza_names()
    if isinstance(stanza_name, list):
        stanza_name = stanza_name[0] if stanza_name else ""
    stanza_name = stanza_name.replace("://", "_").replace("/", "_").replace(" ", "_")

    org_name = ""
    if options and options.get("organization_name"):
        org_name = options.get("organization_name").replace(" ", "_").replace("/", "_")

    # Create hash from full values to guarantee uniqueness
    key_source = "{}|{}|{}".format(stanza_name, org_name, log_type.upper())
    key_hash = hashlib.sha256(key_source.encode()).hexdigest()[:6]

    # Truncate names for readability, hash ensures uniqueness
    stanza_prefix = stanza_name[:15] if stanza_name else ""
    org_prefix = org_name[:15] if org_name else ""

    if org_prefix:
        return "{}_{}_{}_{}_seq_id".format(stanza_prefix, org_prefix, log_type.upper(), key_hash)
    return "{}_{}_{}_seq_id".format(stanza_prefix, log_type.upper(), key_hash)


def create_checkpoint_state(seq_id, create_ts=None):
    """Create checkpoint dict with seq_id and human-readable timestamp."""
    if create_ts:
        try:
            ts = datetime.datetime.utcfromtimestamp(float(create_ts)).isoformat() + "Z"
        except (ValueError, TypeError):
            ts = datetime.datetime.utcnow().isoformat() + "Z"
    else:
        ts = datetime.datetime.utcnow().isoformat() + "Z"
    return {"seq_id": seq_id, "timestamp": ts}


def get_seq_id_from_checkpoint(checkpoint_value):
    """Extract seq_id, supporting old (int) and new (dict) formats."""
    if checkpoint_value is None:
        return None
    if isinstance(checkpoint_value, dict):
        return checkpoint_value.get("seq_id")
    try:
        return int(checkpoint_value)
    except (ValueError, TypeError):
        return None


def migrate_checkpoint_if_needed(helper, log_type, options):
    """
    One-time migration from old global checkpoint to new input-specific key.
    Runs automatically on first collection after upgrade.
    """
    old_key = "{}_seq_id".format(log_type.upper())
    new_key = get_checkpoint_key(helper, log_type, options)

    # Skip if new key already exists (already migrated or fresh start)
    if helper.get_check_point(new_key) is not None:
        return

    # Skip if no old checkpoint to migrate
    old_value = helper.get_check_point(old_key)
    if old_value is None:
        return

    # Copy old value to new key (one-time)
    old_seq_id = get_seq_id_from_checkpoint(old_value)
    if old_seq_id is not None:
        new_state = create_checkpoint_state(old_seq_id)
        helper.save_check_point(new_key, new_state)
        helper.log_info("Migrated checkpoint {} -> {}: seq_id={}".format(
            old_key, new_key, old_seq_id))


def get_json_from_url(url, headers=None, params=None, proxy=None, helper=None):
    """Creates json response from url

    :param url: str, url to call
    :param headers: dict, Optional custom headers
    :param params: dict, url parameters
    :param proxy: dict
    :param helper: helper object of splunk.
    :return: response in json.
    """
    headers = headers or {}
    params = params or {}

    try:
        req = helper.send_http_request(url, 'POST',
                                       headers=headers, payload=params,
                                       use_proxy=bool(proxy), timeout=600.0)
    except requests.exceptions.ConnectionError as error:
        raise Exception("Error in connecting to splunk request method"
                        " {}\nProxy: {}.\n{}".format(url, proxy, str(error)))

    try:
        response = req.json()

    except ValueError:
        raise InvalidJSONError("URL: {}\nstatus code: {}\nContent: {}".format(
            url,
            req.status_code,
            req.content
        ))

    if req.status_code == 401:
        raise InvalidAPIKeyError("URL: {}\nparams: {}\nstatus code:"
                                 " {}\nContent: {}".format(url, params,
                                                           req.status_code,
                                                           req.content))

    if req.status_code == 404:
        raise ResourceNotFoundError("URL: {}\nstatus code: "
                                    "{}\nContent: {}".format(url,
                                                             req.status_code,
                                                             req.content))

    if req.status_code in [502, 500]:
        raise ServerError("URL: {}\nstatus code: "
                          "{}\nContent: {}".format(url,
                                                   req.status_code,
                                                   req.content))

    if req.status_code != 200:
        raise requests.RequestException("URL: {} Received status {} with"
                                        " content {}.".format(url,
                                                              req.status_code,
                                                              req.content))

    return response


def connect_to_silo(log_type, options, helper,
                    next_seq=None, start_seq_flag=None):
    """Connect to silo api and returns json data
    :param log_type: log type
    :param options: a dictionary containing token, organisation name etc.
    :param helper: helper object of splunk
    :param next_seq: next sequence of logs.
    :param start_seq_flag: start sequence flag
    :return: response in json.
    """
    orig_url = options.get('authentic8_api_url')
    url = modify_url(orig_url, helper)
    token = options.get("auth_token")
    org_name = options.get("organization_name")
    proxy = options.get("proxy")
    log_seq_id = get_checkpoint_key(helper, log_type, options)
    checkpoint_value = helper.get_check_point(log_seq_id)
    old_seq_id = get_seq_id_from_checkpoint(checkpoint_value)
    seq_id = int(old_seq_id) + 1 if old_seq_id else 0
    if next_seq:
        seq_id = next_seq
    helper.log_info(" Starting sequence id is {}".format(seq_id))
    if start_seq_flag:
        command = {"command": "extractlog", "start_seq": 0,
                   "end_seq": seq_id, "org": org_name,
                   "type": log_type}
    else:
        command = {"command": "extractlog", "start_seq": seq_id,
                   "org": org_name, "type": log_type}
    payload = make_api_payload(token, command)
    response = get_json_from_url(url, API_HEADERS,
                                 json.dumps(payload), proxy, helper)
    return response


def modify_url(url, helper):
    """
    Modifying the url.
    :param url: Authentic8 url.
    :param helper: Splunk helper object.
    :return: url string.
    """
    if url.startswith("http://"):
        url = url.replace("http://", "https://", 1)
        helper.log_debug("http replaced with https")
    elif url.startswith("https://"):
        helper.log_debug("Url is valid.")
    else:
        helper.log_debug("Invalid url")
        helper.log_debug("Setting current url to none and using the "
                         "default url for further processing.")
        url = "https://extapi.authentic8.com/api/"
    return url


def processing_auth8_logs(log_type, options, helper,
                          ew, start_seq_flag=None, old_key_name=None):
    """
    Processing authentic8 logs.
    :param log_type: Type of logs.
    :param options: Configuration dictionary.
    :param helper: Splunk helper object.
    :param ew: Splunk event writer.
    :param start_seq_flag:start seq flag.
    :param old_key_name: older key name.
    :return: None
    """
    # Migrate old checkpoint on first run after upgrade (one-time, no-op after)
    if not old_key_name:  # Only for normal processing, not lost-key recovery
        migrate_checkpoint_if_needed(helper, log_type, options)

    response_list = []
    log_list = []
    last_processed_seq_id = None
    last_processed_create_ts = None

    try:
        response = connect_to_silo(log_type, options, helper,
                                   start_seq_flag=start_seq_flag)
        if 'error' in response[1]:
            helper.log_error("API call failed: {}".format(response[1]['error']))
            return
        more_data = response[1].get('result').get('is_more')
        response_list.append(response)
        while more_data:
            helper.log_debug("More data is there{}".format(more_data))
            next_seq = response[1].get('result').get('next_seq')
            response = connect_to_silo(log_type, options, helper,
                                       next_seq=next_seq)
            more_data = response[1].get('result').get('is_more')
            response_list.append(response)
    except InvalidAPIKeyError:
        helper.log_error("API key is invalid or expired.Please "
                         "validate that your token is entered correctly")
        return
    except InvalidJSONError:
        helper.log_error("Data received from API is not in JSON format")
        return
    except ServerError:
        helper.log_error("Server error occurred while calling authentic8 API")
        return
    except Exception as error:
        helper.log_error("Error in  getting response "
                         "from authentic8 {}".format(error))
    else:
        try:
            for response in response_list:
                log_list.extend(response[1].get('result').get('logs'))
        except Exception as err:
            helper.log_error("getting exception as {}".format(err))
        else:
            if not log_list:
                helper.log_info("No data is available.")
            else:
                helper.log_info("Received {} logs of type {}".format(len(log_list), log_type))
            for log in log_list:
                if log_type == "ENC":
                    encryption_type = log.get('encryption_type')
                    key_name = log.get('key_name', 'UNKNOWN')

                    # Skipping other logs when older
                    # log is processing because newer log already processed.
                    if old_key_name and old_key_name != key_name:
                        continue
                    helper.log_debug("Processing ENC log seq_id={}, key_name={}, encryption_type={}".format(
                        log.get('seq_id'), key_name, encryption_type))
                    key_data = helper.get_check_point(key_name)
                    if not key_data:
                        helper.log_warning("Private key NOT FOUND for key_name='{}'. "
                                           "Skipping this log. Make sure the private key is "
                                           "stored with exactly this key name.".format(key_name))
                        lost_key_list = helper.get_check_point('lost_key')
                        if not lost_key_list:
                            helper.log_info("Inside lost key")
                            helper.save_check_point('lost_key', [key_name])
                        else:
                            if key_name not in lost_key_list:
                                helper.log_info("Inside ELSE lost key")
                                lost_key_list.append(key_name)
                                helper.save_check_point('lost_key',
                                                        lost_key_list)
                        continue
                    try:
                        helper.log_debug("Attempting decryption for seq_id={} with key_name='{}'".format(
                            log.get('seq_id'), key_name))
                        data = json.dumps(decrypt_log(log, encryption_type,
                                                      key_data, log_type))
                        write_to_splunk(helper, ew, data)
                        helper.log_debug("Successfully decrypted and wrote log seq_id={}".format(log.get('seq_id')))
                        if not old_key_name:
                            last_processed_seq_id = log['seq_id']
                            last_processed_create_ts = log.get('create_ts')
                    except seccure.IntegrityError as err:
                        helper.log_error("Private key is different "
                                         "for key name:- {}, "
                                         "getting error as {}"
                                         .format(key_name, err))
                    except ValueError:
                        helper.log_error("Invalid decryption key: {}".format(key_name))
                    except InvalidTag:
                        helper.log_error("Decryption failed, possibly wrong key used: {}".format(key_name))
                    except Exception as err:
                        helper.log_error("Getting error {} while decryption".
                                         format(err))
                else:
                    log = process_cim_mapping(log_type, log)
                    data = json.dumps(log)

                    write_to_splunk(helper, ew, data)
                    last_processed_seq_id = log['seq_id']
                    last_processed_create_ts = log.get('create_ts')

            # Save checkpoint once after all logs processed
            if last_processed_seq_id is not None:
                log_seq_id = get_checkpoint_key(helper, log_type, options)
                checkpoint_state = create_checkpoint_state(last_processed_seq_id, last_processed_create_ts)
                helper.save_check_point(log_seq_id, checkpoint_state)
                helper.log_info("Checkpoint saved: {}={}".format(log_seq_id, checkpoint_state))


def process_cim_mapping(log_type, log):
    """
    Processing log for cim mapping.
    :param log_type: log type.
    :param log: log dict.
    :return: updated log.
    """
    actual_log_type = log.get("type")
    log_type = actual_log_type if actual_log_type else log_type
    for key in cim_map_dict:
        if key not in log:
            continue
        if log_type.upper() == "A8SS" and key == 'client_ip':
            continue
        if log_type.upper() == "SESSION" and key == 'client_ip':
            log['src_ip'] = log.pop(key)
            continue
        if log_type.upper() == "UPLOAD" and key == 'url':
            log['dest'] = log.pop(key)
            continue
        log[cim_map_dict.get(key)] = log.pop(key)
    return log


def decrypt_log(log, encryption_type, key_data, log_type):
    """
    Decrypting the encrypted log.
    :param log: each enc log.
    :param encryption_type: Standard or Legacy (seccure).
    :param key_data: private key or passphrase.
    :param log_type: log type.
    :return: dictionary
    """
    if encryption_type == 'Standard':
        # Load cryptography key in PEM format and decrypt ciphertext to plaintext (Standard encryption type)
        private_key = serialization.load_pem_private_key(key_data.encode(), None)
        ciphertext = base64.b64decode(log['enc'])
        ephemeral_key = serialization.load_der_public_key(ciphertext[12:103])
        shared_key = private_key.exchange(ec.ECDH(), ephemeral_key)  # ECDHE key exchange
        derived_key = HKDF(algorithm=hashes.SHA384(), length=32, salt=None, info=None).derive(shared_key)
        decryptor = Cipher(algorithms.AES(derived_key), modes.GCM(ciphertext[:12], ciphertext[103:119])).decryptor()
        plaintext = decryptor.update(ciphertext[119:]) + decryptor.finalize()
        data = json.loads(plaintext.decode())
    else:
        data = json.loads(seccure.decrypt(base64.b64decode(log['enc']),
                                          passphrase=key_data.encode('utf-8'),
                                          curve='secp256r1/nistp256'))

    data = {'seq_id': log['seq_id'], 'create_ts': log['create_ts'], **data}
    data = process_cim_mapping(log_type, data)
    return data


def write_to_splunk(helper, ew, data):
    """
    Writing data into splunk.
    :param helper: splunk helper object.
    :param ew: Splunk event writer object.
    :param data: data
    :return: None
    """
    try:
        event = helper.new_event(source=helper.get_input_type(),
                                 index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(),
                                 data=data)
        ew.write_event(event)
    except Exception as err:
        helper.log_error("Getting error as {} while "
                         "dumping data in splunk".format(err))


def _save_update_checkpoint(helper, last_update_ts, version=None, log_types=None):
    """Save log type update checkpoint.
    :param helper: Splunk helper object.
    :param last_update_ts: float, timestamp of last update.
    :param version: str, version string from API response.
    :param log_types: list, updated log type list to persist across restarts.
    """
    state = {"last_update_ts": last_update_ts}
    if version is not None:
        state["version"] = version
    if log_types is not None:
        state["log_types"] = log_types
    helper.save_check_point(LOG_TYPE_CHECKPOINT_KEY, state)


def update_log_type_list(options, helper):
    """Update log_type_list from API if stale (older than 24h).

    Calls get_log_types API once per day. On success, updates
    config.log_type_list in-place so all importers see the change.
    On any failure, logs a warning, saves timestamp to avoid retry
    spam, and returns silently.

    :param options: dict with auth_token, authentic8_api_url, proxy keys.
    :param helper: Splunk helper object.
    """
    # Check if update is needed
    checkpoint = helper.get_check_point(LOG_TYPE_CHECKPOINT_KEY)
    if checkpoint and isinstance(checkpoint, dict):
        # Restore previously fetched types (each run is a new process)
        stored_types = checkpoint.get("log_types")
        if isinstance(stored_types, list) and len(stored_types) >= LOG_TYPE_MIN_COUNT:
            if stored_types != log_type_list:
                log_type_list[:] = stored_types
                helper.log_debug("Restored {} log types from checkpoint".format(len(stored_types)))

        last_update = checkpoint.get("last_update_ts", 0)
        if (time.time() - last_update) < LOG_TYPE_UPDATE_INTERVAL_SECONDS:
            helper.log_debug("Log type update skipped, last update {:.0f}s ago".format(
                time.time() - last_update))
            return

    # Preserve existing checkpoint data for error paths
    prev_version = checkpoint.get("version") if checkpoint and isinstance(checkpoint, dict) else None
    prev_types = checkpoint.get("log_types") if checkpoint and isinstance(checkpoint, dict) else None

    token = options.get("auth_token")
    orig_url = options.get("authentic8_api_url")
    url = modify_url(orig_url, helper)
    proxy = options.get("proxy")

    payload = make_api_payload(token, {"command": "get_log_types"})

    now = time.time()

    try:
        response = get_json_from_url(url, API_HEADERS, json.dumps(payload), proxy, helper)
    except Exception as err:
        helper.log_warning("Failed to fetch log types from API: {}".format(err))
        _save_update_checkpoint(helper, now, prev_version, prev_types)
        return

    # Validate response structure
    try:
        result = response[1].get("result", {})
        new_types = result.get("log_types")
        version = result.get("version")
        if not isinstance(new_types, list) or not isinstance(version, str):
            helper.log_warning("Invalid log types response structure")
            _save_update_checkpoint(helper, now, prev_version, prev_types)
            return
    except (IndexError, AttributeError, TypeError) as err:
        helper.log_warning("Malformed log types response: {}".format(err))
        _save_update_checkpoint(helper, now, prev_version, prev_types)
        return

    # Sanity check: response must contain a reasonable number of types
    if len(new_types) < LOG_TYPE_MIN_COUNT:
        helper.log_warning("API returned only {} log types, expected at least {}. Discarding.".format(
            len(new_types), LOG_TYPE_MIN_COUNT))
        _save_update_checkpoint(helper, now, prev_version, prev_types)
        return

    # Check if version changed
    stored_version = checkpoint.get("version") if checkpoint and isinstance(checkpoint, dict) else None
    if stored_version == version:
        helper.log_debug("Log type list version unchanged ({})".format(version))
        _save_update_checkpoint(helper, now, version, list(log_type_list))
        return

    # Update in-place so all importers see the change
    sorted_types = sorted([t.upper() for t in new_types])
    log_type_list[:] = sorted_types
    helper.log_info("Log type list updated to version {}: {} types".format(version, len(sorted_types)))
    _save_update_checkpoint(helper, now, version, sorted_types)
