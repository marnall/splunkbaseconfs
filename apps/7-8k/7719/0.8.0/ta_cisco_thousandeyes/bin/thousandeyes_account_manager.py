from solnlib import conf_manager

from thousandeyes_constant import THOUSANDEYES_TA_NAME


class ThousandEyesAccountManager:
    """
    Class to manage ThousandEyes accounts in Splunk.

    This class provides methods to retrieve all ThousandEyes accounts and update access tokens
    """

    def __init__(self, session_key: str):
        """
        Initialize the account manager with a session key.

        :param session_key: Splunk session key for authentication.
        """
        self.session_key = session_key
        self.conf_manager = conf_manager.ConfManager(
            session_key,
            THOUSANDEYES_TA_NAME,
            realm=f"__REST_CREDENTIAL__#{THOUSANDEYES_TA_NAME}#configs/conf-{THOUSANDEYES_TA_NAME}_account",
        )

    def get_all_accounts(self) -> dict:
        """
        Retrieve all ThousandEyes accounts from Splunk configuration.

        :return: Dictionary of all ThousandEyes accounts.
        """
        return self.conf_manager.get_conf(f"{THOUSANDEYES_TA_NAME}_account", refresh=True).get_all()

    def update_access_token(
        self,
        new_access_token,
        new_refresh_token,
        account_name,
    ):
        """
        Update the token values in the account configuration file.

        :param new_access_token: Regenerated access token.
        :param new_refresh_token: Regenerated refresh token.
        :param account_name: Name of the ThousandEyes account to update.
        """
        encrypt_fields = {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }
        account_conf = self.conf_manager.get_conf(f"{THOUSANDEYES_TA_NAME}_account", refresh=True)
        account_conf.update(account_name, encrypt_fields, encrypt_fields.keys())