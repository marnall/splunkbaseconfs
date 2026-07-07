#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

# encoding = utf-8


import remedy_incident_alert_base as riab


def process_event(helper, *args, **kwargs):

    # The following example gets and sets the log level
    helper.set_log_level(helper.log_level)
    helper.log_info("Alert action remedy_incident started.")
    handler = riab.RemedyIncidentAlertBase(
        helper.settings, helper.settings["server_uri"]
    )
    handler.handle()
    return 0
