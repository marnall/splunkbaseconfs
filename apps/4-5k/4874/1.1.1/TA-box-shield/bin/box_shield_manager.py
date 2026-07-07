import sys
import datetime
import json
import traceback
from box_shield_connect import BoxShieldConnect
from solnlib.modular_input.event_writer import ClassicEventWriter


class BoxShieldManager(object):
    """This Class manage the all activies to manage the stuffs those are needed to call th API via boxsdk.
    Also Transform the events in perticular format to ingest those events to Splunk.
    Also This class contains methods to ingest events into the Splunk

    Attributes:
        bsconnector (obj) : Initialize the BoxShieldConnect class object to use the mathods of it.
        client (None, obj): Initialized as `None` but when the client will be authenticated it will initialized with respective obj
        event_types (list): Contains list which uses to get the perticular type of events later on.
        source_type (None, str): Initialized as `None` but as the perticular type of data processed then source_type will be initialized
        ew (obj): Initializing the ClassicEventWrite object in order to ingest all the events at the time
        input_name (str): Unique data input name

    """

    def __init__(self, helper, event_types):
        self.bsconnector = BoxShieldConnect(helper)
        self.client = None
        self.event_types = event_types
        self.source_type = None
        self.ew = ClassicEventWriter()
        self.helper = helper
        self.input_name = self.helper.get_input_stanza_names()

    def box_shield_start_collection(self):
        """It is a driver function
        Get the client object and Initialize the end_time to store this value in checkpoint later on.
        If any error occures in this function it will stop the executing further.

        """
        self.helper.log_info("Starting the data collection")
        try:
            self.client = self._authentication_manager()
        except Exception:
            self.helper.log_error(
                "Unknown error occurred while authentication {}".format(traceback.format_exc()))
            self.helper.log_error("Data collection is failed for index {} due to the authentication failure".format(self.helper.get_arg('index')))
            sys.exit()
        if self.client:
            self._event_manager()

    def _authentication_manager(self):
        """Get the credentials dict and retrieve client object

        Returns:
            client (obj): Client Object

        """
        oauth = self.bsconnector.get_oauth_obj()
        return self.bsconnector.get_client(oauth)

    def _event_manager(self):
        """Manage all the events and save the checkpoint when the data collection is completed
        """
        self.end_time = ("{}{}".format((datetime.datetime.utcnow(
        )-datetime.timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S"), "-00:00"))
        last_30_days = "{}{}".format((datetime.datetime.utcnow(
        )-datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S"), "-00:00")
        for event_type_key in self.event_types.keys():
            self.source_type = event_type_key
            created_after = self._get_created_after(last_30_days)
            created_before = self.end_time
            try:
                flag = True
                next_stream_position = None
                while flag:
                    flag, stream_position = self._recursive_events_manager(
                        created_after, created_before, event_type_key, next_stream_position)
                    next_stream_position = stream_position
                    if not flag:
                        break
                self.helper.save_check_point("{}:{}".format(
                    self.input_name, self.source_type), self.end_time)
                self.helper.log_info(
                "Data collection is completed for the time {} to {} for sourcetype {} and index {}.".format(created_after, created_before, self.source_type, self.helper.get_arg('index')))
            except Exception:
                self.helper.log_critical(
                "Error occurred during data collection for {} sourcetype and index {} ".format(self.source_type, self.helper.get_arg('index')))

    def _recursive_events_manager(self, created_after, created_before, event_type_key, next_stream_position=None):
        """This function recursively manage the API calls via boxsdk

        Args:
            created_after (str): To get the data after the specified time
            created_before (str): To get the data before the specified time
            event_type_key (str): Basically the sourcetype
            next_stream_position (str): This field used to get data consistently.
                                        It will contains the position of last events call,
                                        we use this field in upcoming API call.

        """
        events = None
        try:
            events, stream_position = self._get_admin_events(
                created_after, created_before, event_type_key, next_stream_position)
        except Exception as e:
            self.helper.log_error(
                "Error occured while retrieving admin events. Refer the troubleshooting section in README file.")
            raise Exception(str(e))
        if events:
            if self.source_type == "box:shield:classification":
                classic_ew_event_obj_list = self._get_classification_events_ew_obj_list(events)
            elif self.source_type == "box:shield:alerts":
                classic_ew_event_obj_list = self._get_alert_events_ew_obj_list(events)
            else:
                classic_ew_event_obj_list = self._get_events_ew_obj_list(events)
            try:
                self.ew.write_events(classic_ew_event_obj_list)
                self.helper.log_info(
                    "Collected events are {} into splunk for {} sourcetype".format(len(classic_ew_event_obj_list), self.source_type))
            except Exception as e:
                self.helper.log_critical("Error in indexing list of events. \nError: {}".format(traceback.format_exc()))
                raise Exception(str(e))
            if len(events['entries']):
                return True, stream_position
            else:
                return False, stream_position


    def _get_admin_events(self, created_after, created_before, event_type_key, next_stream_position):
        """This function get the events and keep the track on stream position
        Args:
            created_after (str): To get the data after the specified time
            created_before (str): To get the data before the specified time
            event_type_key (str): Basically the sourcetype
            next_stream_position (str): This field used to get data consistently.
                                        It will contains the position of last events call,
                                        we use this field in upcoming API call.

        Returns:
            events (obj): Box response event object
            stream_position (str): This field used to get data consistently.
                                    It will contains the position of last events call,
                                    we use this field in upcoming API call.


        """
        try:
            events = self.bsconnector.get_events(
                self.client, created_after, created_before, self.event_types[event_type_key], next_stream_position)
            stream_position = events['next_stream_position']
            return events, stream_position
        except Exception as e:
            raise Exception(str(e))

    def _get_events_ew_obj_list(self, events):
        """Just create the list of event obj for classic event writer without doing any further process

        Args:
            events (dict): contains the events information

        Returns:
            classic_ew_event_obj_list (list):  contains list of classic event writer objects
        """
        classic_ew_event_obj_list = []
        try:
            for event in events['entries']:
                response_data = event.response_object
                if "source" in response_data.keys():
                    response_data['box_source'] = response_data.pop('source')
                # converting each event into classic event writer object. Create list of these events and ingest into the Splunk.
                classic_ew_event_obj = self.ew.create_event(source=self.helper.get_input_type(), index=self.helper.get_output_index(
                ), sourcetype=str(self.source_type), data=json.dumps(response_data))
                classic_ew_event_obj_list.append(classic_ew_event_obj)
        except KeyError:
            self.helper.log_warning("Error occurred while filtering {} events. \nError: {}".format(self.source_type, traceback.format_exc()))
        except AttributeError:
            self.helper.log_warning("Error occurred while filtering {} events. \nError: {}".format(self.source_type, traceback.format_exc()))
        return classic_ew_event_obj_list

    def _get_alert_events_ew_obj_list(self, events):
        """just create the list of event obj for classic event writer with filtering the alert events

        Args:
            events (dict): contains the alert events information

        Returns:
            classic_ew_event_obj_list (list):  contains list of classic event writer objects
        """
        classic_ew_event_obj_list = []

        try:
            for event in events['entries']:
                response_data = event.response_object
                if "source" in response_data.keys():
                    response_data['box_source'] = response_data.pop('source')
                if "link" in (event.additional_details['shield_alert']).keys():
                    response_data['additional_details']['shield_alert']['shield_alert_link'] = response_data['additional_details']['shield_alert'].pop('link')
                if event.ip_address:
                    response_data.pop('ip_address')
                # converting each event into classic event writer object. Create list of these events and ingest into the Splunk.
                classic_ew_event_obj = self.ew.create_event(source=self.helper.get_input_type(), index=self.helper.get_output_index(
                ), sourcetype=str(self.source_type), data=json.dumps(response_data))
                classic_ew_event_obj_list.append(classic_ew_event_obj)
        except KeyError:
            self.helper.log_warning("Error occurred while filtering {} events. \nError: {}".format(self.source_type, traceback.format_exc()))
        except AttributeError:
            self.helper.log_warning("Error occurred while filtering {} events. \nError: {}".format(self.source_type, traceback.format_exc()))
        return classic_ew_event_obj_list

    def _get_classification_events_ew_obj_list(self, events):
        """Look into the additional details field in events and filter the events based the type field

        As shown in below example we'll receive the following dict as part of event, so only those events will be
        ingested which has the start string "securityClassification" in "type" field and other events will be bypass.

        When the event_type is "METADATA_INSTANCE_*****" then the received additional_details in event will be following
        Example 1.
            "additional_details": {
                "metadata": {
                    "type": "securityClassification-****",
                    "operationParams": "[{\"op\":\"*****\",\"path\":\"\\/Box__Security__Classification__Key\",\"value\":\"*******\"}]"
                }
            }

        When the event_type is "METADATA_TEMPLATE_*****" then the received additional_details in event will be following
        Example 2.
            "additional_details": {
                "metadata_template": {
                    "id": "******",
                    "type": "securityClassification-*******",
                    "operationParams": "[[{\"op\":\"*****\",\"data\":{\"displayName\":\"Classification\",\"type\":\"****\",\"id\":****,\"key\":\"Box__Security__Classification__Key\",\"hidden\":****,\"options\":[{\"id\":***,\"key\":\"*****\"}]}}]]",
                    "templateKey": "securityClassification-6VMVochwUWo",
                    "scope": "*****"
                }
            }

        Args:
            events (dict): contains the events information

        Returns:
            classic_ew_event_obj_list (list):  contains list of classic event writer objects
                                               which is filtered by the "type" field
        """
        classic_ew_event_obj_list = []

        try:
            for event in events['entries']:
                if "TEMPLATE" in event.event_type:
                    metadata_field_name = "metadata_template"
                else:
                    metadata_field_name = "metadata"
                response_data = event.response_object
                if (event.additional_details[metadata_field_name]['type']).startswith(('securityClassification')):
                    if "source" in response_data.keys():
                        response_data['box_source'] = response_data.pop('source')
                    if response_data['additional_details'][metadata_field_name]['operationParams']:
                        response_data['operationParams'] = json.loads((response_data['additional_details'][metadata_field_name]).pop('operationParams'))
                    # converting each event into classic event writer object. Create list of these events and ingest into the Splunk.
                    classic_ew_event_obj = self.ew.create_event(source=self.helper.get_input_type(), index=self.helper.get_output_index(
                    ), sourcetype=str(self.source_type), data=json.dumps(response_data))
                    classic_ew_event_obj_list.append(classic_ew_event_obj)
        except KeyError:
            self.helper.log_warning("Error occurred while filtering {} events. \nError: {}".format(self.source_type, traceback.format_exc()))
        except AttributeError:
            self.helper.log_warning("Error occurred while filtering {} events. \nError: {}".format(self.source_type, traceback.format_exc()))
        return classic_ew_event_obj_list

    def _get_created_after(self, last_30_days):
        """Manage and returns created_after field

        Args:
            last_30_days (str): Has UTC date of last 30 days
        Returns:
            created_after (str): To get specific date to start collection

        """
        try:
            created_after = self.helper.get_check_point(
                "{}:{}".format(self.input_name, self.source_type))
        except Exception:
            self.helper.log_error("Error occurred while retrieving start_time from checkpoint. Refer the troubleshooting section in README file. \nError: {}".format(traceback.format_exc()))
            sys.exit()
        if not created_after:
            created_after = "{}{}".format(self.helper.get_arg('start_time'),"-00:00") if self.helper.get_arg('start_time') else last_30_days
        return created_after
