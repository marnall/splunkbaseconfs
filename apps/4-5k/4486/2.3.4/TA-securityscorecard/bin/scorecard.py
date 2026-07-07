"""Module to get data from Security Scorecard."""

import json
from collections import OrderedDict

from formatters import format_date_string
from scorecard_exceptions import NoDataError
from utils import connect_to_ss, get_value_from_dict_list


class ScoreCard(object):
    """Represents a scorecard object."""

    def __init__(self, base_url, access_key, helper):
        """Initializes the Scorecard class."""
        self.__access_key = access_key
        self.__base_url = base_url
        self.__helper = helper

    def get_overall_score_url(self, company):
        """This method returns the URL for fetching the overall Score."""
        return '{}/companies/{}/history/score'.format(self.__base_url, company)

    def get_factors_meta_url(self):
        """This method returns the URL for fetching the factors metadata."""
        return '{}/metadata/factors'.format(self.__base_url)

    def get_factor_score_url(self, company):
        """This method returns the URL for fetching the factors Score."""
        return '{}/companies/{}/history/factors/score'.format(self.__base_url, company)

    def get_issue_types_meta_url(self):
        """This method returns the URL for fetching the list of issue-types."""
        return '{}/metadata/issue-types'.format(self.__base_url)

    def get_issue_levels_url(self, company):
        """This method returns the URL for fetching the issues."""
        return '{}/companies/{}/history/events'.format(self.__base_url, company)

    def get_portfolios_url(self):
        """This method returns the URL for fetching the portfolios."""
        return '{}/portfolios'.format(self.__base_url)

    def get_portfolio_data_url(self, portfolio_id):
        """This method returns the URL for fetching the companies inside a portfolio."""
        return "{}/portfolios/{}/companies".format(self.__base_url, portfolio_id)

    def get_industry_url(self, company):
        """This method returns the URL for fetching the company details."""
        return "{}/companies/{}".format(self.__base_url, company)

    @staticmethod
    def generate_overall_score(company, today_values, yesterday_values):
        """This method is used to generate the overall score of a company."""
        diff = today_values['score'] - yesterday_values['score']

        return OrderedDict([
            ('body', 'OverAll'),
            ('type', "'scoreChange'"),
            ('src', 'OverallScore'),
            ('subject', company),
            ('dateYesterday', format_date_string(yesterday_values.get('date', ''))),
            ('dateToday', format_date_string(today_values.get('date', ''))),
            ('scoreYesterday', yesterday_values.get('score', '')),
            ('scoreToday', today_values.get('score', '')),
            ('scoreChange', diff),
            ('diff', diff),
        ])

    def get_overall_score(self, company, **config):
        """This method is used to get the overall score of a company."""
        from_date, to_date = config.get('from_date_factor'), config.get('to_date')
        params = {'date_from': from_date, 'date_to': to_date} if from_date and to_date else {}
        scores = connect_to_ss(
            self.get_overall_score_url(company),
            token=self.__access_key,
            params=params,
            proxy=config.get('proxy'),
            helper=self.__helper
        )

        if not scores or not scores['entries']:
            raise NoDataError
        rv = []

        try:
            # Python 2.7
            range_ = xrange
        except Exception:
            # Python 3
            range_ = range

        for value in range_(len(scores['entries']) - 1):
            yesterday_values = scores['entries'][value]
            today_values = scores['entries'][value + 1]
            rv.append(self.generate_overall_score(company, today_values, yesterday_values))
        return rv

    @staticmethod
    def generate_factors(company, today_values, yesterday_values, factors_meta):
        """This method is used to generate the factor score of a company."""
        rv = []
        for factor in today_values.get('factors', []):
            name = factor['name']
            other = get_value_from_dict_list(yesterday_values['factors'], 'name', name)
            diff = factor['score'] - other['score'] if other else 0
            matched_factor = get_value_from_dict_list(factors_meta, 'key', name)
            try:
                factor_description = matched_factor.get('description', '')
            except KeyError:
                factor_description = 'data is not there'
            except AttributeError:
                factor_description = 'data is not there'

            rv.append(OrderedDict([
                ('body', 'Factor'),
                ('type', "'scoreChange'"),
                ('src', name),
                ('subject', company),
                ('dateYesterday', format_date_string(yesterday_values.get('date', ''))),
                ('dateToday', format_date_string(today_values.get('date', ''))),
                ('scoreYesterday', other['score'] if other else 0),
                ('scoreToday', factor['score']),
                ('scoreChange', diff),
                ('diff', diff),
                ('factorDescription', "'{}'".format(factor_description))
            ]))

        return rv

    # added log here
    def get_factors(self, company, **config):
        """This method is used to get the factors of a company."""
        factors_meta = connect_to_ss(
            self.get_factors_meta_url(),
            token=self.__access_key,
            proxy=config.get('proxy'),
            helper=self.__helper
        )['entries']
        from_date, to_date = config.get('from_date_factor'), config.get('to_date')
        params = {'date_from': from_date, 'date_to': to_date, 'timing': 'daily'} if from_date and to_date else {}
        url = self.get_factor_score_url(company)

        factors = connect_to_ss(
            url,
            token=self.__access_key,
            params=params,
            proxy=config.get('proxy'),
            helper=self.__helper
        )

        if not factors or not factors['entries']:
            raise NoDataError
        rv = []

        try:
            # Python 2.7
            range_ = xrange
        except Exception:
            # Python 3
            range_ = range

        for value in range_(len(factors['entries']) - 1):
            yesterday_values = factors['entries'][value]
            today_values = factors['entries'][value + 1]
            rv.extend(self.generate_factors(company, today_values, yesterday_values, factors_meta))
        return rv

    # added log here
    def get_issue_levels(self, company, **config):
        """Finds all the issue levels for a company.

        :param company: str
        :return: list of dicts
        """
        # added log here
        try:
            issue_types = connect_to_ss(
                self.get_issue_types_meta_url(),
                self.__access_key,
                proxy=config.get('proxy'),
                helper=self.__helper
            )['entries']
        except Exception:
            raise NoDataError

        url = self.get_issue_levels_url(company)
        from_date = config.get('from_date')
        to_date = config.get('to_date')

        if from_date:
            # For issue levels from date and to date are the same.
            from_date = '{}T00:00:00Z'.format(from_date)
            to_date = '{}T00:00:00Z'.format(to_date)
            params = {'date_from': from_date, 'date_to': to_date}
        else:
            params = {}

        levels = connect_to_ss(
            url,
            self.__access_key,
            params=params,
            proxy=config.get('proxy'),
            helper=self.__helper
        )

        if not levels or not levels['entries']:
            raise NoDataError

        issue_detail_list = []
        group_status_mapping = {
            'active': 'Issues Observed',
            'departed': 'Issues UnObserved',
            'resolved': 'Issues Refuted',
        }
        if config.get('fetch_issue_level_data'):
            error_list = []
            # issue_level_entries -----> (levels['entries'])
            for issue in levels['entries']:
                try:
                    issue_details = connect_to_ss(
                        issue['detail_url'],
                        self.__access_key,
                        params=params,
                        proxy=config.get('proxy'),
                        helper=self.__helper
                    )
                    for issue_detail in issue_details['entries']:
                        tmp = OrderedDict([
                            ('body', 'IssueFindings'),
                            ('date', format_date_string(issue.get('date'))),
                            ('eventID', issue.get('id', 'Not found any id corresponding to this issue')),
                            ('eventtype', 'SecurityScorecard(alert)'),
                            ('groupStatus', issue_detail.get('group_status')),
                            ('issueName', "'{}'".format(
                                get_value_from_dict_list(issue_types, 'key', issue.get('issue_type'))['title']
                                if get_value_from_dict_list(issue_types, 'key', issue.get('issue_type'))
                                else "not found")),
                            ('issueType', issue.get('issue_type')),
                            ('severity_value', issue.get('severity')),
                            ('src', issue.get('factor')),
                            ('subject', company),
                            ('tag', 'alert'),
                            ('type', "'{}'".format(group_status_mapping.get(
                                issue_detail.get('group_status', 'Unknown')))),
                            ('raw_value', "'{}'".format(json.dumps(issue_detail))),
                        ])

                        issue_detail_list.append(tmp)
                except KeyError as err:
                    error_list.append({issue.get('id', 'detail_url'): "{}_not found_for_this_id".format(err)})
                except Exception as err:
                    error_list.append({issue.get('id', 'detail_url'): err})
            if error_list:
                issue_detail_list.append({'error': error_list})

        return map(
            lambda entry: OrderedDict([
                ('body', 'Issue'),
                ('type', "'{}'".format(group_status_mapping.get(entry['group_status'], 'Unknown'))),
                ('src', entry.get('factor', 'Unknown')),
                ('eventID', entry.get('id', 'No_id')),
                ('subject', company),
                ('date', format_date_string(entry.get('date', 'no_date'))),
                ('issueType', entry.get('issue_type', 'no_issueType')),
                ('findingsCount', entry.get('issue_count', 'no_issue_count')),
                ('groupStatus', entry.get('group_status')),
                ('issueName', "'{}'".format(
                    get_value_from_dict_list(issue_types, 'key', entry.get('issue_type'))['title']
                    if get_value_from_dict_list(issue_types, 'key', entry.get('issue_type'))
                    else "not found")),
                ('totalScoreImpact', entry.get('total_score_impact')),
                ('severity_value', entry.get('severity')),
            ]),
            filter(lambda each: each['issue_type'] != 'breach', levels['entries'])
        ), issue_detail_list

    def get_portfolios(self, **config):
        """This method is used to get the portfolios."""
        portfolio = connect_to_ss(
            self.get_portfolios_url(),
            self.__access_key,
            proxy=config.get('proxy'),
            helper=self.__helper
        )
        return portfolio['entries']

    def get_portfolio_data(self, portfolio_id, **config):
        """This method is used to get the companies of a portfolio."""
        companies = connect_to_ss(
            self.get_portfolio_data_url(portfolio_id),
            self.__access_key,
            proxy=config.get('proxy'),
            helper=self.__helper
        )
        return companies['entries']

    def get_industry_name(self, company, **config):
        """This method is used to get the industry name of a company."""
        company = connect_to_ss(
            self.get_industry_url(company),
            self.__access_key,
            proxy=config.get('proxy'),
            helper=self.__helper
        )
        industry_name = company.get('industry')

        return industry_name


