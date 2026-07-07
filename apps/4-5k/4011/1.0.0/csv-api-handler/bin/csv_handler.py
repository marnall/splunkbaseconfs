# System import
import os, sys, csv, json, logging


# Splunk Import
from splunk.persistconn.application import PersistentServerConnectionApplication

# Local import
splunk_home = os.getenv('SPLUNK_HOME')
sys.path.append(splunk_home + '/etc/apps/csv-api-handler/bin/')

csv_location = str(splunk_home) + '/etc/apps/csv-api-handler/lookups/'
SUFFIX = '.csv'

__author__ = 'Manoj Jangid'
__version__ = '0.0.1'
__description__ = 'CSV File Handler'


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class CSVHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            json_data = json.loads(in_string)
            csv_name = json_data['rest_path']
            file_name = csv_location + csv_name + SUFFIX

            data_collection = []
            csv_file = open(file_name)
            reader = csv.DictReader(csv_file)
            for row in reader:
                data_collection.append(row)
        except:
            logging.error('error=%s' % (sys.exc_info()[0]))

        return {'payload': json.dumps(data_collection), 'status': 200}

if __name__ == '__main__':
    print ()