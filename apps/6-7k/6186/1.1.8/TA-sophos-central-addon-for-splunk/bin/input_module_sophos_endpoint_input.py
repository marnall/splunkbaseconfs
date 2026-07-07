# encoding = utf-8
import ta_sophos_central_addon_for_splunk_declare  # noqa: F401

import json

import sophos_consts
from sophos_collect import SophosCollect
import sophos_common_utils as utils
from log_manager import setup_logging


_LOGGER = setup_logging("sophos_endpoint_input")


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def get_sophos_endpoints(
    sophos_collect_instance, tenant_id, host_name, next_key, page_limit
):
    parameters = {
        "pageTotal": True,
        "pageSize": page_limit,
        "fields": (
            "associatedPerson,"
            "encryption,"
            "group,"
            "health,"
            "hostname,"
            "id,"
            "ipv4Addresses,"
            "ipv6Addresses,"
            "lastSeenAt,"
            "macAddresses,"
            "os,"
            "tamperProtectionEnabled,"
            "tenant,"
            "type"
        ),
    }
    headers = {"X-Tenant-Id": tenant_id}

    if next_key:
        parameters["pageFromKey"] = next_key

    response = sophos_collect_instance._call_endpoint(
        sophos_url=host_name,
        endpoint=sophos_consts.ENDPOINT_ENDPOINT,
        parameters=parameters,
        headers=headers,
        method="GET",
        scheme_flag=True,
    )
    response = response.json() if response else {}
    return response


def collect_events(helper, ew):
    """To collect Sophos endpoints."""
    try:
        # Get Splunk session key
        session_key_of_splunk = helper.context_meta["session_key"]
        # Get API page limit
        page_limit = helper.get_arg("page_limit")
        # Get input name
        input_name = helper.get_input_stanza_names()
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
        account_type = conf_params.get("account_id_type")

        # Verify the account type
        if account_type == "tenant":
            host_name = conf_params["apihost_dataregion"]
            tenant_id = conf_params["account_id"]
            tenants_data.append((host_name, tenant_id))
        elif account_type in ["partner", "organization"]:
            bulk_tenants = utils.read_tenants(
                logger=_LOGGER, mod_input_name="Endpoints"
            )
            tenants_data = [
                (tenant.get("apiHost"), tenant.get("id"))
                for tenant in bulk_tenants["items"]
            ]
        else:
            _LOGGER.info(
                "Saved credentails are not for either tenant, partner or organization hence exiting.")
            exit()

        _LOGGER.info("Starting data collection process for {} input with {} page_limit.".format(
            input_name, str(page_limit)))
        for host_name, tenant_id in tenants_data:
            try:
                flag_first = True
                next_key = None
                while flag_first or (next_key is not None):
                    flag_first = False

                    # Collect Sophos Endpoints data
                    response = get_sophos_endpoints(
                        sophos_collect_instance,
                        tenant_id,
                        host_name,
                        next_key,
                        page_limit
                    )

                    if response:
                        _LOGGER.debug(
                            "Successfully fetched endpoints for tenant ID {} from Sophos.".format(
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
                        _LOGGER.info(
                            "Successfully ingested endpoints for tenant ID: {} and input: {}.".format(
                                tenant_id, input_name
                            )
                        )
                        pages = response.get("pages")
                        if pages:
                            next_key = pages.get("nextKey")
                    else:
                        _LOGGER.error(
                            "Failed to fetched endpoints for tenant ID {} from Sophos.".format(
                                tenant_id
                            )
                        )
            except Exception as exception:
                _LOGGER.error(
                    "Exception occurred while ingesting endpoints for tenant ID {} for {} input. Exception: {}".format(
                        tenant_id, input_name, str(exception)
                    )
                )
                continue
        _LOGGER.info("Data collection process is completed for {} input.".format(input_name))
    except Exception as exception:
        _LOGGER.error(
            "Exception occurred for {} input. Exception: {}".format(str(input_name), str(exception))
        )
