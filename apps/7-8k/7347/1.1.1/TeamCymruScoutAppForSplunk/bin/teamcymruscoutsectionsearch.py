"""This file defines custom  command."""
import import_declare_test
import sys
import time
import traceback
import re
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from cymru_helpers.logger_manager import setup_logging
from cymru_helpers.conf_helper import get_conf_file, get_credentials
from cymru_helpers.rest_helper import RestHelper
from cymru_helpers.constants import DATE_REGEX

logger = setup_logging("ta_team_cymru_scout_section_search_command")


@Configuration()
class TeamCymruScoutSectionSearchCommand(GeneratingCommand):
    """Team Cymru Scout search custom command class."""

    indicator_type = Option(require=True)
    indicators = Option(require=True)
    account_name = Option(require=True)
    section_name = Option(require=True)
    communication = Option(require=False, default=False)
    start_date = Option(require=False, default="")
    end_date = Option(require=False, default="")

    def parse_response(self, response):
        """Parse Response."""
        dates = response.get(self.section_name).get("data").get("dates")
        datasets = response.get(self.section_name).get("data").get("datasets")

        final_resp = []
        for dataset in datasets:
            for i in range(len(dates)):
                temp = dict()
                if self.section_name != "top_country_codes_by_ip":
                    temp['label'] = dataset.get("label")
                else:
                    temp['label'] = dataset.get('country')
                temp['data'] = dataset.get("data")[i]
                temp['date'] = dates[i]
                final_resp.append(temp)
        return final_resp

    def parse_proto_response(self, response):
        """Parse Protocol Response."""
        if not response.get('proto_by_ip').get('data').get('proto_by_date'):
            return
        length = len(response.get('proto_by_ip').get('data').get('proto_by_date')[0].get('data', []))
        proto_length = len(response.get('proto_by_ip').get('data').get('protocols'))
        final_resp = []
        for i in range(length):
            temp = dict()
            temp['date'] = response.get('proto_by_ip').get('data').get('proto_by_date')[0].get('data')[i].get('date')
            for j in range(proto_length):
                if self.communication:
                    temp[response.get('proto_by_ip').get('data').get('proto_by_date')[j].get('keyword')] = response.get('proto_by_ip').get('data').get('proto_by_date')[j].get('data')[i].get('count')  # noqa:E501
                else:
                    temp['total_event_count'] = temp.get('total_event_count', 0) + response.get('proto_by_ip').get('data').get('proto_by_date')[j].get('data')[i].get('count')  # noqa:E501
            if self.communication:
                yield {'_time': time.time(), "_raw": temp}
            else:
                final_resp.append(temp)
        fr = dict()
        fr["top_services_by_ip"] = final_resp
        yield {'_time': time.time(), "_raw": fr}

    def validate_params(self):
        """Validate params."""
        if self.indicators == "" or self.indicator_type == "" or self.section_name == "" or self.account_name == "":
            logger.error("Team Cymru Scout Error: Invalid Parameters.")
            logger.debug(
                "Team Cymru Scout Debug: Invalid Parameters : {}"
                .format(traceback.format_exc())
            )
            self.write_error("Invalid Parameters.")
            exit(1)
        if self.indicator_type not in ["ip"]:
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
            cymru_config.update({"indicator_type": "ip"})
            cymru_config.update({"indicators": self.indicators})
            cymru_rest_helper = RestHelper(cymru_config, logger)
            response = cymru_rest_helper.get_section_data(
                self.section_name, self.start_date, self.end_date
            )

            for res in response:
                if self.section_name == "proto_by_ip":
                    final_resp = self.parse_proto_response(res)
                    for r in final_resp:
                        yield {'_time': time.time(), "_raw": r}
                else:
                    final_resp = self.parse_response(res)
                    fr = dict()
                    fr["top_services_by_ip"] = final_resp
                    yield {'_time': time.time(), "_raw": fr}
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


dispatch(TeamCymruScoutSectionSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
