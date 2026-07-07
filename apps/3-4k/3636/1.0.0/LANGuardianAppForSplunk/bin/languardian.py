import logging as log
import csv
import json
import base64
import re
from ModularInput import *
from RESTClient import *
from Utilities import *
# Splunk Libraries
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

__author__ = 'ksmith'

_MI_APP_NAME = 'LANGuardian App For Splunk Modular Input'
_APP_NAME = 'LANGuardianAppForSplunk'
_SPLUNK_HOME = make_splunkhome_path([""])

log_location = os.path.join(_SPLUNK_HOME, "var", "log", "splunk", _APP_NAME)
if not os.path.isdir(log_location):
    os.mkdir(log_location)
output_file_name = os.path.join(log_location, 'modularinput.log')
log.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=output_file_name,
                filemode='a+', level=log.INFO, datefmt='%Y-%m-%d %H:%M:%S %z')
log.Formatter.converter = time.gmtime


class LANGuardianAppForSplunkRESTclient(RESTClient):
    def _build_url(self):
        return "{}/netmon/view.cgi".format(self._hostname)

    def _call(self, *args, **kwargs):
        try:
            payload = self._payload(rid=kwargs["rid"], lg_login_username=kwargs["user"],
                                    lg_login_password=kwargs["password"])
            fullUrl = "{}://{}?{}&output=csv&human&t={}-{}".format(kwargs["http_type"], self._build_url(), payload, kwargs["starttime"],
                                                              kwargs["endtime"])
            return self._read(fullUrl, payload=None)
        except Exception, e:
            self._catch_error(e)

    def get_events(self, **kwargs):
        return self._call(**kwargs)


class LANGuardianAppForSplunkModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        if len(val_data["hostname"]) > 255:
            raise Exception("Hostname cannot be longer than 255 characters.")

        if val_data["interval"] <= 300:
            raise Exception("Interval must be greater than 5 minutes.")

        return True


MI = LANGuardianAppForSplunkModularInput(app_name=_APP_NAME, scheme={
    "title": "LANGuardian App For Splunk",
    "description": "LANGuardian App For Splunk consumes individual reports via API for integration.",
    "args": [
        {"name": "hostname",
         "description": "The hostname for the NetFort appliance",
         "title": "NetFort Appliance"
         },
        {"name": "report_ids",
         "description": "Report IDs for reports to be indexed. Comma separated list.",
         "title": "Report IDs",
         "required_on_create": False
         },
        {"name": "report_user",
         "description": "Username for running reports",
         "title": "Username"
         },
        {"name": "proxy_name",
         "description": "The stanza name for a configured proxy.",
         "title": "Proxy Name"
         },
        {"name": "http_type",
         "description": "Specify HTTP or HTTPS to connect to host.",
         "title": "HTTP/HTTPS to host"
         },
        {"name": "report_credential_realm",
         "description": "Stanza Name to use for credentials",
         "title": "Credential Realm"}
    ]
})

chardet_egg = os.path.join(os.path.dirname(__file__), "chardet-2.3.0-py2.7.egg")
sys.path.append(chardet_egg)

import chardet

