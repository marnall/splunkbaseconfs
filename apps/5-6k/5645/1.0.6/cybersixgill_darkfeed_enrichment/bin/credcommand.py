"""Validate client id and client_secret provided by the user."""

from collections.abc import Generator
from sys import argv, stdin, stdout

from sixgill.sixgill_base_client import SixgillBaseClient
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch
from utils import CHANNEL_ID, get_credentials, get_session_with_proxy, setup_logging

logger = setup_logging(__name__)


@Configuration()
class Cred(GeneratingCommand):
    """Validate CyberSixgill API credentials for Splunk searches.

    This command validates the client ID and client secret stored in Splunk's
    storage passwords by attempting to obtain an access token from the CyberSixgill API.
    """

    def generate(self) -> Generator[dict, None, None]:
        """Validate CyberSixgill API credentials and return the status.

        This method:
        1. Retrieves credentials from Splunk storage
        2. Establishes a connection to CyberSixgill API
        3. Attempts to obtain an access token
        4. Yields the validation status

        Yields:
            dict: A dictionary containing the credential validation status:
                - {"cred_status": "success"} if credentials are valid
                - {"cred_status": "failed"} if credentials are invalid or an error occurs

        Note:
            Any exception during the process will result in a "failed" status.

        """
        try:
            client_id, client_secret = get_credentials(self.service.storage_passwords)
            client_session = get_session_with_proxy()
            sixgill_client = SixgillBaseClient(
                client_id=client_id,
                client_secret=client_secret,
                channel_id=CHANNEL_ID,
                verify=True,
                session=client_session,
            )
            sixgill_access = sixgill_client.get_access_token()
            if sixgill_access:
                yield {"cred_status": "success"}
            else:
                yield {"cred_status": "failed"}
        except Exception as ex:
            logger.exception(ex)
            yield {"cred_status": "failed"}


if __name__ == "__main__":
    dispatch(Cred, argv, stdin, stdout, __name__)
