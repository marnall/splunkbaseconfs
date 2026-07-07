#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#


class AlertUtils:
    def __init__(self, input_params, per_page, checkpoint_dict):
        self.input_params = input_params
        self.alert_type = input_params.get("alert_type", "code_scanning_alerts")
        self.per_page = per_page
        self.checkpoint_dict = checkpoint_dict
        self.request_params = {
            "per_page": str(self.per_page),
            "direction": "asc",
            "sort": "updated",
        }

    def get_params(self):
        """
        The method does initial setup and for secret_scanning_alerts
        based on the checkpoint if there is an after parameter the
        direction and sort are removed from request parameters
        """
        if self.alert_type == "code_scanning_alerts":
            self.set_code_scanning_params()
        elif self.alert_type == "dependabot_alerts":
            self.set_dependabot_params()
        else:
            if self.checkpoint_dict.get("last_after", "") != "":
                self.request_params = {"per_page": str(self.per_page)}
            self.set_secret_scanning_params()
        return self.request_params

    def set_code_scanning_params(self):
        """
        This method helps setting up the request params for
        code_scanning_params. If all is selected for any of the params
        then that parameter is excluded from the request params
        """
        if self.input_params.get("severity", "all") != "all":
            self.request_params["severity"] = self.input_params.get("severity")
        if self.input_params.get("state", "all") != "all":
            self.request_params["state"] = self.input_params.get("state")

    def set_dependabot_params(self):
        """
        This method helps setting up the request params for
        dependabot_alerts. If all is selected for any of the params
        then that parameter is excluded from the request params
        """
        if self.input_params.get("dependabot_severity", "all") != "all":
            self.request_params["severity"] = self.input_params.get(
                "dependabot_severity",
            )
        if self.input_params.get("dependabot_state", "all") != "all":
            self.request_params["state"] = self.input_params.get(
                "dependabot_state",
            )
        if self.input_params.get("dependabot_ecosystem", "all") != "all":
            self.request_params["ecosystem"] = self.input_params.get(
                "dependabot_ecosystem",
            )
        if self.input_params.get("dependabot_scope", "all") != "all":
            self.request_params["scope"] = self.input_params.get(
                "dependabot_scope",
            )

    def set_secret_scanning_params(self):
        """
        This method helps setting up the request params for
        secret_scanning_alerts. If all is selected for any of the params
        then that parameter is excluded from the request params
        """
        self.request_params["state"] = self.input_params.get(
            "secret_scanning_state", "open"
        )
        if self.input_params.get("severity", "all") != "all":
            self.request_params["severity"] = self.input_params.get("severity")
        if self.input_params.get("secret_scanning_resolution", "all") != "all":
            self.request_params["resolution"] = self.input_params.get(
                "secret_scanning_resolution",
            )
        if self.input_params.get("secret_scanning_validity", "all") != "all":
            self.request_params["validity"] = self.input_params.get(
                "secret_scanning_validity",
            )
