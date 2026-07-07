import import_declare_test  # isort: skip # noqa: F401
import sys
import time
import json
from alert_actions_base import ModularAlertBase
from solnlib.utils import is_true
from infoblox_helpers.conf_helper import get_credentials
from infoblox_helpers.rest_helper import RestHelper

SOURCE = "infoblox_soc_insights_{}_alert"


class AlertActionSocInsightsDetails(ModularAlertBase):
    """Alert Action."""

    def __init__(self, ta_name, alert_name):
        """Initialise Alert Action."""
        super(AlertActionSocInsightsDetails, self).__init__(ta_name, alert_name)

    def validate_params(self):
        """Validate Params."""
        if not self.get_param("index"):
            self.log_warn("Index is a mandatory parameter, but its value is None. Setting it's value to default.")
            self.configuration["index"] = "default"
        if not self.get_param("global_account"):
            self.log_error("Infoblox Account is a mandatory parameter, but its value is None.")
            return False
        return True

    def get_soc_insights_data(self):
        """Get SOC Insights Data."""
        for event in self.get_events():
            insight_id = event.get('insight_id', "")

            if is_true(self.soc_assets):
                self.get_assets_data(insight_id)
            if is_true(self.soc_indicators):
                self.get_indicators_data(insight_id)
            if is_true(self.soc_events):
                self.get_events_data(insight_id)
            if is_true(self.soc_comments):
                self.get_comments_data(insight_id)

    def get_assets_data(self, insight_id):
        """Get SOC Assets Data."""
        insight_type = "assets"
        self.log_info("Started getting SOC Insights assets data.")
        data = self.infoblox_rest_helper.get_soc_insight_details(
            type=insight_type,
            insight_id=insight_id
        )
        for event in data.get(insight_type, []):
            event.update({"insight_id": insight_id})
            self.insight_assets_events.append(event)

    def get_indicators_data(self, insight_id):
        """Get SOC Indicators Data."""
        insight_type = "indicators"
        self.log_info("Started getting SOC Insights indicators data.")
        data = self.infoblox_rest_helper.get_soc_insight_details(
            type=insight_type,
            insight_id=insight_id
        )
        for event in data.get(insight_type, []):
            event.update({"insight_id": insight_id})
            self.insight_indicators_events.append(event)

    def get_events_data(self, insight_id):
        """Get SOC Events Data."""
        insight_type = "events"
        self.log_info("Started getting SOC Insights events data.")
        data = self.infoblox_rest_helper.get_soc_insight_details(
            type=insight_type,
            insight_id=insight_id
        )
        for event in data.get(insight_type, []):
            event.update({"insight_id": insight_id})
            self.insight_events_events.append(event)

    def get_comments_data(self, insight_id):
        """Get SOC Comments Data."""
        insight_type = "comments"
        self.log_info("Started getting SOC Insights comments data.")
        data = self.infoblox_rest_helper.get_soc_insight_details(
            type=insight_type,
            insight_id=insight_id
        )
        for event in data.get(insight_type, []):
            event.update({"insight_id": insight_id})
            self.insight_comments_events.append(event)

    def ingest_soc_insights_data(self):
        """Ingest SOC Insights Data."""
        if is_true(self.soc_assets):
            self.ingest_assets_data()
        if is_true(self.soc_indicators):
            self.ingest_indicators_data()
        if is_true(self.soc_events):
            self.ingest_events_data()
        if is_true(self.soc_comments):
            self.ingest_comments_data()

    def ingest_assets_data(self):
        """Ingest SOC Assets Data."""
        insight_type = "assets"
        self.log_info("Started ingesting SOC Insights assets data.")
        for asset_data in self.insight_assets_events:
            self.addevent(
                raw=json.dumps(asset_data), sourcetype="infoblox_soc_insights_assets", cam_header=False
            )
        self.writeevents(
            index=self.index,
            source=SOURCE.format(insight_type),
            fext="infoblox_soc_insights_assets"
        )
        self.log_info("Total assets ingested: {}".format(len(self.insight_assets_events)))
        # empty the list so that it can be used again
        self.events = []

    def ingest_indicators_data(self):
        """Ingest SOC Indicators Data."""
        insight_type = "indicators"
        self.log_info("Started ingesting SOC Insights indicators data.")
        for indicator_data in self.insight_indicators_events:
            self.addevent(
                raw=json.dumps(indicator_data), sourcetype="infoblox_soc_insights_indicators", cam_header=False
            )
        self.writeevents(
            index=self.index,
            source=SOURCE.format(insight_type),
            fext="infoblox_soc_insights_indicators"
        )
        self.log_info("Total indicators ingested: {}".format(len(self.insight_indicators_events)))
        # empty the list so that it can be used again
        self.events = []

    def ingest_events_data(self):
        """Ingest SOC Events Data."""
        insight_type = "events"
        self.log_info("Started ingesting SOC Insights events data.")
        for asset_data in self.insight_events_events:
            self.addevent(
                raw=json.dumps(asset_data), sourcetype="infoblox_soc_insights_events", cam_header=False
            )
        self.writeevents(
            index=self.index,
            source=SOURCE.format(insight_type),
            fext="infoblox_soc_insights_events"
        )
        self.log_info("Total events ingested: {}".format(len(self.insight_events_events)))
        # empty the list so that it can be used again
        self.events = []

    def ingest_comments_data(self):
        """Ingest SOC Comments Data."""
        insight_type = "comments"
        self.log_info("Started ingesting SOC Insights comments data.")
        for asset_data in self.insight_comments_events:
            self.addevent(
                raw=json.dumps(asset_data), sourcetype="infoblox_soc_insights_comments", cam_header=False
            )
        self.writeevents(
            index=self.index,
            source=SOURCE.format(insight_type),
            fext="infoblox_soc_insights_comments"
        )
        self.log_info("Total comments ingested: {}".format(len(self.insight_comments_events)))
        # empty the list so that it can be used again
        self.events = []

    def process_event(self, *args, **kwargs):
        """Process events."""
        status = 0
        start_time = time.time()
        try:
            if not self.validate_params():
                return 3
            self.global_account = self.get_param('global_account')
            self.index = self.get_param('index')
            self.soc_assets = self.get_param('assets')
            self.soc_indicators = self.get_param('indicators')
            self.soc_events = self.get_param('events')
            self.soc_comments = self.get_param('comments')
            self.insight_assets_events = []
            self.insight_indicators_events = []
            self.insight_events_events = []
            self.insight_comments_events = []
            self.log_info("Alert action infoblox_soc_insights_details started.")
            self.log_debug((
                f'action=parameter_received assets={self.soc_assets} indicators={self.soc_indicators} '
                f'events={self.soc_events} comments={self.soc_comments} '
                f'global_account={self.global_account} index={self.index}'))

            infoblox_config = {
                "session_key": self.session_key,
                "index": self.index
            }
            account_info = get_credentials(
                session_key=self.session_key,
                account_name=self.global_account
            )
            infoblox_config.update(account_info)

            self.infoblox_rest_helper = RestHelper(infoblox_config, self._logger)

            self.get_soc_insights_data()
            self.ingest_soc_insights_data()

            total_time_taken = time.time() - start_time
            self.log_info("Alert Action completed and total time taken: {}".format(total_time_taken))
            return 0
        except (AttributeError, TypeError) as ae:
            import traceback
            self.log_error(
                "Error: {}. Double check spelling and also verify that a compatible version of "
                "Splunk_SA_CIM is installed.".format(str(ae))
            )
            return 4
        except Exception as e:
            self.log_info("In error handler")
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    exitcode = AlertActionSocInsightsDetails("InfobloxAppForSplunk", "infoblox_soc_insights_details").run(sys.argv)
    sys.exit(exitcode)
