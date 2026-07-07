import import_declare_test  # noqa: F401

try:
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..")))
    sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "..", "common")))

    import splunk.admin as admin

    from common.utility import read_conf_file
    import common.log as log

    logger = log.get_logger(__file__)
    logger.info("Hello.....")

    def get_advantage_accounts(conf_details):
        """Returns a list of advantage accounts from conf."""
        account_list = []
        for account_name, account_details in conf_details.items():
            if account_details.get('account_type') == 'mandiant_advantage':
                account_list.append(account_name)
        return account_list


    class AdvantageAccountDisplaying(admin.MConfigHandler):
        """Get the advantage account names."""

        def setup(self):
            """To setup the variables to access in account."""
            pass

        def handleList(self, conf_info):
            """Populate the accounts in singleselect dropdown."""
            # set splunk context vars
            try:
                conf_file = read_conf_file(self.getSessionKey(), "ta_mandiant_advantage_account")
                advantage_account = get_advantage_accounts(conf_file)
                for account in advantage_account:
                    conf_info[account]
            except Exception as e:
                logger.error(
                    "message:error occured while populating advantage accounts | "
                    "Following error occured while populating advantage accounts. "
                    "ERROR: {}".format(e)
                )


    if __name__ == "__main__":
        """Driving function."""
        admin.init(AdvantageAccountDisplaying, admin.CONTEXT_NONE)
except Exception as e:
    raise Exception("ERROR INT2: {}".format(e))
