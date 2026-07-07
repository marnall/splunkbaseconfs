from acclib.splunk_connection import SplunkConnection
from acclib import csv_helper
from acclib.date_helper import DateHelper


splunk_connection = SplunkConnection()

try:
    result = csv_helper.download_ciso_activity_csv(
        splunk_connection,
        splunk_connection.argvals.get('filters', '').split('|'),
        splunk_connection.argvals.get('start_date'),
        splunk_connection.argvals.get('end_date'),
        splunk_connection.argvals.get('regions', '*').split('|'),
        splunk_connection.argvals.get('client_names', '*').split('|'),
        splunk_connection.argvals.get('domain', '*').split('|'),
        splunk_connection.argvals.get('username', '*').split('|'),
        splunk_connection.argvals.get('search', '')
    )
    splunk_connection.output(result)
except Exception as e:
    splunk_connection.output([{'error': str(e)}])
