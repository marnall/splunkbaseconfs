#
# SPDX-FileCopyrightText: 2025 Splunk LLC.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import logging
from typing import List

import import_declare_test  # noqa: 401
from splunk_ta_jira_cloud_validation import Validator
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import RestModel, SingleModel, field
from splunktaucclib.rest_handler.error import RestError
import jira_cloud_utils as utils
import jira_cloud_consts as jcc

util.remove_http_proxy_env_vars()


fields: List[field.RestField] = []
model = RestModel(fields, name=None)


endpoint = SingleModel("splunk_ta_jira_cloud_domain", model, config_name="domain")


class JiraCloudDomainExternalHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleEdit(self, confInfo):
        Validator(session_key=self.getSessionKey()).validate_domain(
            domain=self.callerArgs.id
        )
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        Validator(session_key=self.getSessionKey()).validate_domain(
            domain=self.callerArgs.id
        )
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        session_key = self.getSessionKey()
        domain_name = self.callerArgs.id
        logger = utils.set_logger(session_key, jcc.JIRA_CLOUD_VALIDATION)
        try:
            res = utils.get_conf_details(
                session_key, logger, jcc.API_TOKEN_DETAILS_CONF_FILE
            )
            if res:
                for acc_name, acc_props in res.items():
                    if acc_props.get("domain", "") == domain_name:
                        raise RestError(
                            409,
                            "Cannot delete the domain as it is already been used in {}.".format(
                                acc_name
                            ),
                        )
        except RestError as e:
            logger.error(
                "Cannot delete the domain as it is already been used in {}.".format(
                    acc_name
                )
            )
            raise RestError(
                409,
                "Cannot delete the domain as it is already been used in {}.".format(
                    acc_name
                ),
            )
        except Exception as e:
            logger.error("Error while deleting the domain: {}".format(str(e)))
            raise RestError(500, "Error while deleting the domain. Please try again.")
        AdminExternalHandler.handleRemove(self, confInfo)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=JiraCloudDomainExternalHandler,
    )
