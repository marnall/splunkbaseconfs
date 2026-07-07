from __future__ import annotations

import os
import sys
from collections import OrderedDict
from collections.abc import Generator


try:
    from typing_extensions import override
except ImportError:
    # Define a no-op decorator
    def override(func):
        return func


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

from ipinfo.bundles import MaxBundle
from ipinfo.errors import (
    APIRequestException,
    APITokenNotFoundException,
    InvalidPrefixException,
    MMDBNotFoundException,
    RESTAPIOnlyBundleException,
)
from ipinfo.utils import get_config
from ipinfo.validators import ListOrBoolean
from splunklib.searchcommands import dispatch, validators
from splunklib.searchcommands.decorators import Configuration, Option
from splunklib.searchcommands.streaming_command import StreamingCommand


@Configuration()
class IPinfoMaxCommand(StreamingCommand):
    prefix: Option = Option(require=False, default=False, validate=ListOrBoolean())
    restapi: Option = Option(require=False, default=False, validate=validators.Boolean())
    bundle: MaxBundle = MaxBundle()

    @override
    def prepare(self):
        # We read the distributed configuration here so we can reliably retrieve the replication
        # config, at this point the command has still not ran and we edit the configuration
        # with no issues
        replication = get_config("replicate_lookup", self.service)
        self._configuration.distributed = replication == "Yes"

        fieldnames: list[str] = self.fieldnames or []
        method = get_config("method", self.service)
        if self.restapi:
            method = "RESTAPI"
        restapi_mode = method == "RESTAPI"
        try:
            self.bundle.prepare(fieldnames, self.prefix, restapi_mode, self.service)
        except (MMDBNotFoundException, InvalidPrefixException, APITokenNotFoundException, RESTAPIOnlyBundleException) as exc:
            self.write_error(str(exc))
            raise

    @override
    def stream(self, records: Generator[OrderedDict[str, str], None, None]) -> Generator[OrderedDict[str, str], None, None]:
        try:
            yield from self.bundle.stream(records)
        except APIRequestException as exc:
            self.write_error(str(exc))
            raise
        except Exception as exc:
            raise


dispatch(IPinfoMaxCommand, sys.argv, sys.stdin, sys.stdout, __name__)
