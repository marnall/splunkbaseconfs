from acclib.splunk_connection import SplunkConnection
from acclib import event_service
from acclib.date_helper import DateHelper


splunk_connection = SplunkConnection()

try:
    result = []
    alerts = event_service.get_alerts(
        splunk_connection,
        DateHelper.to_unixtime(splunk_connection.argvals.get('start_date', DateHelper.n_days_ago(days=7))),
        DateHelper.to_unixtime(splunk_connection.argvals.get('end_date', DateHelper.current_date()), expire=True),
        splunk_connection.argvals.get('search', ''),
        include_operations=False
    )
    for alert in alerts:
        result.append({
            'created': alert['_time'],
            'feature_name': alert['feature_name'],
            'message': alert['alert_message'],
            'score': alert['score'],
            'file_name': alert['file_name'],
            'last_accessed': alert['last_accessed'],
            'file_path': alert['file_path'],
            'city': alert['src_city'],
            'country': alert['src_country'],
            'region': alert['src_region'],
            'lat': alert['src_lat'],
            'lon': alert['src_lon'],
            'user': alert['alert_user'],
            'src': alert['src'],
            'uuid': alert['alert_uuid']
        })
    splunk_connection.output(result)
except Exception as e:
    splunk_connection.output([{'error': str(e)}])
