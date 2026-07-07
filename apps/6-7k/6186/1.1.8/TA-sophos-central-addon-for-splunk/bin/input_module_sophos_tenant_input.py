# encoding = utf-8

import os
from filelock import Timeout, FileLock
from log_manager import setup_logging
import json
from sophos_collect import SophosCollect
from sophos_consts import PARTNER_TENANT_ENDPOINT, ORGANIZATION_TENANT_ENDPOINT, LOCK_POLLING_INTERVAL, LOCK_TIMEOUT
import sophos_common_utils as utils

_LOGGER = setup_logging("sophos_tenant_input")


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def collect_events(helper, ew):
    """To collect Sophos tenants."""
    tenant_file_lock = FileLock(os.path.join(os.path.dirname(__file__), "..", "local", "tenant_data.json.lock"))
    tenant_file = os.path.join(os.path.dirname(__file__), "..", "local", "tenant_data.json")
    try:
        with tenant_file_lock.acquire(timeout=LOCK_TIMEOUT, poll_intervall=LOCK_POLLING_INTERVAL):
            _LOGGER.info("Tenants input has acquired lock on tenant_data.json.lock")
            session_key = helper.context_meta["session_key"]
            sophos_collect_instance = SophosCollect(session_key)
            sophos_configs = utils.get_sophos_config_params(session_key)

            try:
                sophos_collect_instance.check_credentials()
            except Exception as e:
                _LOGGER.error(str(e))
                tenant_file_lock.release(force=True)
                _LOGGER.info("Tenants input has released lock on tenant_data.json.lock")
                exit()

            id_type = sophos_configs.get("account_id_type", "").strip()

            tenant_endpoint = ""
            if id_type == "partner":
                account_type = "X-Partner-ID"
                tenant_endpoint = PARTNER_TENANT_ENDPOINT
            elif id_type == "organization":
                account_type = "X-Organization-ID"
                tenant_endpoint = ORGANIZATION_TENANT_ENDPOINT
            else:
                _LOGGER.info("Saved credentails are not for partner or organization hence exiting")
                tenant_file_lock.release(force=True)
                _LOGGER.info("Tenants input has released lock on tenant_data.json.lock")
                exit()

            base_hostname = sophos_configs.get("apihost_global", "").strip().replace("https://", "")
            x_account_id = sophos_configs.get("account_id", "").strip()

            if not all([id_type, base_hostname, x_account_id]):
                _LOGGER.error("missing either of these values (id_type, base_hostname, x_account_id)")
                tenant_file_lock.release(force=True)
                _LOGGER.info("Tenants input has released lock on tenant_data.json.lock")
                exit()

            headers = {
                account_type: x_account_id
            }
            page = 1
            params = {
                "pageSize": helper.get_arg("page_limit"),
                "page": page,
                "pageTotal": True,
            }
            response_data = None
            first = True
            data = {"items": []}
            while first or (response_data and response_data["pages"]["total"] > response_data["pages"]["current"]):
                first = False
                response = sophos_collect_instance._call_endpoint(
                    base_hostname,
                    tenant_endpoint,
                    method="get",
                    headers=headers,
                    parameters=params
                )
                if not response:
                    break
                response_data = response.json()
                data["items"].extend(response_data["items"])
                page += 1
                params["page"] = page

            if data["items"]:
                with open(tenant_file, "w") as fp:
                    json.dump(data, fp)
                    _LOGGER.info("Tenants file created!!")
            else:
                _LOGGER.error("Something went wrong while collecting tenants")
            tenant_file_lock.release(force=True)
            _LOGGER.info("Tenants input has released lock on tenant_data.json.lock")
    except Timeout:
        _LOGGER.error("Failed to acquire lock in given timeout.")
        tenant_file_lock.release(force=True)
        _LOGGER.info("Tenants input has released lock on tenant_data.json.lock")
        exit()
    except Exception as e:
        _LOGGER.error(str(e), stack_info=True, exc_info=True)
        tenant_file_lock.release(force=True)
        _LOGGER.info("Tenants input has released lock on tenant_data.json.lock")
        exit()
