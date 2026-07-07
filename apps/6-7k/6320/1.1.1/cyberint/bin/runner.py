import datetime
import logging
from typing import Any, Dict, Generator, Optional

from client import CyberintClient


class CyberintRunner:
    MAX_ALERTS_SIZE = 100

    def __init__(
        self,
        base_url: str,
        access_token: str,
        start_time: str,
        checkpoint_filename: str,
    ):
        self.client = CyberintClient(base_url, access_token)
        self.checkpoint_filename = checkpoint_filename

        try:
            with open(self.checkpoint_filename, 'r') as f:
                self.start_time = f.read()
        except FileNotFoundError:
            self.start_time = start_time

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.client.close()

    def run(self) -> Generator:
        logging.info('Executing Cyberint runner')

        last_run = self.start_time
        logging.info('Last run is %s', last_run)

        alerts = self.client.list_alerts(1, self.MAX_ALERTS_SIZE, modification_date=last_run)
        logging.info('Got %d alerts from Cyberint', len(alerts))

        for alert in alerts:
            if self._update_last_run(last_run, alert['modification_date']):
                logging.debug('Found date newer from last run: %s', alert['modification_date'])
                last_run = alert['modification_date']

            try:
                yield self.format_alert(alert) or alert
            except (KeyError, AttributeError, TypeError):
                logging.warning('Failed to format the alert')
                yield alert

        if last_run != self.start_time:
            logging.debug('Updating last run inside the DB')

            last_run = datetime.datetime.strptime(last_run, self.client.ALERTS_DATE_FORMAT)
            last_run += datetime.timedelta(seconds=1)

            with open(self.checkpoint_filename, 'w') as f:
                f.write(datetime.datetime.strftime(last_run, self.client.ALERTS_DATE_FORMAT))

        logging.info('Finished sending alerts. Last run is %s', last_run)

    def format_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formatting the alert before sending it to Splunk.

        Args:
            alert (Dict[str, Any]): The alert object from Cyberint.

        Returns:
            Dict[str, Any]: The formatted alert to send to Splunk.
        """

        alert['log_category'] = 'Cyberint Category'
        alert_id = alert['ref_id']
        alert_data = alert['alert_data']

        if alert_data.get('csv') is not None:
            alert_data['csv_url'] = self.client.get_alert_attachment_url(
                alert_id, alert_data['csv']['id'])
        else:
            logging.debug('Missing CSV data for alert %s', alert_id)

        report_url = self.client.get_alert_report_url(alert_id)
        if report_url:
            alert['analysis_report_url'] = report_url
        else:
            logging.debug('Missing analysis report for alert %s', alert_id)

        for attachment in alert.get('attachments', []):
            attachment['attachment_url'] = self.client.get_alert_attachment_url(
                alert_id, attachment['id'])

        return alert

    def _update_last_run(self, old_date_str: Optional[str], new_date_str: str) -> bool:
        if not old_date_str:
            return True

        old_date = datetime.datetime.strptime(old_date_str, self.client.ALERTS_DATE_FORMAT)
        new_date = datetime.datetime.strptime(new_date_str, self.client.ALERTS_DATE_FORMAT)

        return new_date > old_date