def run():
    MI.start()
    try:
        MI.config()
        utils = Utilities(app_name=_APP_NAME, session_key=MI.get_config("session_key"))
        report_user = MI.get_config("report_user")
        report_pwd = utils.get_credential(MI.get_config("report_credential_realm"), report_user)
        report_ids = MI.get_config("report_ids")
        report_http_type = MI.get_config("http_type")

        log.debug("report_pwd: {}".format(report_pwd))
        if report_pwd is None or report_pwd == "none":
            err_msg = "No credential found for user: {}".format(report_user)
            log.error("No credential found for user: {}".format(report_user))
            MI.print_error(err_msg)
            exit()
        else:
            MI.log.debug(
                "Report user: {}, pwd_length: {}".format(report_user, len(report_pwd)))

        if report_ids is None or report_ids is False or report_ids.lower() == "false":
            MI.print_error("No report IDs specified")

        log.debug("Report IDs: {}".format(report_ids))

        log.debug("Config: {}".format(MI.config()))

        MI.host(MI.get_config("hostname"))
        MI.source(MI.get_config("name"))

        RESTConfig = {
            "auth":
                {
                    "type": "basic",
                    "username": report_user,
                    "password": report_pwd
                },
            "hostname": MI.get_config("hostname"),
            "verify_certificate": False,
            "output_type": "csv"
        }

        # NLG-22
        proxy_name = MI.get_config("proxy_name")
        if proxy_name is not None and proxy_name != "not_configured" and proxy_name is not "none":
            RESTConfig["proxy"] = utils.get_proxy_configuration(proxy_name)

        RC = LANGuardianAppForSplunkRESTclient(_APP_NAME, RESTConfig)

        # split the report IDs into individual reports and run the reports

        for report_id in report_ids.split(','):

            log.debug("Report ID: {}".format(report_id))
            my_key = '{}:{}'.format(MI.get_config("hostname"), report_id)
            my_sourcetype = "netfort:languardian:{}".format(report_id)
            MI.sourcetype(my_sourcetype)

            log.debug("my_key: {}".format(my_key))
            log.debug("my_sourcetype: {}".format(my_sourcetype))

            MI.checkpoint_default_lookback(600)

            chk = MI._get_checkpoint(my_key)
            if chk is None:
                chk = {}
            MI.log.debug("returned from get_checkpoint TYPE: {0}".format(type(chk)))
            if type(chk) == float or type(chk) == int:
                MI.log.debug("resetting the checkpoint to an object")
                chk = {}
            if "last_time" not in chk:
                MI.log.debug("setting starting time to 0")
                chk["last_time"] = 0

            if "internal_ids" not in chk:
                MI.log.debug("create internal_ids object")
                chk["internal_ids"] = []

            MI.log.debug("Current checkpoint TYPE: {0}".format(type(chk)))

            if int(chk["last_time"]) < 1:
                MI.log.debug("setting starting time to now")
                now = time.time()
                starttime = int(now - int(MI.checkpoint_default_lookback(600)))
            else:
                MI.log.debug("setting starting time to chk last_time")
                starttime = int(chk["last_time"])

            # Because of post processing that happens we need to allow for events to be loaded so set end time to be
            # 5 minutes earlier than the current time

            endtime = int(((datetime.utcnow() - timedelta(minutes=5)) - datetime.utcfromtimestamp(0)).total_seconds())

            log.debug("Start time: %s. End time: %s" % (starttime, endtime))

            data = None

            log.debug("Get Events")

            try:
                data = RC.get_events(rid=report_id, starttime=starttime, endtime=endtime, user=report_user,
                                     password=report_pwd,http_type=report_http_type)

            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                jsondump = {"message": str((e)),
                            "exception_type": "%s" % type(e).__name__,
                            "exception_arguments": "%s" % e,
                            "filename": fname,
                            "line": exc_tb.tb_lineno,
                            "report_id": report_id
                            }
                log.error("{}".format(jsondump))
                MI.print_error(json.dumps(jsondump))

            # Need to make sure that data is actually something
                #            log.debug("The data looks like: %s" % data)

                # Parse the CSV data
                # Checklist fields: instance total_failures message severity_level
            if data is None:
                jsondump = {"message": "Data for report {} is None.".format(report_id),
                            "severity_level": "2",
                            "instance": MI.host(),
                            "action": "no_report_data"}
                MI.print_error(json.dumps(jsondump))
                continue

            if str(report_id) == "1003":
                log.debug("Convert string to UTF-8")
                content_encoding = chardet.detect(data)
                log.debug("Original Encoding: {}".format(content_encoding))

                tmp_data_base64 = base64.b64encode(data)

                new_data_utf_8 = base64.b64decode(tmp_data_base64)
                byte_array = bytearray()
                byte_array.extend(new_data_utf_8)
                log.debug("Byte array Encoding: {}".format(chardet.detect(byte_array)))
#                new_data_utf_8 = byte_array.decode("utf-8")

                table_rows = byte_array.split("\n")
