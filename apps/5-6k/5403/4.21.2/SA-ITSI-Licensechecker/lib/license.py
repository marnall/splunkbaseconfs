# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import xml.etree.ElementTree as ET


class License(object):

    UNEXPIRED_LICENSE_STATUS = 'VALID'

    # ****************** WARNING: the FUTURE_LICENSE_STATUS variable is used elsewhere in the code *******************
    # This variable is also defined in /apps/SA-ITOA/package/lib/feature_flagging/splunk_license_state_maintainer.py
    # and should be kept in sync.
    FUTURE_LICENSE_STATUS = 'FROM_THE_FUTURE'

    def __init__(self,
                 guid=None,
                 name=None,
                 hash=None,
                 label=None,
                 body=None,
                 expiration_time=None,
                 status=None,
                 group_id=None,
                 subgroup_id=None,
                 add_ons=None):
        self.guid = guid
        self.name = name
        self.hash = hash
        self.label = label
        self.body = body
        self.expiration_time = expiration_time
        self.status = status
        self.group_id = group_id
        self.subgroup_id = subgroup_id
        self.add_ons = add_ons

        if self.body is not None:
            self._load_guid_from_body()
            assert self.guid

        assert self.guid or self.hash, "Either guid or hash should be set"

    def __eq__(self, other):
        if isinstance(other, License):
            if other.guid is not None and self.guid is not None:
                return self.guid == other.guid
            elif other.hash is not None and self.hash is not None:
                return self.hash == other.hash
            else:
                assert False, \
                    "Either guid or hash should be set for both operands. "\
                    "self.guid: {}, other.guid: {}. "\
                    "self.hash: {}. other.hash: {}".format(self.guid, other.guid, self.hash, other.hash)
        return False

    def _load_guid_from_body(self):
        root = ET.fromstring(self.body)
        if self.guid is None:
            self.guid = root.findall("./payload/guid")[0].text

    def is_valid(self):
        return self.status == self.UNEXPIRED_LICENSE_STATUS

    def is_from_future(self):
        return self.status == self.FUTURE_LICENSE_STATUS

    def among_licenses(self, licenses):
        return any(self == lic for lic in licenses)

    def resolve_to_real_license(self, real_licenses):
        """
        This method merges the information in this object with a matching real license.
        Real license is the object that was created from the information we had retrieved from Splunk.

        @type real_licenses: list
        @param real_licenses: License objects created from license information in Splunk

        @rtype: License
        @return: License object with Splunk license data enhanced with the data in this object.
        """
        real_license = next((lic for lic in real_licenses if lic == self), None)
        if real_license is not None:
            real_license.name = self.name
        return real_license
