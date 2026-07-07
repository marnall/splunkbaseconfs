##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test  # noqa: F401 isort: skip

import logging

import splunk_ta_f5_utility as common_utility
from import_declare_test import TEMPLATES_CONF, ta_name
from log_manager import setup_logging
from solnlib import conf_manager
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from splunktaucclib.rest_handler.endpoint import (  # isort: skip
    RestModel,
    SingleModel,
    field,
    validator,
)  # isort: skip

util.remove_http_proxy_env_vars()

fields = [
    field.RestField(
        "description",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255,
            min_len=0,
        ),
    ),
    field.RestField(
        "content", required=True, encrypted=False, default=None, validator=None
    ),
    field.RestField("disabled", required=False, validator=None),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("f5_templates_ts", model, config_name="template")


class F5TemplateHandler(AdminExternalHandler):
    """
    This class handles the parameters in the configuration page
    """

    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)
        self.logger = setup_logging(self.getSessionKey(), "splunk_ta_f5_rh_template")

    def handleList(self, conf_info):
        """
        This method is called when template is rendered with configurable parameters from splunk_ta_f5_bigip_template.conf  # noqa: E501
        after decoding base64 value of content field
        :param conf_info: The dictionary used to display configurable parameters.
        :return: None
        """
        AdminExternalHandler.handleList(self, conf_info)
        for name, value in list(conf_info.items()):
            if value.get("content"):
                value["content"] = common_utility.decode(value["content"])

    def handle_request(self, conf_info, is_handle_edit_operation):
        """
        This method handles request for Create and Edit operation of the template.
        :param conf_info: The dictionary used to display configurable parameters.
        :param is_handle_edit_operation: boolean variable to check whether the operation is Create or Edit.
        :return: None
        """
        stanza_name = self.callerArgs.id
        try:
            session_key = self.getSessionKey()
            cfm = conf_manager.ConfManager(session_key, ta_name)
            templates_conf_obj = cfm.get_conf(TEMPLATES_CONF)
            common_utility.perform_validation(
                self.callerArgs.id,
                self.payload,
                common_utility.params.get("F5_BIGIP_TEMPLATES_CONF_FILE_NAME"),
                endpoint,
                is_handle_edit_operation,
                self.getSessionKey(),
            )
            # Gives the content of the template
            content = self.payload[common_utility.params.get("CONTENT_PARAM")]

            self.payload["content"] = str(
                (common_utility.encode(self.payload["content"]))
            )
            templates_conf_obj.update(stanza_name, self.payload)
            self.payload["content"] = content
        except Exception as e:
            self.logger.error("Error occured while listing the templates: " + str(e))
        if is_handle_edit_operation:
            self.logger.info(
                "Successfully edited the template: {}".format(self.callerArgs.id)
            )
        else:
            self.logger.info(
                "Successfully created the template: {}".format(self.callerArgs.id)
            )

    def handleCreate(self, conf_info):
        """
        This method is called when new template is created. It stores values of configurable parameters after
        encoding value of content field in base64 string
        :param conf_info: The dictionary containing configurable parameters.
        :return: None
        """
        self.handle_request(conf_info, False)

    def handleEdit(self, conf_info):
        """
        This method is called when template is updated. It updates values of configurable paramters after
        encoding value of content field in base64 string
        :param conf_info: The dictionary containing configurable parameters.
        :return: None
        """
        self.handle_request(conf_info, True)

    def handleRemove(self, confInfo):
        """
        This method is called when template is deleted.
        It deletes the template raw if it's not used in task configuration.
        :param conf_info: The dictionary containing configurable parameters.
        :return: None
        """
        default_templates = [
            "Standard_GlobalLB_v16_1_0",
            "Standard_LocalLB",
            "Standard_Management",
            "Standard_Network",
            "Standard_System",
        ]
        # This checks if template to be deleted is default template or not.
        # If default template is attempted to be deleted, it raises an RestError
        if self.callerArgs.id in default_templates:
            self.logger.error(
                '"{}" cannot be deleted because it is default template.'.format(
                    self.callerArgs.id
                ),
            )
            raise RestError(
                405,
                '"{}" cannot be deleted because it is default template.'.format(
                    self.callerArgs.id
                ),
            )
        is_input_exist, field_name = common_utility.is_input_exists(
            self.callerArgs.id, self.getSessionKey(), "templates"
        )
        if is_input_exist:
            self.logger.error(
                '"{}" cannot be deleted because it is used in inputs.'.format(
                    field_name
                ),
            )
            raise RestError(
                405,
                '"{}" cannot be deleted because it is used in inputs.'.format(
                    field_name
                ),
            )
        # If template is not in use, continue to remove the template by calling super method
        AdminExternalHandler.handleRemove(self, confInfo)
        self.logger.info(
            "Successfully deleted the template: {}".format(self.callerArgs.id)
        )


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=F5TemplateHandler,
    )
