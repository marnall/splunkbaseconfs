import logging as log

from ModularInput import *
from RESTClient import *

__author__ = 'ksmith'

_MI_APP_NAME = 'Cyphort For Splunk Modular Input'
_APP_NAME = 'CyphortForSplunk'

_SPLUNK_HOME = os.getenv("SPLUNK_HOME")
if _SPLUNK_HOME is None:
    _SPLUNK_HOME = os.getenv("SPLUNKHOME")
if _SPLUNK_HOME is None:
    _SPLUNK_HOME = "/opt/splunk"


def create_logger_handler(fd, level, max_bytes=10240000, backup_count=5):
    handler = handlers.RotatingFileHandler(fd, maxBytes=max_bytes, backupCount=backup_count)
    handler.setFormatter(log.Formatter('%(asctime)s [%(levelname)s] [%(filename)s] %(message)s'))
    handler.setLevel(level)
    return handler


def get_logger(level=log.INFO):
    logger = log.Logger(_APP_NAME)
    logger.setLevel(level)
    log_location = os.path.join(_SPLUNK_HOME, "var", "log", "splunk", _APP_NAME)
    if not os.path.isdir(log_location):
        os.mkdir(log_location)
    output_file_name = os.path.join(log_location, 'modularinput.log')
    handler = create_logger_handler(output_file_name, level)
    logger.addHandler(handler)
    log.Formatter.converter = time.gmtime
    return logger


log = get_logger(log.INFO)

class CyphortForSplunkModularInput(ModularInput):
    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        Fixes ASA-64
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        interval = val_data["interval"]
        if int(interval) < 300:
            raise Exception("Interval too low. Minimum is 300 seconds.")
        return True


class CyphortForSplunkRESTClient(RESTClient):
    def _build_url(self, endpoint):
        return "https://%s/cyadmin/api.php?op=%s" % (self._hostname, endpoint)

    def _call(self, endpoint, **kwargs):
        payload = self._payload(**kwargs)
        self._log.debug("Payload : {0}".format(payload))
        url = self._build_url(endpoint)
        self._log.debug("URL: {0}".format(url))
        return self._read(url, payload=payload)

    def get_incidents(self, **kwargs):
        return self._call("incidents", **kwargs)

    def get_events(self, **kwargs):
        return self._call("events", **kwargs)

    def get_event_detail(self, **kwargs):
        if "event_id" in kwargs:
            return self._call("event_details", **kwargs)
        else:
            return False


MI = CyphortForSplunkModularInput(_APP_NAME, scheme={
    "title": "Cyphort For Splunk",
    "description": "Cyphort For Splunk. Advanced Threat Detection and Mitigation",
    "args": [
        {"name": "hostname",
         "description": "The host to query for information. A corresponding credential must be stored.",
         "title": "Hostname",
         "required": False
         },
        {"name": "token",
         "description": "The API Token to use with Cyphort",
         "title": "Token"
         }
    ]
})


def run():
    try:
        MI.start()
        MI.set_logger(log)
        RC = CyphortForSplunkRESTClient(_APP_NAME, {
            "auth":
                {"type": "token",
                 "token": MI.get_config("token"),
                 "authorization_string": "%s"
                 },
            "hostname": MI.get_config("hostname"),
            "verify_certificate": False
        })
        # RC._toggle_debug();
        # set the lookback to 180 days. This is in Minutes.
        MI.checkpoint_default_lookback(60 * 24 * 180)
        MI.host(MI.get_config("hostname"))
        import math
        try:
            MI.debug("starting incident calls")
            MI.sourcetype("cyphort:incident")
            chk = MI._get_checkpoint("incidents")
            if chk is None:
                chk = {}
            MI.debug("returned from get_checkpoint TYPE: {0}".format(type(chk)))
            if type(chk) == float or type(chk) == int:
                MI.debug("resetting the checkpoint to an object")
                chk = {}
            if "incidents" not in chk:
                chk["incidents"] = []
            if "last_time" not in chk:
                chk["last_time"] = 0
            chk["incidents_full"] = MI.decompress_ranges(chk["incidents"])
            now = int(math.ceil(time.mktime(datetime.now().timetuple())))
            lookback = now - 86400
            diff = now - lookback
            if chk["last_time"] < 1:
                diff = now
            MI.debug("diff: %s now: %s" % (diff, now))
            events = RC.get_incidents(interval_sec=diff, end_time_sec=now, max_risk_value=1)
            if "error_msg" in events:
                raise Exception("%s" % json.dumps(events))
            MI.debug("events: %s" % len(events))
            MI.debug("setting the time_field to last_activity_time")
            # CYP-62  - Cast x["incident_id"] as an integer, so that it finds it correctly in the Array.
            events_not_found = [x for x in events["incident_array"] if
                                int("{}".format(x["incident_id"])) not in chk["incidents_full"]]
            MI.print_multiple_events(events_not_found,
                                     time_field="last_activity_time")
            events["incident_array"] = [int(x["incident_id"]) for x in events["incident_array"] if
                                        x["incident_id"] not in chk["incidents_full"]]
            combined_ranges = [x for x in itertools.chain(events["incident_array"], chk["incidents_full"])]
            compressed = MI.compress_ranges(combined_ranges)
            MI.info("new_events {0} compressed: {1}".format(events["incident_array"], compressed))
            chk["last_time"] = now
            chk["incidents"] = compressed
            del chk["incidents_full"]
            MI._set_checkpoint("incidents", object=chk)
            MI.sourcetype("cyphort:api")
            MI.print_event(json.dumps(events))
            MI.info("completed Cyphort calls")
        except Exception, e:
            MI.print_error(e)

        MI.stop()
    except Exception, e:
        MI.print_error(e)


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