class Company(object):
    """Represents a company object."""

    def __init__(self, api_url, access_key, domain, helper, portfolio_id=None, portfolio_name=None):
        """Initializes Company object."""
        self.score_card = ScoreCard(api_url, access_key, helper)
        self.domain = domain
        self.portfolio_id = portfolio_id
        self.portfolio_name = portfolio_name

    # added log here
    def get_overall_score(self, **config):
        """This method returns the overall score for a company."""
        return self.score_card.get_overall_score(self.domain, **config)

    def get_factors(self, **config):
        """This method returns the factor score for a company."""
        return self.score_card.get_factors(self.domain, **config)

    def get_issue_levels(self, **config):
        """This method returns the issues for a company."""
        return self.score_card.get_issue_levels(self.domain, **config)

    def get_industry_name(self, **config):
        """This method returns the industry name for a company."""
        return self.score_card.get_industry_name(self.domain, **config)


class Portfolio(object):
    """Represents a portfolio object."""

    def __init__(self, api_url, helper, access_key, ids=None, **config):
        """Initializes Portfolio object."""
        self.score_card = ScoreCard(api_url, access_key, helper)
        self.companies = []
        self.invalid_ids = []
        self.valid_ids = []

        portfolios = self.score_card.get_portfolios(**config)

        if ids:
            portfolios = list(filter(lambda val: val['id'] in ids, portfolios))
            self.valid_ids = [val['id'] for val in portfolios]
            self.invalid_ids = list(filter(lambda val: val not in self.valid_ids, ids))
        else:
            self.valid_ids = [val['id'] for val in portfolios]

        for portfolio in portfolios:
            portfolio_data = self.score_card.get_portfolio_data(portfolio['id'])
            self.companies.extend(map(
                lambda val: Company(
                    api_url=api_url,
                    access_key=access_key,
                    domain=val['domain'],
                    portfolio_id=portfolio['id'],
                    portfolio_name=portfolio['name'],
                    helper=helper
                ),
                portfolio_data,
            ))
