import ta_lansweeper_declare  # noqa: F401, D100

import sys
import traceback
import time
import itertools
import concurrent.futures as cf
import common.command_utility as command_utility
from solnlib.credentials import CredentialNotExistException
from common.lansweeper_const import MAC, THREAD_COUNT
from common.lansweeper_collect import LansweeperCollect
from common.logger_manager import setup_logging
from splunklib.searchcommands import EventingCommand, Configuration, Option, validators, dispatch

_LOGGER = setup_logging("ta_lansweeper_lsmac_command")


@Configuration()
class LsMacCommand(EventingCommand):
    """
    lsmac - Generating and Transforming Command.

    This command can be used as generating command as well as transforming command,
    When used as generating command, it returns assets information of the given site ids,
    When used as transforming command, it will take macs from field="<mac_addresses>".

    **Syntax**::
    `|  lsmac site_ids="site_id_123" macs="00:50:56:8A:06:E4"`
    `|  lsmac site_ids="site_id_123" macs="00:50:56:8A:06:E4" max_results_per_site=50`
    `index=”main”| lsmac site_ids="site_id_123" field=mac_addr | table ....`
    `index=”main”| lsmac site_ids="site_id_123" field=mac_addr max_results_per_site=50 | table ....`

    **Description**::
    When used as generating command, lsmac command uses the MAC address or
    MAC addresses provided in macs field to return
    assets information from given Site id or Site ids, when used as transforming command,
    lsmac command uses the field to return assets information from given Site id or Site ids.
    Use "| kv" after lsmac query if want to extract key value pairs for events.
    """

    site_ids = Option(
        doc='''**Syntax:** **site_id=***<site ids>*
        **Description:** Site ids for which asset information needs to be retrieved from Lansweeper''',
        name='site_ids', require=True, validate=validators.List()
    )

    macs = Option(
        doc='''**Syntax:** **mac=***<mac_address>*
        **Description:** mac address(es) for which asset information needs to be retrieved from Lansweeper''',
        name='macs', require=False, validate=validators.List()
    )

    field = Option(
        doc='''**Syntax:** **field=***<mac_field>*
        **Description:** mac address(es) for which asset information needs to be retrieved from Lansweeper''',
        name='field', require=False,
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
    mac_list = None
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
                if isinstance(self.macs, list):
                    self.mac_list = [mac.strip() for mac in self.macs if mac]
                else:
                    self.mac_list = self.macs
                if self.field:
                    self.field_name = self.field.strip()

                # Validating options
                if self.mode == "Live" and not self.mac_list:
                    self.write_error("Please provide MAC Addresse(s) for the parameter \"macs\"")
                    exit(1)

                elif self.mode == "Local" and not self.field_name:
                    self.write_error("Please provide value for the parameter \"field\"")
                    exit(1)

                elif self.mode and self.mode not in ["Live", "Local"]:
                    self.write_error("Provided mode is invalid.")
                    exit(1)

                elif self.mac_list and self.field_name:
                    self.write_error("Please provide only one of the required parameters: \"field\" or \"macs\"")
                    exit(1)

                elif (not self.mac_list) and (not self.field_name):
                    self.write_error("Please provide one of the required parameters: \"field\" or \"macs\"")
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

                if self.mac_list and not self.field_name:
                    """This piece of code will work as generating command. It
                    validates mac addresses given in macs parameter,
                    site ids and fetches assets data."""

                    self.api_client.filter_list.extend(set(self.mac_list))
                    has_invalid = self.api_client.validate_mac()
                    if has_invalid:
                        self.write_warning("Provided Ips have some invalid values. Check log for details")

                elif self.field_name and not self.mac_list:
                    """This piece of code will work as transforming command. It
                    validates mac addresses given in field parameter,
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
                            future = tp.submit(self.api_client.fetch_data, site_id, MAC,
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
                                "source": "lsmac",
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
        super(LsMacCommand, self).__init__()


dispatch(LsMacCommand, sys.argv, sys.stdin, sys.stdout, __name__)
