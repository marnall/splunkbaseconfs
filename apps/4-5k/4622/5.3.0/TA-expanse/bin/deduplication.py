import ta_expanse_declare

import abc
from constants import ALERT_ID_PATH


class AlertDeduplicationProcessor:
    """The Alerts implementation of deduplication

    Available methods:
        fetch_existing_alerts: queries splunk for the alerts that exist with a server time of > 2
                               days ago from the last start date
        deduplicate: uses the alerts found in fetch_existing_alerts to remove already processed
                     alerts from the new data array

    """

    def __init__(self, dedup_ids=None):
        self.dedup_ids = dedup_ids if dedup_ids is not None else []
        self.total_alerts = 0
        self.deduped_alerts = 0

    @abc.abstractmethod
    def deduplicate(self, helper, alerts):
        """Method to remove already processed data from the new data array

        Args:
            alerts (list[OrderedDict]): a list of the data from an expanse endpoint
        Returns:
            Generator[OrderedDict]: The data with removals taken out
        """
        for alert in alerts:
            helper.log_debug(f"Debugging deduplication: Alerts to dedup {len(self.dedup_ids)}: {self.dedup_ids}")
            self.total_alerts += 1
            helper.log_debug(f"Debugging deduplication: {len(self.dedup_ids)}")
            if alert[ALERT_ID_PATH] not in self.dedup_ids:
                helper.log_debug(f"Debugging deduplication: Alert Added!! {alert[ALERT_ID_PATH]}")
                self.dedup_ids.append(alert[ALERT_ID_PATH])
                yield alert
            else:
                helper.log_debug(f"Debugging deduplication: Alert deduped!! {alert[ALERT_ID_PATH]}")
                self.deduped_alerts += 1
