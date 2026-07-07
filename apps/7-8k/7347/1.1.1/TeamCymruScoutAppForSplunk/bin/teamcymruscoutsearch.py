"""This file defines custom  command."""
import import_declare_test
import sys
import time
import traceback
import re
import json
import base64
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from cymru_helpers.logger_manager import setup_logging
from cymru_helpers.conf_helper import get_credentials
from cymru_helpers.rest_helper import RestHelper
from cymru_helpers.constants import DATE_REGEX

logger = setup_logging("ta_team_cymru_scout_search_command")


@Configuration()
class TeamCymruScoutSearchCommand(GeneratingCommand):
    """Team Cymru Scout search custom command class."""

    indicator_type = Option(require=True)
    indicators = Option(require=True)
    account_name = Option(require=True)
    start_date = Option(require=False, default="")
    end_date = Option(require=False, default="")

    def extract_tags(self, all_tags, prefix='', tags=None):
        """Extract tag values."""
        if tags is None:
            tags = []
        if all_tags is None:
            return "-"
        for item in all_tags:
            name = item['name']
            if item['children'] is None:
                tags.append(prefix + name)
            else:
                self.extract_tags(item['children'], prefix + name + '>', tags)
        return "   ".join(tags)

    def extract_communications(self, ip_response):
        """Extract Communications."""
        try:
            peers = ip_response.get("communications", {}).get("peers", {})
            if peers:
                for peer in peers:
                    top_services_ports_list = []
                    local_tags_list = []
                    peer_tags_list = []
                    peer_port_range = ""

                    if peer.get("local", {}).get("top_services", []):
                        for top_service in reversed(peer.get("local", {}).get("top_services", [])):
                            top_services_ports_list.append(top_service.get("port"))
                    if not top_services_ports_list:
                        top_services_ports_list = ["-"]
                    peer["local"]["top_services_ports_str"] = ", ".join(
                        str(item) for item in top_services_ports_list
                    )

                    if peer.get("local", {}).get("tags", []):
                        for local_tag in peer.get("local", {}).get("tags", []):
                            local_tags_list.append(local_tag.get("name"))
                    peer["local"]["local_tags_str"] = ", ".join(
                        str(item) for item in local_tags_list
                    )

                    if peer.get("peer", {}).get("tags", []):
                        for peer_tag in peer.get("peer", {}).get("tags", []):
                            peer_tags_list.append(peer_tag.get("name"))
                    peer["peer"]["peer_tags_str"] = ", ".join(
                        str(item) for item in peer_tags_list
                    )

                    peer["peer"]["country_codes_str"] = ", ".join(
                        str(item) for item in peer.get("peer", {}).get("country_codes", [])
                    )
                    peer["local"]["country_codes_str"] = ", ".join(
                        str(item) for item in peer.get("local", {}).get("country_codes", [])
                    )

                    min_port = peer.get("peer", {}).get("min_port")
                    max_port = peer.get("peer", {}).get("max_port")
                    unique_ports = peer.get("peer", {}).get("unique_ports")
                    if min_port == max_port:
                        peer_port_range = min_port
                    else:
                        peer_port_range = str(min_port) + "-" + str(max_port) + " (" + str(unique_ports) + ")"
                    peer["peer"]["peer_port_range"] = peer_port_range

                    peer["peer_str"] = json.dumps({"peer": peer.get("peer", {})})
                    peer["local_str"] = json.dumps({"local": peer.get("local", {})})

        except Exception as e:
            logger.error("Team Cymru Scout Error: Error Occured While extracting communications: {}".format(e))
            logger.debug(
                "Team Cymru Scout Debug: Error Occured While extracting communications: {}"
                .format(traceback.format_exc())
            )

    def extract_pdns_nameserver_child(self, ip_response):
        """Extract PDNS nameservers."""
        try:
            all_pdns = ip_response.get("pdns", {}).get("pdns", [])
            if all_pdns:
                for pdns in all_pdns:
                    if pdns.get("nameservers", []):
                        nameserver_list = []
                        for nameserver in pdns.get("nameservers", []):
                            if nameserver.get("nameservers", []):
                                nameserver["nameserver_child"] = ", ".join(
                                    str(item) for item in nameserver.get("nameservers", [])
                                )
                            nameserver_list.append(nameserver)
                        pdns["nameserver_str"] = json.dumps({"nameservers": nameserver_list})
                    else:
                        pdns["nameserver_str"] = ""
        except Exception as e:
            logger.error("Team Cymru Scout Error: Error Occured While extracting PDNS: {}".format(e))
            logger.debug(
                "Team Cymru Scout Debug: Error Occured While extracting PDNS: {}"
                .format(traceback.format_exc())
            )

    def extract_certs_altnames(self, ip_response):
        """Extract Certifications Alt names."""
        try:
            certs = ip_response.get("x509", {}).get("x509", {})
            if certs:
                for cert in certs:
                    cert["altnames_str"] = ", ".join(
                        str(item) for item in cert.get("altnames", [])
                    )
        except Exception as e:
            logger.error("Team Cymru Scout Error: Error Occured While extracting PDNS: {}".format(e))
            logger.debug(
                "Team Cymru Scout Debug: Error Occured While extracting PDNS: {}"
                .format(traceback.format_exc())
            )

    def validate_params(self):
        """Validate Indicator Type."""
        if self.indicators == "" or self.indicator_type == "" or self.account_name == "":
            logger.error("Team Cymru Scout Error: Invalid Parameters.")
            logger.debug(
                "Team Cymru Scout Debug: Invalid Parameters : {}"
                .format(traceback.format_exc())
            )
            self.write_error("Invalid Parameters.")
            exit(1)
        if self.indicator_type not in ["ip", "domain"]:
            logger.error("Team Cymru Scout Error: Invalid Indicator Type.")
            logger.debug(
                "Team Cymru Scout Debug: Invalid Indicator Type : {}"
                .format(traceback.format_exc())
            )
            self.write_error("Invalid Indicator Type.")
            exit(1)
        if not (re.match(DATE_REGEX, self.start_date) and re.match(DATE_REGEX, self.end_date)):
            logger.warning(
                f"Team Cymru Scout Warning: Provided Start Date: {self.start_date} or "
                f"End Date: {self.end_date} are invalid. Hence removing these params."
            )
            self.start_date = ""
            self.end_date = ""

    def generate(self):
        """Generate Events Function."""
        logger.info("Team Cymru Scout Info: Started Custom Command Script Execution.")
        logger.debug("Generating Events")

        self.start_date = self.start_date.strip()
        self.end_date = self.end_date.strip()
        self.validate_params()
        start_time = time.time()
        self.session_key = self.search_results_info.auth_token

        cymru_config = {
            "session_key": self.session_key,
            "api_type": "details",
        }
        account_info = get_credentials(
            session_key=self.session_key,
            account_name=self.account_name
        )
        cymru_config.update(account_info)
        self.indicators = self.indicators.replace("[", "").replace("]", "")

        try:
            if self.indicator_type == "ip":
                cymru_config.update({"indicator_type": "ip"})
                cymru_config.update({"indicators": self.indicators})
                cymru_rest_helper = RestHelper(cymru_config, logger)
                response = cymru_rest_helper.get_data(self.start_date, self.end_date)
            else:
                cymru_config.update({"indicator_type": "domain"})
                cymru_config.update({"indicators": self.indicators})
                cymru_rest_helper = RestHelper(cymru_config, logger)
                response = cymru_rest_helper.get_data()

            for res in response:
                if self.indicator_type == "ip":
                    res['team_cymru_tags'] = self.extract_tags(res.get("summary", {}).get("tags", []))
                    self.extract_communications(res)
                    self.extract_pdns_nameserver_child(res)
                    self.extract_certs_altnames(res)
                yield {'_time': time.time(), "_raw": res}
        except Exception as e:
            logger.error("Team Cymru Scout Error: Error Occured While Fetching Data: {}".format(e))
            logger.debug(
                "Team Cymru Scout Debug: Error Occured While Fetching Data : {}"
                .format(traceback.format_exc())
            )
            self.write_error('Unexpected Error Ocuued While Fetching Data. Check logs for more details.')
        logger.info(
            "Team Cymru Scout Info: Completed the Execution of Custom Command Script. "
            "Time Taken: {} minutes".format((time.time() - start_time) / 60)
        )


dispatch(TeamCymruScoutSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
