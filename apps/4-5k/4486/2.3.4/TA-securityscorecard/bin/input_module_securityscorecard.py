
# encoding = utf-8

import sys
import datetime
import requests
from solnlib import conf_manager, log
import traceback
from urllib.parse import urljoin

from config import FIELDS, DAYS, CHECKPOINT_NAME
from scorecard import Company
from splunk_utils import get_proxy_uri, get_global_account_credential, extract_input_fields, build_portfolio, wait_for_kvstore
from ta_securityscorecard_declare import ta_name
from writers import CompanyWriter


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
    logger = log.Logs().get_logger("ta_securityscorecard_input_validation")
    access_key = get_global_account_credential(definition.metadata["session_key"], definition.parameters.get("global_account"))
    api_url = definition.parameters.get("securityscorecard_api_url")
    try:
        proxy_settings = get_proxy_uri(definition.metadata["session_key"])
    except Exception as e:
        logger.error(
            "Error occured while reading the proxy details: {}".format(traceback.format_exc())
        )
        msg = "Error occurred while reading proxy details. Please check the ta_securityscorecard_input_validation.log file for more details".format(e)
        raise(Exception(msg))

    status_code, message = 500, "Unknown error"
    try:
        # Check that url starts with https or not.
        if not api_url.startswith("https"):
            status_code, message = 409, "SecurityScorecard API URL must start with https."
        else:
            api_url = urljoin(api_url, "/portfolios")

        # Initialize the header dict
        headers = {
            'authorization': 'Token {}'.format(access_key),
            'X-SSC-Application-Name': 'Splunk',
            'X-SSC-Application-Version': '2.3.4',
        }
        response = requests.get(api_url, headers=headers, proxies=proxy_settings, timeout=120)

        # Parse the response
        if response.status_code == 401:
            status_code, message = 401, "Unable to verify the API Key of selected account. Please verify the account details."
            logger.error(message)
        elif response.status_code == 200:
            status_code, message = 200, ""
        else:
            logger.warning("Something went wrong while validating the SSC API Url: {}".format(response.text))
            status_code, message = response.status_code, "Something went wrong while validating the API Url. Please check the ta_securityscorecard_input_validation.log file for more details."
    except Exception as e:
        logger.error(
            "Error occured while validating the account: {}".format(traceback.format_exc())
        )
        msg = "Error occured while validating the account: {}. Please check the ta_securityscorecard_input_validation.log file for more details.".format(e)
        status_code, message = 500, msg

    if status_code != 200:
        raise Exception(message)

def check_interval(helper, interval):
    """Method to check if the interval is less than 86400 seconds and update it to 86400 if it is less."""
    if interval < 86400:
        try:
            helper.log_info("Interval is less than 86400, updating it to 86400.")
            session_key = helper.context_meta["session_key"]
            cfm_update = conf_manager.ConfManager(
                session_key,
                ta_name,
                realm="inputs",
            )
            # Get the inputs.conf file
            inputs_conf = cfm_update.get_conf("inputs")

            # Name of the stanza to update
            stanza_name = "securityscorecard://{}".format(helper.get_arg("name"))

            # Update the interval value
            inputs_conf.update(stanza_name, {"interval": "86400"})
        except Exception as e:
            helper.log_error("Error while updating interval. {}".str(e))
            return

