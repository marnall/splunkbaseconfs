
# encoding = utf-8
import ta_sophos_central_addon_for_splunk_declare  # noqa: F401

import time
import json
from datetime import datetime

import sophos_consts
from sophos_collect import SophosCollect
import sophos_common_utils as utils
from log_manager import setup_logging

_LOGGER = setup_logging("sophos_alert_input")


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def get_sophos_alerts(sophos_collect_instance, time_from, time_to, tenant_id, host_name, page_limit):
    time_params = {
        "from": time_from,
        "to": time_to,
        "pageSize": page_limit,
    }
    headers = {
        "X-Tenant-Id": tenant_id
    }

    response = sophos_collect_instance._call_endpoint(
        sophos_url=host_name,
        endpoint=sophos_consts.ALERT_ENDPOINT,
        parameters=time_params,
        headers=headers,
        method="GET",
        scheme_flag=True,
    )
    response = response.json() if response else {}
    return response


def collect_events(helper, ew):
    """To collect Sophos alerts."""
    try:
        # Get input name
        input_name = helper.get_input_stanza_names()
        # Get Splunk session key
        session_key_of_splunk = helper.context_meta['session_key']
        # Get API page limit
        page_limit = helper.get_arg("page_limit")
        conf_params = utils.get_sophos_config_params(session_key_of_splunk)
        # Initialize SophosCollect Object
        sophos_collect_instance = SophosCollect(session_key_of_splunk)
        # Verify Sophos Configurations exist
        try:
            sophos_collect_instance.check_credentials()
        except Exception as e:
            _LOGGER.error(str(e))
            exit()

        tenants_data = []
        account_type = conf_params["account_id_type"]

        # Verify the account type
        if account_type == "tenant":
            host_name = conf_params["apihost_dataregion"]
            tenant_id = conf_params["account_id"]
            tenants_data.append((host_name, tenant_id))
        elif account_type in ["partner", "organization"]:
            bulk_tenants = utils.read_tenants(logger=_LOGGER, mod_input_name="Alerts")
            tenants_data = [(tenant.get("apiHost"), tenant.get("id")) for tenant in bulk_tenants["items"]]
        else:
            _LOGGER.info(
                "Saved credentails are not for either tenant, partner or organization hence exiting."
            )
            exit()

        # Fetch last stored checkpoint time
        checkpoint = helper.get_check_point(input_name)
        tenant_checkpoint = json.loads(checkpoint) if checkpoint else {}
        _LOGGER.info("Starting data collection process for {} input with {} page_limit.".format(
            input_name, str(page_limit)))
        for host_name, tenant_id in tenants_data:
            try:
                current_time = int(time.time())
                time_from = tenant_checkpoint.get(tenant_id, current_time - (30 * 24 * 60 * 60))
                time_from = datetime.utcfromtimestamp(time_from).isoformat() + "Z"
                time_to = datetime.utcfromtimestamp(current_time).isoformat() + "Z"

                # Collect Sophos Alerts data
                response = get_sophos_alerts(
                    sophos_collect_instance=sophos_collect_instance,
                    time_from=time_from,
                    time_to=time_to,
                    tenant_id=tenant_id,
                    host_name=host_name,
                    page_limit=page_limit
                )

                if response:
                    _LOGGER.debug(
                        "Successfully fetched alerts for tenant ID {} from Sophos.".format(
                            tenant_id
                        )
                    )

                    # Iterate over the response and index it in Splunk
                    for data in response.get("items", []):
                        event = helper.new_event(
                            source=helper.get_input_type(),
                            index=helper.get_output_index(),
                            sourcetype=helper.get_sourcetype(),
                            data=json.dumps(data),
                        )
                        ew.write_event(event)
                    _LOGGER.info("Successfully ingested alerts for tenant ID: {} and input: {}.".format(
                        tenant_id, input_name))

                    # Add checkpoint time of current tenant
                    tenant_checkpoint[tenant_id] = current_time + 1
                else:
                    _LOGGER.error(
                        "Failed to fetched alerts for tenant ID {} from Sophos.".format(
                            tenant_id
                        )
                    )

            except Exception as exception_ingest_alert:
                _LOGGER.error(
                    "Exception occurred while ingesting alerts for tenant ID {} and input {}. Exception: {}".format(
                        tenant_id, input_name, str(exception_ingest_alert)
                    )
                )
                continue

        # Store checkpoint time
        helper.save_check_point(input_name, json.dumps(tenant_checkpoint))
        _LOGGER.info("Checkpoint is updated for {} input.".format(input_name))
        _LOGGER.info("Data collection process is completed for {} input.".format(input_name))
    except Exception as exception:
        _LOGGER.error("Exception occurred for {} input. Exception: {}".format(
            input_name, str(exception)))
