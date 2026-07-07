from tempfile import TemporaryDirectory
from os import environ

import license

from etl.sfcc_etl import SfccEtl


def validate_input(splunk_helper, definition):
    splunk_helper.log_debug("ETL validating input...")
    return None


@license.license_required
def collect_events(splunk_helper, splunk_event_writer):
    try:
        checkpoint_directory = splunk_helper._input_definition.metadata[
            "checkpoint_dir"
        ]
        # Directory where the temporary files will be stored.
        # ETL is using this directory to store the downloaded files from Salesforce Commerce Cloud.
        download_dir = environ.get("SPLUNK_HOME", "/opt/splunk")
        with TemporaryDirectory(
            prefix="tmp-ta-aiops-sfcc-logs-", dir=download_dir
        ) as working_directory:
            SfccEtl(
                splunk_helper,
                splunk_event_writer,
                working_directory,
                checkpoint_directory,
            ).start()

    except Exception as exception:
        splunk_helper.log_error(exception)
        raise exception
