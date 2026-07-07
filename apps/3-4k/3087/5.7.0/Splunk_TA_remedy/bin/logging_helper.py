#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from solnlib.log import Logs


def get_logger(name):
    return Logs().get_logger(name)
