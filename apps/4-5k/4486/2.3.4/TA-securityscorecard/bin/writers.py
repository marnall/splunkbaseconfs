import datetime
import time

from formatters import dict_to_kv_string
from scorecard_exceptions import InvalidAPIKeyError, InvalidJSONError, NoDataError, ServerError

MAX_RETRY = 3
OVERALL_CNT = 0
FACTOR_CNT = 0
ISSUE_CNT = 0
new_from_date = ''
SPLUNK_ERROR = "Halt for 5 sec due to server error."
RESUME_ERROR = "Resuming for {} time."
INDUSTRY_NAME = {}


class CompanyWriter(object):
    """Represents a CompanyWriter object."""

    def __init__(self, company, helper, ew):
        """Initializes CompanyWriter class."""
        self.__company = company
        self.__helper = helper
        self.__ew = ew

    def write_overall(self, **config):
        """This method is used to process the overall Score for a company."""
        global OVERALL_CNT
        chk_point_name = ''
        try:
            scores = self.__company.get_overall_score(**config)
        except KeyError:
            self.__helper.log_error("Getting overall score for {} to {} returned only "
                                    "1 entry for getting difference it needed  at least "
                                    "two entry".format(config['from_date'],
                                                       config['to_date']))
        except InvalidAPIKeyError as e:
            self.__helper.log_error("API key is invalid or expired. "
                                    "Please validate that your token is entered correctly")
            self.__helper.log_error(str(e))
            return
        except NoDataError as e:
            self.__helper.log_info("No Overall data found in between {} to {} \
                or response is None".format(config['from_date'], config['to_date']))
        except InvalidJSONError as e:
            self.__helper.log_error("Data received from API is not in JSON format")
            self.__helper.log_error(str(e))
        except ServerError as e:
            self.__helper.log_error("Sever error occurred while calling the Overall API")
            self.__helper.log_error(str(e))
            while OVERALL_CNT <= MAX_RETRY:
                OVERALL_CNT += 1
                self.__helper.log_info(SPLUNK_ERROR)
                time.sleep(5)
                self.__helper.log_info(RESUME_ERROR)
                self.write_overall(**config)
            self.__helper.log_warning("Retry limit exhausted for ServerError.")
        except Exception as e:
            self.__helper.log_error("Error in fetching company overall")
            self.__helper.log_error(str(e))
            raise
        else:
            global new_from_date
            # Write overall score for company
            self.__helper.log_debug("Total Overall received = {} ".format(len(scores)))
            if not config.get('portfolioId') and scores:
                try:
                    input_name = list(self.__helper.get_input_stanza())[0]
                    self.__helper.log_debug("Domain is {}".format(self.__company.domain))
                    chk_point_name = "{}_{}".format(input_name, self.__company.domain).replace(".", "_").lower()
                    from_date = scores[-1]['dateToday'][:10]
                    new_from_date = str(
                        datetime.datetime.strptime(from_date, "%Y-%m-%d")
                        + datetime.timedelta(days=1)
                    )[:10]
                    self.__helper.log_debug("New date for fetching data will be saved as {}".format(new_from_date))
                except Exception as err:
                    self.__helper.log_warning('No data found from API.')
                    self.__helper.log_debug('Error {} occurred while fetching date from score {}'.format(err, scores))
            override = config.get('diff_override_portfolio_overall') \
                if config.get('portfolioId') and config.get('portfolioName') \
                else config.get('diff_override_own_overall')
            for score in scores:
                try:
                    if self.__company.domain:
                        domain_name = self.__company.domain
                        if domain_name not in INDUSTRY_NAME:
                            industry_name = self.__company.get_industry_name(**config)
                            INDUSTRY_NAME[domain_name] = industry_name

                        if INDUSTRY_NAME[domain_name]:
                            score.update(
                                {'industry': INDUSTRY_NAME[domain_name]}
                            )
                except Exception as e:
                    self.__helper.log_error("Error in fetching industry")
                    self.__helper.log_error(str(e))
                if score.get('diff') != 0 or override:
                    score.pop('diff', None)
                    score.update({'severity': config['level_overall_change']})

                    # Insert portfolio id and name if present
                    if config.get('portfolioId') and config.get('portfolioName'):
                        score.update({
                            'portfolioId': config['portfolioId'],
                            'portfolioName': config['portfolioName'],
                        })

                    item = dict_to_kv_string(score)
                    event = self.__helper.new_event(
                        source=self.__helper.get_input_type(),
                        index=self.__helper.get_output_index(),
                        sourcetype=self.__helper.get_sourcetype(),
                        data=item,
                    )
                    self.__ew.write_event(event)
            else:
                if chk_point_name:
                    self.__helper.save_check_point(chk_point_name, new_from_date)
                    self.__helper.log_debug("Checkpoint date saved as {}".format(new_from_date))
            self.__helper.log_debug("Overall data logged for {}".format(self.__company.domain))

    def write_factors(self, **config):
        """This method is used to process the factors for a company."""
        global FACTOR_CNT
        try:
            factors = self.__company.get_factors(**config)
        except IndexError:
            self.__helper.log_error("Getting factor score from {} to {} returned only "
                                    "1 entry for getting difference it needed  at least "
                                    "two entry".format(config['from_date'], config['to_date']))
        except NoDataError as e:
            self.__helper.log_info("No factor data found in between {} to {} \
                or response is None.".format(config['from_date'], config['to_date']))
        except InvalidJSONError as e:
            self.__helper.log_error("Data received from API is not in JSON format")
            self.__helper.log_error(str(e))
        except ServerError as e:
            self.__helper.log_error("Server error occurred while calling the factors API")
            self.__helper.log_error(str(e))
            while FACTOR_CNT <= MAX_RETRY:
                FACTOR_CNT += 1
                self.__helper.log_info(SPLUNK_ERROR)
                time.sleep(5)
                self.__helper.log_info(RESUME_ERROR)
                self.write_factors(**config)
        except Exception as e:
            self.__helper.log_error("Error in fetching company factors")
            self.__helper.log_error(str(e))
            raise
        else:
            self.__helper.log_debug("Total Factors received = {} ".format(len(factors)))
            override = config.get('diff_override_portfolio_factor') \
                if config.get('portfolioId') and config.get('portfolioName') \
                else config.get('diff_override_own_factor')

            for factor in factors:
                try:
                    if self.__company.domain:
                        domain_name = self.__company.domain
                        if domain_name not in INDUSTRY_NAME:
                            industry_name = self.__company.get_industry_name(**config)
                            INDUSTRY_NAME[domain_name] = industry_name

                        if INDUSTRY_NAME[domain_name]:
                            factor.update(
                                {'industry': INDUSTRY_NAME[domain_name]}
                            )
                except Exception as e:
                    self.__helper.log_error("Error in fetching industry")
                    self.__helper.log_error(str(e))

                if factor.get('diff') != 0 or override:
                    factor.pop('diff', None)
                    factor.update({'severity': config['level_factor_change']})

                    # Insert portfolio id and name if present
                    if config.get('portfolioId') and config.get('portfolioName'):
                        factor.update({
                            'portfolioId': config['portfolioId'],
                            'portfolioName': config['portfolioName'],
                        })

                    item = dict_to_kv_string(factor)
                    event = self.__helper.new_event(
                        source=self.__helper.get_input_type(),
                        index=self.__helper.get_output_index(),
                        sourcetype=self.__helper.get_sourcetype(),
                        data=item,
                    )
                    self.__ew.write_event(event)
            self.__helper.log_debug("Factor data logged for {}".format(self.__company.domain))

    def write_issues(self, **config):
        """This method is used to process the issues for a company."""
        global ISSUE_CNT
        try:
            issues, issue_detail_list = self.__company.get_issue_levels(**config)
        except NoDataError as e:
            self.__helper.log_info("No issue data found in between {} to {}".format(config['from_date'],
                                                                                     config['to_date']))
        except InvalidJSONError as e:
            self.__helper.log_error("Data received from API is not in JSON format.")
            self.__helper.log_error(str(e))
        except ServerError as e:
            self.__helper.log_error("Server error occurred while calling the ISSUE API.")
            self.__helper.log_error(str(e))
            while ISSUE_CNT <= MAX_RETRY:
                ISSUE_CNT += 1
                self.__helper.log_info(SPLUNK_ERROR)
                time.sleep(5)
                self.__helper.log_info(RESUME_ERROR)
                self.write_issues(**config)
        except Exception as e:
            self.__helper.log_error("Error in fetching company issues")
            self.__helper.log_error(str(e))
            raise
        else:
            for issue in issues:
                try:
                    if self.__company.domain:
                        domain_name = self.__company.domain
                        if domain_name not in INDUSTRY_NAME:
                            industry_name = self.__company.get_industry_name(**config)
                            INDUSTRY_NAME[domain_name] = industry_name

                        if INDUSTRY_NAME[domain_name]:
                            issue.update(
                                {'industry': INDUSTRY_NAME[domain_name]}
                            )
                except Exception as e:
                    self.__helper.log_error("Error in fetching industry")
                    self.__helper.log_error(str(e))

                issue.update({'severity': config['level_new_issue_change']})

                # Insert portfolio id and name if present
                if config.get('portfolioId') and config.get('portfolioName'):
                    issue.update({
                        'portfolioId': config['portfolioId'],
                        'portfolioName': config['portfolioName'],
                    })

                item = dict_to_kv_string(issue)
                event = self.__helper.new_event(
                    source=self.__helper.get_input_type(),
                    index=self.__helper.get_output_index(),
                    sourcetype=self.__helper.get_sourcetype(),
                    data=item,
                )
                self.__ew.write_event(event)
                self.__helper.log_debug("Issue data logged for {}".format(issue['subject']))
            if config['fetch_issue_level_data']:
                for issue_details in issue_detail_list:
                    # issue_details.update({'severity': config['level_new_issue_change']})
                    try:
                        item = dict_to_kv_string(issue_details)
                        event = self.__helper.new_event(
                            source=self.__helper.get_input_type(),
                            index=self.__helper.get_output_index(),
                            sourcetype=self.__helper.get_sourcetype(),
                            data=item,
                        )
                        self.__ew.write_event(event)
                    except Exception as err:
                        self.__helper.log_error("Not able to log issue details getting error as {}".format(err))
                self.__helper.log_debug("Issue level findings logged for {}".format(self.__company.domain))
