#!/usr/bin/env python3.9
#
# File: command_ameobsgroupinfo.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import annotations

import os
import sys
from collections.abc import Generator
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import Configuration, EventingCommand, Option, dispatch

from ame.command_ame import AmeCommand
from ame.consts.Handlers import SITEPATH
from ame.handlers.ObjectsHandler import FetchableObject, ObjectResponsePayload
from ame.models.observables.ObservableGroup import ObservableGroup
from dpshared.models.FastAPIResponse import InternalResponse

if TYPE_CHECKING:
    from splunklib.searchcommands.internals import RecordWriter

COMMAND_NAME = "ameobsgroupinfo"


@Configuration()
class ameobsgroupinfo(EventingCommand, AmeCommand):  # noqa: N801
    if TYPE_CHECKING:
        _record_writer: RecordWriter
    """
    ##Syntax
    | ameobsgroupinfo ...
    ##Description
    Custom search command to serve information for observable groups.
    """

    tenant_uids = Option(require=False)
    key_field = Option(require=False, default="observable_group")
    initial_run = Option(require=False, default=True)

    def __init__(self) -> None:
        EventingCommand.__init__(self)
        AmeCommand.__init__(self)

    def _create_observable_group_columns(
        self, observable_group: ObservableGroup
    ) -> dict[str, Any]:
        return {
            f"{self.key_field}.observable_group_name": observable_group.name,
            f"{self.key_field}.observable_group_description": observable_group.description,
            f"{self.key_field}.observable_group_scope": observable_group.scope,
            f"{self.key_field}.observable_group_additional_fields": observable_group.additional_fields,
        }

    def get_observable_groups(self, tenant_uids: list[str]) -> list[ObservableGroup]:
        response = self.sdk_wrapper.get_internal_endpoint(
            SITEPATH.AME_OBJECTS,
            payload_type=InternalResponse[ObjectResponsePayload],
            tenant_uids=tenant_uids,
            objects=FetchableObject.OBSERVABLE_GROUPS,
        )
        if response.status != HTTPStatus.OK:
            response_messages = [message.text for message in response.messages]
            raise Exception(
                f"Failed to get observable groups: {response.status} - {','.join(response_messages)}"
            )
        if not response.payload or not response.payload.observable_groups:
            raise Exception(
                f"Failed to get observable groups: {response.status} - Received empty reply"
            )
        return response.payload.observable_groups

    def transform(self, records: list[dict]) -> Generator[dict, None, None]:
        try:
            if self.initial_run:
                self.setup_metadata()
                separated_tenant_uids: list[str] = (
                    self.tenant_uids.split(",") if self.tenant_uids else []
                )
                separated_tenant_uids = list(
                    {
                        tenant_uid.strip()
                        for tenant_uid in separated_tenant_uids
                        if tenant_uid.strip()
                    }
                )
                observable_groups = self.get_observable_groups(tenant_uids=separated_tenant_uids)
                self.observable_groups_map: dict[str, ObservableGroup] = {
                    og.key: og for og in observable_groups
                }

                self.initial_run = False

            self.write_info(f"[{COMMAND_NAME}]: Starting to process events")

            for record in records:
                observable_group_key = record.get(self.key_field)
                if observable_group_key:
                    observable_group = self.observable_groups_map.get(observable_group_key)
                    if observable_group:
                        observable_group_columns = self._create_observable_group_columns(
                            observable_group
                        )
                        for key, value in observable_group_columns.items():
                            self.add_field(record, key, value)

                yield record

        except Exception as exc:
            self._datapunctum_logger.exception(
                {
                    "action": COMMAND_NAME,
                    "status": "failed",
                    "exception": exc,
                    "user": self._metadata.searchinfo.username
                    if hasattr(self._metadata.searchinfo, "username")
                    else "unknown",
                }
            )
            self._datapunctum_logger.exception(exc)
            raise exc

        self.write_info(f"[{COMMAND_NAME}]: Finished processing events")


dispatch(ameobsgroupinfo, sys.argv, sys.stdin, sys.stdout, __name__)
