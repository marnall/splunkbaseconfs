from dbx_bootstrap_env import setup_python_path

import sys
import time
import requests
import re
import os
from urllib.parse import urlparse

from dbx2.rest.settings import Settings
from splunklib import modularinput as smi
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dbx2.logger_provider import LoggerProvider
from dbx2.task_server_configuration_provider import TaskServerConfigurationProvider


class DbxDbOutputRunner:
    SCHEME = """<scheme>
        <title>Scheduled DBX DB Output Job Runner</title>
        <use_external_validation>false</use_external_validation>
        <streaming_mode>xml</streaming_mode>
        <use_single_instance>false</use_single_instance>
    </scheme>
    """

    def __init__(self):
        taskserverPort = Settings.read_taskserver_port()
        self.server_db_output_url = "http://localhost:" + str(taskserverPort) + "/api/outputs/{}/run"
        self.modinput_name_regex = re.compile(r"dbx_db_output://([\w.-]+)$")

    def do_scheme(self):
        print(self.SCHEME)

    def init_stream(self):
        sys.stdout.write("<stream>")

    def fini_stream(self):
        sys.stdout.write("</stream>")

    def get_config(self):
        try:
            return smi.InputDefinition.parse(sys.stdin)
        except Exception as e:
            raise Exception(f"Error getting Splunk configuration via STDIN: {str(e)}")

    def stream_events(self):
        start_time = time.time()
        input_definition = self.get_config()
        session_key = input_definition.metadata["session_key"]

        logger = LoggerProvider().provide(session_key=session_key)
        logger.info("feature=output action=execute")

        try:
            modinput_name = next(iter(input_definition.inputs.keys()))
            db_output_name = self.modinput_name_regex.search(modinput_name).group(1)
            logger.info(f"feature=output action=execute name={db_output_name}")

            headers = {
                "content-type": "application/json",
                "X-DBX-SESSION_KEY": session_key,
            }

            s = requests.Session()
            retries = Retry(total=5, backoff_factor=1)
            s.mount("http://", HTTPAdapter(max_retries=retries))

            verify_ssl = self._verify_ssl(self.server_db_output_url)
            response = s.post(url=self.server_db_output_url.format(db_output_name), headers=headers, verify=verify_ssl)

            if response.status_code != 200:
                if response.status_code == 303:
                    logger.info(
                        f"feature=output action=execute name={db_output_name} status=skipped "
                        + f"message=output was executed on other node, status_code={response.status_code}, content={response.content}"
                    )
                else:
                    logger.warning(
                        f"feature=output action=execute name={db_output_name} status=failed "
                        + f"status_code={response.status_code}, content={response.content}"
                    )
            else:
                logger.info(
                    f"feature=output action=execute name={db_output_name} status=success content={response.content}"
                )
        except Exception as e:
            logger.error(f"feature=output action=execute name={db_output_name} status=failed cause={e}")
        finally:
            logger.info(
                f"feature=output action=execute name={db_output_name} status=success execution_time={time.time() - start_time}"
            )

    def run(self):
        if len(sys.argv) > 1:
            if sys.argv[1] == "--scheme":
                self.do_scheme()
            else:
                return 1
        else:
            self.stream_events()

        return 0

    def _verify_ssl(self, host):
        return self._is_fips_enabled() or not self._is_localhost(host)

    @staticmethod
    def _is_localhost(url):
        hostname = urlparse(url).hostname
        return hostname in {"localhost", "127.0.0.1", "::1"}

    @staticmethod
    def _is_fips_enabled():
        fips_enabled = TaskServerConfigurationProvider().get_configuration()
        return fips_enabled or os.getenv("SPLUNK_DBX_FIPS_ENABLED", "false") == "true"


if __name__ == "__main__":
    exit_code = DbxDbOutputRunner().run()
    sys.exit(exit_code)
