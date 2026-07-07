#!/usr/bin/env python3.9
#
# File: command_amelookupreferences.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
from collections.abc import Generator
from http import HTTPStatus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import Configuration, GeneratingCommand, Option, dispatch

# Import modules from ../lib
# ame imports
from ame.command_ame import AmeCommand
from ame.consts.Handlers import SITEPATH
from dpshared.consts.LogEntryStatus import LogEntryStatus
from dpshared.models.FastAPIResponse import InternalResponse
from dpshared.models.LookupReferencesEntry import LookupReferencesEntry

COMMAND_NAME = "amelookupreferences"


@Configuration(type="reporting")
class amelookupreferences(GeneratingCommand, AmeCommand):  # noqa: N801
    """
    ##Syntax
    | amelookupreferences key="0abcfcafe7" type="tenant | template | notification | ..."
    OR
    | amelookupreferences object_name="my_template_name" tenant_uid="my_tenant" type="template"
    ##Description
    Custom search command to get the usages of a given key.
    """

    key = Option(require=False)
    object_name = Option(require=False)
    tenant_uid = Option(require=False)
    type = Option(require=True)

    def __init__(self) -> None:
        GeneratingCommand.__init__(self)
        AmeCommand.__init__(self)

    def generate(self) -> Generator[dict, None, None]:
        try:
            self.setup_metadata()
            if not self.key and (not self.object_name or not self.tenant_uid):
                self.write_error(
                    f"[{COMMAND_NAME}]: Either key or object_name and tenant_uid must be provided"
                )
                return
            self._datapunctum_logger.info(
                {
                    "action": COMMAND_NAME,
                    "status": LogEntryStatus.SUCCESS,
                    "key": self.key,
                    "name": self.object_name,
                    "tenant_uid": self.tenant_uid,
                    "type": self.type,
                }
            )
            params_dict = {
                "key": self.key,
                "object_name": self.object_name,
                "tenant_uid": self.tenant_uid,
                "type": self.type,
            }
            if not self.key:
                del params_dict["key"]
            if not self.object_name:
                del params_dict["object_name"]
            if not self.tenant_uid:
                del params_dict["tenant_uid"]
            response = self.sdk_wrapper.get_internal_endpoint(
                SITEPATH.AME_OBJECTS_REFERENCES,
                payload_type=InternalResponse[list[LookupReferencesEntry]],
                **params_dict,
            )
            if response.status >= HTTPStatus.BAD_REQUEST:
                self._datapunctum_logger.error(
                    {
                        "action": COMMAND_NAME,
                        "status": LogEntryStatus.FAILED,
                        "messages": response.messages,
                    }
                )
                for message in response.messages:
                    self.write_error(f"[{COMMAND_NAME}]: {message.text}")
                return
            if not response.payload:
                self._datapunctum_logger.debug(
                    {
                        "action": COMMAND_NAME,
                        "status": LogEntryStatus.ABORTED,
                        "reason": "No references found",
                        "messages": response.messages,
                        "response": response.model_dump(),
                    }
                )
                self.write_info(f"[{COMMAND_NAME}]: No references found")
                return
            self._datapunctum_logger.debug(
                {
                    "action": COMMAND_NAME,
                    "status": LogEntryStatus.SUCCESS,
                    "references": response.payload,
                }
            )
            for reference in response.payload:
                yield self.gen_record(**reference.model_dump())
            self.write_info(f"[{COMMAND_NAME}]: Finished processing events")
        except Exception:
            self._datapunctum_logger.exception(
                {
                    "action": COMMAND_NAME,
                    "status": LogEntryStatus.FAILED,
                    "user": self._metadata.searchinfo.username
                    if hasattr(self._metadata.searchinfo, "username")
                    else "unknown",
                }
            )
            self.write_error(
                f"[{COMMAND_NAME}]: An error occurred. Check the logs for more details"
            )
            return


dispatch(amelookupreferences, sys.argv, sys.stdin, sys.stdout, __name__)
