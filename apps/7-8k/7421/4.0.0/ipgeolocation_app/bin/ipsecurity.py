import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Option,
    Configuration,
    validators
)

from api_request import query_ipsecurity_api
from parse_api_response import fill_null_ip_securities_for_api, parse_ipsecurity_api_response
from app_utils import get_null_ip_security_for_api
from app_utils import get_config
from app_utils import get_current_api_usage
from app_utils import get_mmdb_lookup_reader
from app_utils import get_logger
from app_utils import is_indexers


logger = get_logger("ipsecurity")
replicate_lookup = get_config("replicate_lookup") == "Yes"
method = get_config("method")
api_subscription_plan = get_config("api_subscription_plan")


@Configuration(distributed=replicate_lookup)
class IPSecurityLookup(StreamingCommand):
    
    prefix = Option(
        doc='''
        **Syntax:** **prefix=***<true|false>*
        **Description:** Prefix query name to all fields in the response.''',
        default=False, require=False, validate=validators.Boolean())
   

    def stream(self, records): 
        prefix = self.prefix
        fields = self.fieldnames
        
        if len(fields) > 1:
            prefix = True
        
        count = 0
        ip_addresses = []

        try:
            if method == "MMDB":
                self.write_error("`ipsecurity` command doesn't support MMDB lookup method. Use `ipgeolocation` command instead.")
            else:
                if api_subscription_plan != "PAID":
                    self.write_warning("Your subscription plan must be 'PAID' to search IP details through `ipsecurity` command.")
                else:
                    record_list = {}
                    total_requests = 0
                    current_api_usage_before_command = 0

                    if not is_indexers():
                        current_api_usage_before_command = get_current_api_usage(self)
                        logger.info("Used before running command : " + str(current_api_usage_before_command))

                    for record in records:
                        new_counter = 0

                        for field in fields:
                            if record.get(field):
                                ip_value = record.get(field).strip()

                                if ip_value != "":
                                    new_counter += 1
                                    ip_addresses.append(ip_value)
                                    count += 1
                                    total_requests += 1

                        if new_counter >= 1:
                            record_list[str(count)] = record
                        else:
                            null_ip_geolocation = get_null_ip_security_for_api(
                            )

                            for field in fields:
                                if prefix:
                                    record.update(prefix_keys(null_ip_geolocation, field))
                                else:
                                    record.update(null_ip_geolocation)

                            yield record

                        if count > 750:
                            count = 0

                            ip_securities = lookup_ip_security_from_api(
                                self,
                                ip_addresses,
                            )
                            ip_addresses.clear()

                            if bool(ip_securities):
                                temp = record_list
                                record_list = {}

                                for key, record_v1 in temp.items():
                                    try:
                                        for field in fields:
                                            if record_v1.get(field):
                                                if ip_securities[record_v1.get(field)]:
                                                    if prefix:
                                                        record_v1.update(prefix_keys(ip_securities[record_v1.get(field)], field))
                                                    else:
                                                        record_v1.update(ip_securities[record_v1.get(field)])
                                    except Exception as e:
                                        logger.error(e)
                                        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                                    yield record_v1
                            else:
                                self.write_warning("Something went wrong. Please check ipgeolocation.log for more information.")

                                temp = record_list
                                record_list = {}

                                for key, record_v1 in temp.items():
                                    yield record_v1

                    if count < 750:
                        ip_securities = lookup_ip_security_from_api(
                            self,
                            ip_addresses,
                        )

                        if bool(ip_securities):
                            temp = record_list
                            record_list = {}

                            for key, record_v1 in temp.items():
                                try:
                                    for field in fields:
                                        if record_v1.get(field):
                                            if ip_securities[record_v1.get(field)]:
                                                if prefix:
                                                    record_v1.update(prefix_keys(ip_securities[record_v1.get(field)], field))
                                                else:
                                                    record_v1.update(ip_securities[record_v1.get(field)])
                                except Exception as e:
                                    logger.error(e)
                                    logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))

                                yield record_v1
                        else:
                            self.write_warning("Something went wrong. Please check ipgeolocation.log for more information.")
                            temp = record_list
                            record_list = {}

                            for key, record_v1 in temp.items():
                                yield record_v1

                    if not is_indexers():
                        current_api_usage_after_command = get_current_api_usage(self)
                        logger.info("API usage after running command : " + str(current_api_usage_after_command))
                        diff = current_api_usage_after_command - current_api_usage_before_command
                        logger.info("API usage by command as per ipgeolocation.io " + str(diff))
                        logger.info("API usage by command as per app " + str(total_requests))
                        logger.info(
                            "API usage in ipgeolocation.io is updated in about 20 minutes. So, the usage as per ipgeolocation.io might be less than the usage as per command."
                        )
        except Exception as e:
            logger.error(e)
            logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))


def get_mmdb_readers(object, lookup_security: bool):
    geolocation_mmdb_reader = None
    security_mmdb_reader = None

    geolocation_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-geolocation")

    if lookup_security:
        security_mmdb_reader = get_mmdb_lookup_reader(object, "db-ip-security")

    return (geolocation_mmdb_reader, security_mmdb_reader)


def prefix_keys(ip_geolocation, prefix):
    prefixed_ip_geolocation = dict()

    for key, value in ip_geolocation.items():
        prefixed_ip_geolocation[prefix + "_" + key] = value
    
    return prefixed_ip_geolocation


def lookup_ip_security_from_api(
        object,
        ip_address_list: list,
    ):
    ip_securities = dict()

    try:
        response = query_ipsecurity_api(
            object,
            splunk_lib_util,
            ip_address_list,
        )

        if response is None:
            logger.error("Got none response from query_ipgeolocation_api")
            ip_securities = fill_null_ip_securities_for_api(
                ip_address_list,      
            )
        else:
            ip_securities = parse_ipsecurity_api_response(
                response,
            )
    except Exception as e:
        object.write_warning("Error during fetching data from ipgeolocation.io API. Check ipgeolocation.log file for troubleshooting.")
        object.write_warning(str(e))
        logger.error(e)
        logger.debug("\nTraceback:\n" + "".join(traceback.format_exc()))
    
    return ip_securities


if __name__ == "__main__":
    dispatch(IPSecurityLookup, sys.argv, sys.stdin, sys.stdout, __name__)
