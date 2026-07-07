""" Google Analytics Report Input for Splunk """

import sys
from datetime import datetime, timedelta
import os
import json
from splunklib.modularinput import Argument
from splunklib.modularinput import Script
from splunklib.modularinput import Event
from splunklib.modularinput import Scheme
from apiclient.discovery import build # pylint: disable=import-error
from oauth2client.file import Storage
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path # pylint: disable=import-error


def load_checkpoint(file_path):
    """ Loads checkpoint file and returns its value represented as a datetime object """
    if os.path.isfile(file_path):
        checkpoint_str = open(file_path, 'r').read()
        return datetime.strptime(checkpoint_str, "%Y-%m-%d")
    # Checkpoint doesn't exist
    return False


def save_checkpoint(file_path, day):
    """ Saves datetime object to checkpoint file """
    with open(file_path, 'w') as f:
        f.write(day.strftime("%Y-%m-%d"))


def initialize_analyticsreporting():
    """Initializes an Analytics Reporting API V4 service object.

    Returns:
      An authorized Analytics Reporting API V4 service object.
    """
    key_location = make_splunkhome_path(['etc', 'apps', 'TA-google_analytics_reporting', 'bin',
                                         'google_analytics_input_google_analytics_creds'])
    storage = Storage(key_location)
    credentials = storage.get()

    # Build the service object.
    analytics = build('analyticsreporting', 'v4', credentials=credentials)

    return analytics


def get_report(analytics, metrics, dimensions, date, view_id):
    """Queries the Analytics Reporting API V4.

    Args:
      analytics: An authorized Analytics Reporting API V4 service object.
      metrics: A list of metrics names. Must have at least one.
      dimensions: A list of dimensions (can be empty)
      date: A past date in the formay YYYY-MM-DD
      view_id: Google Analytics view ID
    Returns:
      The Analytics Reporting API V4 response.
    """
    metrics_list = []
    for metric in metrics:
        metrics_list.append({"expression": metric})
    dimensions_list = [{"name": "ga:dateHour"}]
    for dimension in dimensions:
        dimensions_list.append({"name": dimension})
    return analytics.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': view_id,
                    'dateRanges': [{'startDate': date, 'endDate': date}],
                    'metrics': metrics_list,
                    'dimensions': dimensions_list
                }]
        }
    ).execute()


def generate_events(response):
    """Parses and prints the Analytics Reporting API V4 response.

    Args:
      response: An Analytics Reporting API V4 response.
    """
    events = []
    for report in response.get('reports', []):
        column_header = report.get('columnHeader', {})
        dimension_headers = column_header.get('dimensions', [])
        metric_headers = column_header.get('metricHeader', {}).get('metricHeaderEntries', [])

        for row in report.get('data', {}).get('rows', []):
            dimensions = row.get('dimensions', [])
            date_range_values = row.get('metrics', [])

            event = {}
            for header, dimension in zip(dimension_headers, dimensions):
                event[header] = dimension

            for values in date_range_values:
                for metric_header, value in zip(metric_headers, values.get('values')):
                    event[metric_header.get('name')] = value
            events.append(event)
    return events


def get_backfill_timestamp(backfill):
    """ Generate a datetime <backfill> days ago """
    now = datetime.now()
    start_of_backfill = now - timedelta(days=backfill)
    return start_of_backfill.strftime("%Y-%m-%d")


class GAnalyticsInput(Script):
    """ Google Analytics Report Input for Splunk """

    def get_scheme(self):
        scheme = Scheme("Google Analytics Input")
        scheme.description = ("Daily input which indexes a list of metrics over a list of "
                              "dimensions")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        viewid_arg = Argument(
            name="view_id",
            title="View ID",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(viewid_arg)

        metrics_arg = Argument(
            name="metrics",
            title="Metrics",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(metrics_arg)

        dimensions_arg = Argument(
            name="dimensions",
            title="Dimensions",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=True
        )
        scheme.add_argument(dimensions_arg)

        backfill_arg = Argument(
            name="backfill",
            title="Backfill",
            data_type=Argument.data_type_number,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(backfill_arg)
        return scheme

    def validate_input(self, definition):
        """ Input validation. Stubbed out for now """
        return

    def stream_events(self, inputs, ew):
        for input_name, input_item in inputs.inputs.iteritems():
            checkpoint_dir = os.path.join(inputs.metadata['checkpoint_dir'], input_name.split(
                '//')[-1])
            dimensions = input_item.get("dimensions", None)
            if dimensions:
                dimensions = dimensions.replace(' ', '').split(',')
            else:
                dimensions = []
            backfill = int(input_item["backfill"])
            if backfill < 0:
                raise Exception("Backfill (%d) can't be negative" % backfill)
            checkpoint = load_checkpoint(checkpoint_dir)
            if not checkpoint:
                checkpoint = datetime.now() - timedelta(days=backfill)

            analytics = initialize_analyticsreporting()

            working_date = checkpoint
            # Keep requesting days worth of metrics until working_date=today
            while working_date.strftime("%Y-%m-%d") != datetime.now().strftime("%Y-%m-%d"):
                reports = get_report(analytics,
                                     input_item["metrics"].replace(' ', '').split(','),
                                     dimensions,
                                     working_date.strftime("%Y-%m-%d"),
                                     input_item.get("view_id"))
                events = generate_events(reports)
                for event_dict in events:
                    event = Event()
                    event.stanza = input_name
                    event.data = json.dumps(event_dict)
                    ew.write_event(event)
                working_date = working_date + timedelta(days=1)
            save_checkpoint(checkpoint_dir, working_date)


if __name__ == "__main__":
    exitcode = GAnalyticsInput().run(sys.argv)
    sys.exit(exitcode)
