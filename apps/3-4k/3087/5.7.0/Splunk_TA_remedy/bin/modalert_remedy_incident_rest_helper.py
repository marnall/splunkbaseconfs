#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
# encoding = utf-8

import remedy_incident_rest_alert_base as riab


def process_event(helper, *args, **kwargs):

    # The following example gets and sets the log level
    helper.set_log_level(helper.log_level)
    helper.log_info("Alert action remedy_incident started.")
    handler = riab.RemedyRestIncidentAlertBase(helper)
    handler.handle()
    return 0
