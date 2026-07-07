import import_declare_test
import traceback
from solnlib import conf_manager

def get_credentials(account_name, session_key):
    """Provide credentials of the configured account.

    Args:
        session_key: current session session key
        logger: log object

    Returns:
        Dict: A Dictionary having account information.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            "TA-mandiant-advantage",
            realm=f"__REST_CREDENTIAL__#TA-mandiant-advantage"
            "#configs/conf-ta_mandiant_advantage_account",
        )
        account_conf_file = cfm.get_conf(
            "ta_mandiant_advantage_account"
        )
        acc_creds = account_conf_file.get(account_name)
    except Exception:
        return None
    return acc_creds