def collect_events(helper, ew):
    """Implement your data collection logic here
    """

    helper.log_info("Process started at {}.".format(datetime.datetime.now()))
    global_account = helper.get_arg('global_account')
    interval = helper.get_arg('interval')
    check_interval(helper, int(interval))

    options = extract_input_fields(helper, FIELDS)
    api_url = options.get('securityscorecard_api_url')
    helper.log_debug("Url is {}".format(api_url))
    url_prefix = api_url.split(":")
    if url_prefix[0] == "http":
        helper.log_info("Replacing http to https in url.")
        api_url = api_url.replace("http", "https")
        helper.log_debug("Modified url is {}".format(api_url))
    elif url_prefix[0] == "https":
        helper.log_debug("Url is valid.")
    else:
        helper.log_debug("Invalid url")
        helper.log_debug("Setting current url to none and using the default url for further processing.")
        api_url=None
    access_key = global_account.get('password')
    if not access_key:
        helper.log_info("Please provide the api key to process.")
        sys.exit(1)
    domain = options.get('domain')
    if not domain:
        helper.log_warning("Domain is mandatory, please specify domain before proceeding.")
        helper.log_info("Processing is stopped forcefully.")
        sys.exit(1)

    session_key = helper.context_meta["session_key"]
    if not session_key:
        return
    try:
        wait_for_kvstore(session_key, helper)
    except Exception as e:
        helper.log_error(str(e))
        return

    level_overall_change = options.get('level_overall_change', 7)
    level_factor_change = options.get('level_factor_change', 7)
    level_new_issue_change = options.get('level_new_issue_change', 7)

    portfolio_ids = options.get('portfolio_ids')
    proxy = options.get('proxy')
    to_date = datetime.datetime.now().date()

    # fetch_company_overall = options.get('fetch_company_overall', False)
    fetch_company_overall = True
    fetch_company_factors = options.get('fetch_company_factors', False)
    fetch_company_issues = options.get('fetch_company_issues', False)
    fetch_portfolio_overall = options.get('fetch_portfolio_overall', False)
    fetch_portfolio_factors = options.get('fetch_portfolio_factors', False)
    fetch_portfolio_issues = options.get('fetch_portfolio_issues', False)
    fetch_issue_level_data = options.get('fetch_issue_level_data', False)

    diff_override_own_overall = options.get('diff_override_own_overall', False)
    diff_override_portfolio_overall = options.get('diff_override_portfolio_overall', False)
    diff_override_own_factor = options.get('diff_override_own_factor', False)
    diff_override_portfolio_factor = options.get('diff_override_portfolio_factor', False)
    input_name = list(helper.get_input_stanza())[0]

    chk_point_name = "{}_{}".format(input_name, domain).replace(".", "_").lower()
    helper.log_debug("Check point name is {}".format(chk_point_name))
    check_point_date = helper.get_check_point(chk_point_name)
    helper.log_debug("chk point date is {}".format(check_point_date))

    # If date is there in check point or it will start from 20 days back(for 1st run).
    from_date = check_point_date if check_point_date else str(to_date - datetime.timedelta(days=DAYS))
    from_date_factor = str(datetime.datetime.strptime(check_point_date, '%Y-%m-%d') - datetime.timedelta(days=1))[:10] if check_point_date else str(to_date - datetime.timedelta(days=DAYS))
    helper.log_info('Started logging records, from {} to {}'.format(from_date, to_date))

    config = {
        'level_overall_change': level_overall_change,
        'level_factor_change': level_factor_change,
        'level_new_issue_change': level_new_issue_change,
        'portfolio_ids': portfolio_ids,
        'to_date': to_date,
        'from_date': from_date,
        'from_date_factor': from_date_factor,
        'proxy': proxy,
        'diff_override_own_overall': diff_override_own_overall,
        'diff_override_portfolio_overall': diff_override_portfolio_overall,
        'diff_override_own_factor': diff_override_own_factor,
        'diff_override_portfolio_factor': diff_override_portfolio_factor,
        'fetch_issue_level_data': fetch_issue_level_data
    }

    company = Company(api_url=api_url, access_key=access_key, domain=domain, helper=helper)
    company_writer = CompanyWriter(company, helper=helper, ew=ew)

    # Fetch overall score for company
    if fetch_company_overall:
        company_writer.write_overall(**config)
        helper.log_debug('Company overall processed.')

    # Fetch factors for company
    if fetch_company_factors:
        company_writer.write_factors(**config)
        helper.log_debug('Company factors processed.')

    # Fetch issues and issue level details for company
    if fetch_company_issues:
        company_writer.write_issues(**config)
        helper.log_debug('Company issues processed.')

    helper.log_info("Start processing portfolio companies.")
    if portfolio_ids:
        ids = None if portfolio_ids == 'all' else [value.strip() for value in portfolio_ids]
        portfolio = build_portfolio(api_url, helper, access_key, ids, **config)
        helper.log_info("Total portfolio companies = {}.".format(len(portfolio.companies)))

        for company in portfolio.companies:
            company_writer = CompanyWriter(company, helper=helper, ew=ew)
            helper.log_info("Processing portfolio company {} ".format(company.domain))
            config.update({
                'portfolioId': company.portfolio_id,
                'portfolioName': "'" + company.portfolio_name + "'",
            })

            # Fetch overall score for company
            if fetch_portfolio_overall:
                company_writer.write_overall(**config)
                helper.log_debug('Logged portfolio company {} overall'.format(company.domain))

            # Fetch factors for company
            if fetch_portfolio_factors:
                company_writer.write_factors(**config)
                helper.log_debug('Logged portfolio company {} factor'.format(company.domain))

            # Fetch issues and issue level details for company
            if fetch_portfolio_issues:
                company_writer.write_issues(**config)
                helper.log_debug('Logged portfolio company {} issue'.format(company.domain))

    helper.log_info("Process finished at {}.".format(datetime.datetime.now()))
