# Though this import seems to be unused, it is actually required to properly
# configure `sys.path` before importing Splunk components.
import ta_cisco_threat_response_declare  # noqa: F401

import functools
import sys

from requests.exceptions import Timeout as TimeoutError
from splunklib.searchcommands import (
    dispatch,
    validators,
    StreamingCommand,
    Configuration,
    Option,
)
from splunklib import client

from actions import Verdict, Context, Targets
from connect import connect, ConnectError
from constants import SOURCE_TYPE
from lazy import Lazy
from settings import (
    Settings,
    CONFIGURATION_FILE,
    STANZA
)


@Configuration()
class ThreatResponseCommand(StreamingCommand):
    """
    ... | threatresponse verdict = <field> | ...
    ... | threatresponse context = <field> <object_1> .. <object_n> | ...
    ... | threatresponse targets = <field> | ...
    """

    verdict = Option(
        require=False,
        validate=validators.Fieldname()
    )

    context = Option(
        require=False,
        validate=validators.Fieldname()
    )

    targets = Option(
        require=False,
        validate=validators.Fieldname()
    )

    def __init__(self):
        super(ThreatResponseCommand, self).__init__()

        self._action = None

    def prepare(self):
        """ Implementation of the `SearchCommand.prepare`.
        This is a method to work with options, configurations and credentials.
        Note: `self.service` is not available at `__init__`.
        """
        settings = Settings(self.service.confs[CONFIGURATION_FILE][STANZA],
                            self.service.storage_passwords)

        self._action = Lazy(
            self.action,
            tr=Lazy(self.connect, settings),
        )

    def connect(self, settings):
        try:
            return connect(settings, self.logger)
        except ConnectError as error:
            self.error_exit(error)

    def stream(self, records):
        action = self._action

        conn = client.connect(token=self.service.token, port=self.service.port)

        index_name = \
            self.service.confs[CONFIGURATION_FILE][STANZA]['index_name']
        if index_name not in self.service.indexes:
            message = "A '{index}' index does not exist. " \
                      "Please go to Manage Indexes " \
                      "and create the index." \
                .format(index=index_name)
            self.error_exit(None, message=message)
        index = conn.indexes[index_name]

        indexing = self.service \
            .confs[CONFIGURATION_FILE][STANZA]['response_indexing']

        for record in records:
            if action.is_applicable_to(record):
                result = ''
                try:
                    result = action.update(record)
                except TimeoutError as error:
                    self.error_exit(
                        error,
                        message='Cisco SecureX threat response: '
                                'Custom Search Command took too long'
                                ' to respond, try again later.'
                    )
                if result:
                    if bool(int(indexing)):
                        try:
                            index.submit(result, sourcetype=SOURCE_TYPE)
                        except Exception as error:
                            message = "A '{}' index has been disabled " \
                                      "or deleted. " \
                                      "Please go to Manage Indexes and " \
                                      "check the status of the index. " \
                                      "If the index is there, " \
                                      "enable it; " \
                                      "otherwise create it." \
                                      "If the index exists and is enabled, " \
                                      "see the logs." \
                                .format(index_name)
                            self.error_exit(error, message=message)
                yield record

    @property
    def action(self):
        actions = []

        if self.verdict is not None:
            actions.append(
                functools.partial(
                    Verdict,
                    observable_field=self.verdict,
                )
            )

        if self.context is not None:
            actions.append(
                functools.partial(
                    Context,
                    observable_field=self.context,
                    objects=self.fieldnames,
                )
            )

        if self.targets is not None:
            actions.append(
                functools.partial(
                    Targets,
                    observable_field=self.targets,
                )
            )

        if len(actions) != 1:
            self.error_exit(None, 'Please specify exactly one option.')

        return actions[0]


if __name__ == '__main__':
    dispatch(ThreatResponseCommand, sys.argv, sys.stdin, sys.stdout, __name__)
