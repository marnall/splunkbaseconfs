import os
import traceback

import import_declare_test  # noqa: F401
import splunk.admin as admin
from log_helper import setup_logging
from thousandeyes_client import ThousandEyesClient
from thousandeyes_utils import get_account_id

logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class ThousandEyesAlertRules(admin.MConfigHandler):
    """Get the Alert Rules data."""

    def setup(self):
        self.supportedArgs.addReqArg("thousandeyes_user")
        self.supportedArgs.addReqArg("thousandeyes_acc_group")

    def handleList(self, confInfo):
        session_key = self.getSessionKey()
        thousandeyes_user = self.callerArgs.data.get("thousandeyes_user")[0]
        acc_group = self.callerArgs.data.get("thousandeyes_acc_group")[0]
        aid = get_account_id(acc_group)
        try:
            logger.info(
                f"Fetching alert rules from user {thousandeyes_user} account id {aid}."
            )
            client = ThousandEyesClient(session_key, thousandeyes_user, logger)

            # Check if the user has the required permissions to access alert rules
            self._check_alerts_auth_scope(client, aid)

            rules_data = client.get_alert_rules(aid)

            if "alertRules" in rules_data:
                for rule in rules_data["alertRules"]:
                    rule_id = str(rule["ruleId"])
                    rule_name = rule.get("ruleName", "Unknown")
                    alert_type = rule.get("alertType", "Unknown")
                    severity = rule.get("severity", "Unknown")

                    # Create display name with more context
                    display_name = f"{rule_name} ({alert_type}, {severity})"

                    confInfo[rule_id].append("name", rule_id)
                    confInfo[rule_id].append("display_name", display_name)
                    confInfo[rule_id].append("rule_name", rule_name)
                    confInfo[rule_id].append("alert_type", alert_type)
                    confInfo[rule_id].append("severity", severity)
                    confInfo[rule_id].append("expression", rule.get("expression", ""))
                    confInfo[rule_id].append(
                        "is_default", str(rule.get("isDefault", False))
                    )

                    # Add test information if available
                    if "tests" in rule:
                        test_names = [
                            test.get("testName", "Unknown") for test in rule["tests"]
                        ]
                        confInfo[rule_id].append("test_names", ", ".join(test_names))
            else:
                logger.warning("No 'alertRules' key found in response")
        except Exception as e:
            logger.error(
                f"Error occurred while fetching alert rules: {e} {traceback.format_exc()}"
            )
            raise Exception(
                f"Error occurred while fetching alert rules: {e} Please check the logs."
            )

    def _check_alerts_auth_scope(self, client, aid):
        """
        Check if the user has the required permissions to access alert rules.
        This is a placeholder for actual permission checks.
        """
        try:
            webhooks = client.get_webhooks(aid)
            if len(webhooks.get("webhooks", [])) > 0:
                logger.info("User has access to webhooks.")
        except Exception as e:
                logger.error(
                    f"Error occurred while fetching webhooks: {e} {traceback.format_exc()}"
                )
                raise Exception(
                    f"Error occurred while fetching webhooks: {e}. Please check the logs."
                )




if __name__ == "__main__":
    admin.init(ThousandEyesAlertRules, admin.CONTEXT_NONE)
