#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
"""

* isort ignores:
- isort: skip = Should not be sorted.
* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import splunk_ta_remedy_declare  # isort: skip # noqa: F401

import remedy_helper
import splunk.Intersplunk as sI
from logger_manager import get_logger

from remedy_rest_command_base import (  # isort: skip
    INCIDENT_CREATE_OPTIONAL_FIELDS,
    INCIDENT_CREATE_REQUIRED_FIELDS,
    handle_create_incident,
    parse_arguments,
)

_LOGGER = get_logger("rest_incident")


def main():
    results, dummyresults, settings = sI.getOrganizedResults()
    session_key = settings["sessionKey"]

    required_fields, default_fields = remedy_helper.get_remedy_fields(
        session_key, "create_incident_rest"
    )

    events = parse_arguments(
        required_fields.union(INCIDENT_CREATE_REQUIRED_FIELDS),
        INCIDENT_CREATE_OPTIONAL_FIELDS,
    )

    _LOGGER.info("Start of Single Incident creation script")
    try:
        handle_create_incident(events, session_key)
    except Exception as err:
        _LOGGER.exception("Error occured in Single Incident creation script: ")
        sI.parseError(err)

    _LOGGER.info("End of Single Incident creation script")


if __name__ == "__main__":
    main()
