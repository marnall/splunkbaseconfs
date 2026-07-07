import json
import os
import sys

from constants import (SONAR_MESSAGE_HEADER, CONFIGURATION_NAME,
                       CONFIGURATION_STANZA)
from sonar_connector import SonarConnector
from sonar_exception import ValidationException
from sonar_splunk_service_configuration import SonarSplunkServiceConfiguration

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))
import concurrent.futures

from splunklib.six.moves.urllib.error import HTTPError, URLError
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration(streaming=True)
class Sonar(GeneratingCommand):
    index = Option(require=True)
    timestamp = Option(require=False)
    limit = Option(require=False, validate=validators.Integer())
    disable_count = Option(require=False, validate=validators.Boolean(), default=False)

    def generate(self):
        if sys.version_info >= (3, 0):
            self.logger.debug("Running python version 3.x")
        else:
            self.logger.debug("Running python version 2.x")

        cfg = self.service.confs[CONFIGURATION_NAME][CONFIGURATION_STANZA]

        service_configuration = SonarSplunkServiceConfiguration(self.service, cfg, self.metadata) \
            .with_index(self.index) \
            .with_timestamp(self.timestamp) \
            .with_limit(self.limit) \
            .with_disable_count(self.disable_count)

        try:
            connector = SonarConnector(service_configuration.validate())
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(connector.request_data)

            while not connector.done(timeout=2):
                job = self.service.job(self.metadata.searchinfo.sid)
                if int(job.isFinalized) == 1:
                    self.write_error("Job cancelled")
                    exit(0)

            response = future.result()

        except ValidationException as error:
            self.write_error("Validation Error: " + str(error))
            exit(0)

        except HTTPError as error:
            error_message = error.read()
            if error_message is not None and len(error_message) > 0:
                self.write_error("[SONAR]: %s" % error_message.decode("utf-8"))
            else:
                self.write_error("[SONAR]: %s" % error)

        except URLError as error:
            self.write_error("[SONAR]: %s" % " ".join(str(v) for v in error.args))

        except IOError as error:
            self.write_error("[SONAR]: %s" % error)

        else:
            try:
                if response.headers[SONAR_MESSAGE_HEADER] is not None:
                    self.write_warning("[SONAR]: " + response.headers[SONAR_MESSAGE_HEADER])
            except KeyError as error:
                self.logger.debug("Header %s not found. %s" % (SONAR_MESSAGE_HEADER, error))

            chunk = response.readline()  # type: bytes

            while chunk is not None and len(chunk) > 0:
                chunk_str = chunk.decode("utf-8")
                yield json.loads(chunk_str)
                chunk = response.readline()


if __name__ == '__main__':
    dispatch(Sonar, sys.argv, sys.stdin, sys.stdout, __name__)
