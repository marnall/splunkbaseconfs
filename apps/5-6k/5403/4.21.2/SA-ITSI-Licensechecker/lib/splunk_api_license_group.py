# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.


class SplunkAPILicenseGroup(object):
    def __init__(self, name, active):
        self.name = name
        self.active = active
