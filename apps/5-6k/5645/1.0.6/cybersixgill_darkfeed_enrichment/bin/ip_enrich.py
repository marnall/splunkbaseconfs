"""Take IP address as input from the user and show the
enriched data from cybersixgill end point.
"""

from collections.abc import Generator
from json import dumps
from pathlib import Path
from sys import argv, stdin, stdout
from sys import path as sys_path
from time import time

from utils import (
    CHANNEL_ID,
    get_credentials,
    get_session_with_proxy,
    process_records,
    setup_logging,
)

sys_path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from sixgill.sixgill_enrich_client import SixgillEnrichClient
from splunklib.searchcommands import Configuration, GeneratingCommand, dispatch

logger = setup_logging(__name__)


@Configuration()
class Cred(GeneratingCommand):
    """Enrich IP address data from CyberSixgill for Splunk searches.

    This command takes an IP address as input and retrieves enriched data from the
    CyberSixgill API endpoint. It processes the data and yields formatted results
    suitable for Splunk search results.
    """

    def generate(self) -> Generator[dict, None, None]:
        """Generate enriched data for the given IP address.

        This method:
        1. Retrieves credentials from Splunk storage
        2. Establishes a connection to CyberSixgill API
        3. Enriches the IP address data
        4. Processes and yields the results

        Yields:
            dict: A dictionary containing the enriched data with:
                - Processed fields from the enrichment
                - _time: Current timestamp
                - _raw: Raw JSON data

        Note:
            If an error occurs, yields an error message with timestamp.

        """
        try:
            ioc_value = self.fieldnames[0]
            client_id, client_secret = get_credentials(self.service.storage_passwords)
            client_session = get_session_with_proxy()
            sixgill_client = SixgillEnrichClient(
                client_id=client_id,
                client_secret=client_secret,
                channel_id=CHANNEL_ID,
                verify=True,
                session=client_session,
            )
            raw_records = sixgill_client.enrich_ioc("ip", str(ioc_value))
            data_list = process_records(raw_records, logger)
            for indicator in data_list:
                final_dict = {}
                for key, value in indicator.items():
                    final_dict.update({key: value})
                final_dict.update({"_time": time(), "_raw": dumps(indicator)})
                yield final_dict
        except Exception as err:
            yield {"_raw": err, "_time": time()}
            logger.exception(err)


if __name__ == "__main__":
    dispatch(Cred, argv, stdin, stdout, __name__)
