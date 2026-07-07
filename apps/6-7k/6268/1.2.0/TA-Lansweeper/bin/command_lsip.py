import ta_lansweeper_declare  # noqa: F401, D100

import sys
import traceback
import time
import itertools
import concurrent.futures as cf
import common.command_utility as command_utility
from solnlib.credentials import CredentialNotExistException
from common.lansweeper_const import IP, THREAD_COUNT
from common.lansweeper_collect import LansweeperCollect
from common.logger_manager import setup_logging
from splunklib.searchcommands import EventingCommand, Configuration, Option, validators, dispatch

_LOGGER = setup_logging("ta_lansweeper_lsip_command")


@Configuration()
class LsIPCommand(EventingCommand):
    """
    lsip - Generating and Transforming Command.

    This command can be used as generating command as well as transforming command,
    When used as generating command, it returns assets information of the given site id,
    When used as transforming command, it will take ips from field="<ip_addresses>".

    **Syntax**::
    `|  lsip site_ids="site_id_123" ips="190.0.0.8"`
    `|  lsip site_ids="site_id_123" ip="190.0.0.8" max_results_per_site=50`
    `index=”main”| lsip site_ids="site_id_123" field=ip_addr | table ....`
    `index=”main”| lsip site_ids="site_id_123" field=ip_addr max_results_per_site=50 | table ....`

    **Description**::
    When used as generating command, lsip command uses the IP address or
    IP addresses provided in ip field to return
    assets information from given Site id or Site ids, when used as transforming command,
    lsip command uses the field to return assets information from given Site id or Site ids.
    Use "| kv" after lsip query if want to extract key value pairs for events.
    """

    site_ids = Option(
        doc='''**Syntax:** **site_id=***<site ids>*
        **Description:** Site ids for which asset information needs to be retrieved from Lansweeper''',
        name='site_ids', require=True, validate=validators.List()
    )

    ips = Option(
        doc='''**Syntax:** **ip=***<ip_address>*
        **Description:** IP address(es) for which asset information needs to be retrieved from Lansweeper''',
        name='ips', require=False, validate=validators.List()
    )

    field = Option(
        doc='''**Syntax:** **field=***<ip_field>*
        **Description:** IP address(es) for which asset information needs to be retrieved from Lansweeper''',
        name='field', require=False
    )

    max_results_per_site = Option(
        doc='''**Syntax:** **max_results_per_site=***<limit parameter>*
        **Description:** limit of events returned per site''',
        name='max_results_per_site', require=False, default=500
    )

    mode = Option(
        doc='''**Syntax:** **mode=***<mode parameter>*
        **Description:** mode of investigation''',
        name='mode', require=False
    )

    events = iter([])
    first_invocation = True
    field_name = None
    sites_list = None
    ip_list = None
    valid_sites = True
    start_time = time.time()

    def transform(self, events):
        """Transform method of Eventing Command."""
        try:
            if self.first_invocation:
                self.first_invocation = False
                _LOGGER.info("SID: {}".format(self.metadata.searchinfo.sid))

                if isinstance(self.site_ids, list):
                    self.sites_list = [site_id.strip() for site_id in self.site_ids if site_id]
                else:
                    self.sites_list = self.site_ids
                if isinstance(self.ips, list):
                    self.ip_list = [ip.strip() for ip in self.ips if ip]
                else:
                    self.ip_list = self.ips
                if self.field:
                    self.field_name = self.field.strip()

                # Validating options
                if self.mode == "Live" and not self.ip_list:
                    self.write_error("Please provide IP Addresse(s) for the parameter \"ips\"")
                    exit(1)

                elif self.mode == "Local" and not self.field_name:
                    self.write_error("Please provide value for the parameter \"field\"")
                    exit(1)

                elif self.mode and self.mode not in ["Live", "Local"]:
                    self.write_error("Provided mode is invalid.")
                    exit(1)

                elif self.ip_list and self.field_name:
                    self.write_error("Please provide only one of the required parameters: \"field\" or \"ips\"")
                    exit(1)

                elif (not self.ip_list) and (not self.field_name):
                    self.write_error("Please provide one of the required parameters: \"field\" or \"ips\"")
                    exit(1)
                else:
                    pass

                try:
                    self.max_results_per_site = int(self.max_results_per_site)
                    if self.max_results_per_site <= 0:
                        self.write_error("""Please provide an Integer greater than 0
                            or * to fetch all data for parameter \"max_results_per_site\".""")
                        exit(1)
                except ValueError:
                    if self.max_results_per_site and self.max_results_per_site.strip() == "*":
                        self.max_results_per_site = 0
                    else:
                        self.write_error("Please provide an Integer for parameter \"max_results_per_site\".")
                        exit(1)

            if not self._finished:
                # Combining event iterartors when command acts as streaming command
                if self.field_name:
                    self.events = itertools.chain(self.events, events)
            else:
                if self.field_name:
                    self.events = itertools.chain(self.events, events)
                    _LOGGER.debug("Time taken to combine chunked events : {} seconds"
                                  .format(time.time() - self.start_time))

                self.session_key = self.search_results_info.auth_token
                self.api_client = LansweeperCollect(self.session_key, _LOGGER)
                if self.ip_list and not self.field_name:
                    """This piece of code will work as generating command. It
                    validates ip addresses given in ips parameter,
                    site ids and fetches assets data."""

                    self.api_client.filter_list.extend(set(self.ip_list))
                    has_invalid = self.api_client.validate_ips()
                    if has_invalid:
                        self.write_warning("Provided IP Addresse(s) have some invalid values for the parameter \"ips. "
                                           "Check log for details.")

                elif self.field_name and not self.ip_list:
                    """This piece of code will work as transforming command. It
                    validates ip addresses given in field parameter,
                    site ids and fetches assets data."""

                    self.api_client.get_filter_details(self.events, self.field_name)

                else:
                    pass

                if "*" in self.sites_list:
                    self.sites_list = command_utility.get_all_site_id(self.session_key)
                else:
                    self.sites_list = set(self.sites_list)
                self.api_client.get_site_details()
                invalid_sites = []
                with cf.ThreadPoolExecutor(max_workers=THREAD_COUNT) as tp:
                    futures = []
                    for site_id in self.sites_list:
                        site_name = self.api_client.site_details.get(site_id, None)
                        if site_name:
                            future = tp.submit(self.api_client.fetch_data, site_id, IP,
                                               limit=self.max_results_per_site,
                                               site_name=site_name)
                            futures.append(future)
                        else:
                            invalid_sites.append(site_id)
                            if self.valid_sites:
                                self.valid_sites = False
                                self.write_warning(
                                    "Given site ids contain some invalid values. Check log for details."
                                )

                    for future in cf.as_completed(futures):
                        for item in future.result():
                            yield {
                                "_raw": item,
                                "sourcetype": "lansweeper:assets",
                                "source": "lsip",
                                "_time": int(time.time())
                            }
                if (not self.valid_sites):
                    _LOGGER.warning("Given site ids are invalid: {}".format(str(invalid_sites)))
        except TypeError as e:
            if (str(e) == "can only concatenate str (not \"NoneType\") to str"):
                self.write_error("Corrupted configurations found. "
                                 "Please delete Passwords.conf, ta_lansweeper_settings.conf "
                                 "& ta_lansweeper_account.conf files from the TA-Lansweeper/local. "
                                 "Please restart the Splunk instance and reconfigure the Proxy(if applicable) "
                                 "& the Account.")
            else:
                self.write_error(str(e))
            _LOGGER.error(traceback.format_exc())
        except CredentialNotExistException:
            self.write_error("Please configure the account first before running this command.")
            _LOGGER.error(traceback.format_exc())
        except Exception as e:
            self.write_error(str(e))
            _LOGGER.error(traceback.format_exc())
        _LOGGER.info("End of custom command."
                     "Total time taken : {} seconds".format(time.time() - self.start_time))

    def __init__(self):
        """Initialize custom command class."""
        super(LsIPCommand, self).__init__()


dispatch(LsIPCommand, sys.argv, sys.stdin, sys.stdout, __name__)
