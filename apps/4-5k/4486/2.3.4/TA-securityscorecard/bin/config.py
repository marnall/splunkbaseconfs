"""Configurations for Security Scorecard."""


FIELDS = [
    'domain',
    'securityscorecard_api_url',
    'level_overall_change',
    'level_factor_change',
    'level_new_issue_change',
    'portfolio_ids',
    'fetch_company_overall',
    'fetch_company_factors',
    'fetch_company_issues',
    'fetch_portfolio_overall',
    'fetch_portfolio_factors',
    'fetch_portfolio_issues',
    'diff_override_own_overall',
    'diff_override_portfolio_overall',
    'diff_override_own_factor',
    'diff_override_portfolio_factor',
    'fetch_issue_level_data'

]


DAYS = 20
SS_RATE_LIMIT = 5000

CHECKPOINT_NAME = 'last_run_date'