#                table_rows = new_data_utf_8.split("\n")
#                table_rows = tmp_data_base64.split("\n")
#                log.debug("Table rows: {}".format(table_rows))

                # Pop off the last item in the list because it is an empty bytearray
                table_rows.pop()
            else:
                table_rows = data.split("\n")

#            log.debug("Type - table_rows: {}".format(type(table_rows)))
            num_table_rows = len(table_rows) - 1

            if str(report_id) == "1003":
                log.debug("Report ID is 1003, assign reader to table_rows directly")
                reader = table_rows
            else:
                log.debug("Report ID is not 1003, assign reader to csv.DictReader")
                reader = csv.DictReader(table_rows)

            log.debug("Number of reader events for report ID {}: {}".format(str(report_id), str(num_table_rows)))

            if num_table_rows < 0:
                MI.print_error("Error with report execution, check report syntax, Report ID: {}".format(str(report_id)))
            else:
                if str(report_id) == "1003":
                    headers = str(reader.pop(0)).split(",")

                for row in reader:

                    if str(report_id) == "1003":
                        tmp_data_dict = str(row).split(",")
                        row_combined = {}
#                       [row_combined.update({headers[x]:tmp_data_dict[x]}) for x in range(0,len(tmp_data_dict))]
                        row_combined = {headers[x]: tmp_data_dict[x] for x in range(0, len(tmp_data_dict))}
                    else:
                        row_combined = row

                    if "Time" in row_combined:
                        start_date = row_combined["Time"]
                        MI.print_event(json.dumps(row_combined, sort_keys=True, ensure_ascii=False).decode('ISO-8859-2'), time_field="Time")
                    elif "Start" in row_combined:
                        start_date = row_combined["Start"]
                        MI.print_event(json.dumps(row_combined, sort_keys=True, ensure_ascii=False).decode('ISO-8859-2'), time_field="Start")
                    elif "Timestamp" in row_combined:
                        start_date = row_combined["Timestamp"]
                        MI.print_event(json.dumps(row_combined, sort_keys=True, ensure_ascii=False).decode('ISO-8859-2'), time_field="Timestamp")
                    elif "Login Time" in row_combined:
                        start_date = row_combined["Login Time"]
                        MI.print_event(json.dumps(row_combined, sort_keys=True, ensure_ascii=False).decode('ISO-8859-2'), time_field="Login Time")
                    else:
                        MI.print_error(
                            "Missing or Unknown time field in report, ID: {}, verify report format".format(report_id))
                        MI.print_event(json.dumps(row_combined, sort_keys=True, ensure_ascii=False).decode('ISO-8859-2'))

                chk["last_time"] = int(endtime)
                new_checkpoint = endtime

                if new_checkpoint != 0:
                    log.debug("New checkpoint will be %s" % new_checkpoint)
                    MI._set_checkpoint(my_key, object=chk)

                # Output a summary event

                summary_dict = {}

                summary_dict["modular_input_consumption_time"] = new_checkpoint
                summary_dict["timestamp"] = new_checkpoint

                # remove two from length of table_rows to account for header and last line break
                summary_dict["total_events"] = (len(table_rows) - 2)
                #            summary_dict["internal_id_array"] = ids_added
                summary_dict["netfort_event_type"] = report_id

                my_sourcetype = "netfort:languardian:api"
                MI.sourcetype(my_sourcetype)
                MI.print_event(json.dumps(summary_dict))

    except Exception, e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        jsondump = {"message": str((e)),
                    "exception_type": "%s" % type(e).__name__,
                    "exception_arguments": "%s" % e,
                    "filename": fname,
                    "line": exc_tb.tb_lineno,
                    "event_sourcetype": MI.sourcetype(),
                    "event_source": MI.source(),
                    "event_host": MI.host()
                    }
        log.error(re.sub(r'lg_login_password=[^&]+','<PASSWORD_REPLACED>', json.dumps(jsondump)))
        MI.print_error(re.sub(r'lg_login_password=[^&]+','<PASSWORD_REPLACED>', json.dumps(jsondump)))
    MI.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            MI.scheme()
        elif sys.argv[1] == "--validate-arguments":
            MI.validate_arguments()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'You giveth weird arguments'
    else:
        run()

    sys.exit(0)
