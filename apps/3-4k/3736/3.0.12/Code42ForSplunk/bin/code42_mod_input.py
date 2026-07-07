import json

from ModularInput import ModularInput
from py42.sdk.util.queued_logger import QueuedLogger


class Code42ForSplunkModularInput(object, ModularInput):
    def __init__(self, modular_input_logger, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self._event_logger = QueuedLogger()
        self.log = modular_input_logger

    def stop(self):
        """Stop the input, waiting first for all log items in the queue to be processed"""
        self._event_logger.wait()
        self.log.debug("Completed printing all modular input events in the queue")
        super(Code42ForSplunkModularInput, self).stop()

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        allowed_endpoints = "computer,org,user,security,alertlog,restore,diagnostic"
        for evt_type in val_data["data_keys"].split(","):
            if evt_type not in allowed_endpoints:
                raise Exception("Data Key: {} is invalid. Valid values are {}".format(evt_type, allowed_endpoints))
        # TODO: Implement for other config options.
        self.log.info("action=validation_settings data={}".format(json.dumps(val_data)))
        if "interval" in val_data:
            if int(val_data["interval"]) < 7200:
                raise Exception("Interval is not at least 7200 seconds")
        return True

    def print_multiple_events_of_sourcetype(self, sourcetype, events, time_field="timestamp"):
        self.log.debug("Printing events. type={0}, count={1}".format(sourcetype, len(events)))
        message = "".join(self.get_event_xml_string_for_event_of_sourcetype(sourcetype,
                                                                            json.dumps(evt)+"\n",
                                                                            time_field=time_field) for evt in events)
        self._event_logger.log(0, message)

    def get_event_xml_string_for_event_of_sourcetype(self, sourcetype, event_data, time_field="timestamp"):
        if len(event_data) < 1:
            event_data = ""
        _isJson = False
        try:
            event_data = json.loads(event_data)
            self.log.debug("successful parse of JSON data: Is Dict: %s" % isinstance(event_data, dict))
            _isJson = True
        except ValueError:
            pass
        if isinstance(event_data, dict) or _isJson:
            if time_field not in event_data and "timestamp" not in event_data:
                event_data["timestamp"] = self.gen_date_string()
                self.log.debug("setting timestamp to generated time: %s" % event_data["timestamp"])
            elif time_field in event_data and "timestamp" not in event_data:
                event_data["timestamp"] = event_data[time_field]
                self.log.debug("setting timestamp to time_field %s time: %s" % (event_data[time_field],
                                                                                event_data["timestamp"]))
            else:
                self.log.debug("unknown condition: time_field %s " % event_data[time_field])
            event_data["modular_input_consumption_time"] = self.gen_date_string()
            event_data = json.dumps(event_data)
        explicit_time_tag = ""
        event_xml = "<event>%s<data><![CDATA[%s]]></data><sourcetype>%s</sourcetype><source>%s</source>" \
                    "<host>%s</host><done /></event>\n" \
                    % (explicit_time_tag, self._escape(event_data), self._escape(sourcetype),
                       self._escape(self.source()), self._escape(self.host()))
        return event_xml
