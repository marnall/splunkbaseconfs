import sys
import os
import gzip

from splunklib.modularinput import *

from boto.s3.connection import S3Connection
from datetime import datetime, timedelta
import dateutil.parser
import pytz

APP_NAME = "Cisco_CWS_TA"

class CiscocwsScript(Script):

    def get_scheme(self):
        # Setup scheme.
        scheme = Scheme("Cisco CWS Logs")
        scheme.description = "Pulls Logs from Cisco CWS"
        scheme.use_external_validation = True

        # Add arguments
        clientid_argument = Argument("client_id")
        clientid_argument.data_type = Argument.data_type_string
        clientid_argument.description = "CWS Client ID"
        clientid_argument.required_on_create = True
        scheme.add_argument(clientid_argument)

        s3key_argument = Argument("s3_key")
        s3key_argument.data_type = Argument.data_type_string
        s3key_argument.description = "S3 Key for retrieving Logs"
        s3key_argument.required_on_create = True
        scheme.add_argument(s3key_argument)

        clientsecret_argument = Argument("s3_secret")
        clientsecret_argument.data_type = Argument.data_type_string
        clientsecret_argument.description = "S3 Secret for retrieving Logs"
        clientsecret_argument.required_on_create = True
        scheme.add_argument(clientsecret_argument)

        return scheme

    def stream_events(self, inputs, ew):
        now = datetime.utcnow().replace(tzinfo=pytz.UTC)

        for input_name, input_item in inputs.inputs.iteritems():
            ew.log("INFO", "CWSMI -  Starting CWS Input")
            CLIENT_ID = input_item["client_id"]
            AWS_SECRET = input_item["s3_secret"]
            AWS_KEY = input_item["s3_key"]
            filename = "%s.meta" % (input_name.split("//")[1])
            filename = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", APP_NAME, "bin", filename)
            ew.log("INFO", 'CWSMI - client_id=%s aws_secret=%s aws_key=%s' % (CLIENT_ID, AWS_SECRET, AWS_KEY))

            # Get Last Run Date
            try:
                f = open(filename, "r")
                last_run = f.readline()
                f.close()
            except Exception, e:
                ew.log("INFO", 'CWSMI - error reading file filename=%s' % (filename))
                last_run = None

            if last_run:
                last_run_date = dateutil.parser.parse(last_run)
                ew.log("INFO", "CWSMI - Last Run - %s" % last_run_date.isoformat())
            else:
                # Running for first time
                ew.log("INFO", "CWSMI - First Run - Defaulting to last 4 hours")
                last_run_date = now - timedelta(hours=4)

            aws_connection = S3Connection(
                    aws_access_key_id=AWS_KEY,
                    aws_secret_access_key=AWS_SECRET,
                    host="vault.scansafe.com"
                    )

            ew.log("INFO", 'CWSMI - Reading bucket')
            bucket = aws_connection.get_bucket(CLIENT_ID)
            try:
                for key in bucket.list():
                    ew.log("INFO", 'CWSMI - key: %s' % (key,))
                    last_modified_date = dateutil.parser.parse(key.last_modified)
                    if (last_modified_date >= last_run_date):
                        temp_filename = key.name.split('/')[1]
                        temp_filename = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", APP_NAME, "tmp", temp_filename)
                        ew.log("INFO", "CWSMI - Processing filename=%s size=%s etag=%s" % (key.name, key.size, key.etag))
                        ew.log("INFO", "CWSMI - tempfile=%s" % (temp_filename,))
                        tempfile = open(temp_filename , "w")
                        key.get_contents_to_file(tempfile)
                        tempfile.close()
                        ew.log("DEBUG", "CWSMI - Downloaded file %s" % (key.name))
                        tempfile = gzip.open(temp_filename, "r")
                        tempfile_content = tempfile.read()
                        for line in iter(tempfile_content.splitlines()):
                            raw_event = Event()
                            raw_event.stanza = "%s_%s" % (input_name, key.name)
                            raw_event.data = line
                            ew.write_event(raw_event)
                        tempfile.close()
                        os.remove(temp_filename)
                        ew.log("DEBUG", "CWSMI - Deleted file %s" % (key.name))
                    else:
                        ew.log("DEBUG", "CWSMI - Skipped filename=%s date=%s for date reasons" % (key.name, key.last_modified))
            except Exception, e:
                ew.log("[Exception]", 'CWSMI - %s' % (e,))

            # Write Timestamp
            f = open(filename, "w")
            f.write(now.isoformat())
            f.close()

if __name__ == "__main__":
    sys.exit(CiscocwsScript().run(sys.argv))

