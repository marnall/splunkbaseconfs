#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import os.path as op

from solnlib import conf_manager

APP_NAME = op.basename(op.dirname(op.dirname(op.abspath(__file__))))


class AccountManager:
    def __init__(self, session_key):
        self.session_key = session_key
        self._accounts = {}
        self.fetch_accounts()

    def fetch_accounts(self):
        account_cfm = conf_manager.ConfManager(
            self.session_key,
            APP_NAME,
            realm="__REST_CREDENTIAL__#{}#configs/conf-splunk_ta_remedy_account".format(
                APP_NAME
            ),
        )
        accounts = account_cfm.get_conf("splunk_ta_remedy_account").get_all()
        self._accounts = accounts

    def set_jwt_token_in_memory(self, account_name, new_jwt_token):
        self._accounts[account_name]["jwt_token"] = new_jwt_token

    def get_account_details(self, account_name):
        if account_name not in self._accounts:
            raise ValueError(
                'Unable to find "{}" account details. '
                "Enter a configured account name or create new account by "
                "going to Configuration page of the Add-on.".format(account_name)
            )

        return self._accounts[account_name]
