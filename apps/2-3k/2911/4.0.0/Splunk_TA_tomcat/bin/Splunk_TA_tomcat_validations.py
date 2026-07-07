#
# SPDX-FileCopyrightText: 2026 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from solnlib import log
import tomcat_consts as c
from splunktaucclib.rest_handler.endpoint.validator import Validator

_LOGGER = log.Logs().get_logger(c.INPUT_VALIDATION_LOG_FILE)


class SignatureParamsValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying Signature
        and Params while storing input's information."""

        if len(data.get("params").split(",")) == len(data.get("signature").split(",")):
            return True
        else:
            _LOGGER.info(
                "For every signature type, there should be a respective parameter in the params "
                "field. Values for Signature are {} and Params are {}".format(
                    data.get("params").split(","),
                    data.get("signature").split(","),
                )
            )
            self.put_msg(
                "For every signature type, there should be "
                "a respective parameter in the params field."
            )
            return False
