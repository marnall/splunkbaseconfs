import os
import time
import datetime
import json
import traceback

from ecs_connect import ECSConnect
from ecs_util import get_conf_details

from splunk.clilib.bundle_paths import make_splunkhome_path
from solnlib.modular_input.event_writer import ClassicEventWriter


class DellECSCollect(object):
    """Class for handling event collection for dell ecs."""

    def __init__(self, helper, ew, input_type="default"):
        """
        Initialize DellECSCollect object.

        :param helper: AOB's helper object
        :param ew: event writer object
        :param input_type: input type for which events have to be collected
        """
        self.helper = helper
        self.event_writer = ew
        self.input_type = input_type
        # To index independant endpoints responses
        self.stanza_dict, self.stanzas, self.conf_parser = get_conf_details(
            helper)
        # To index dependant endpoints responses
        self.dep_stanza_dict, self.dep_stanzas, self.dep_conf_parser = get_conf_details(
            self.helper, file="dependent_endpoint.conf")
        self.current_time = int(time.time())
        self.PORT = "4443"
        self.GLOBAL_ACCOUNT = helper.get_arg('global_account')
        self.GLOBAL_SERVER_ADDRESS = self.GLOBAL_ACCOUNT["server_address"]
        self.GLOBAL_USERNAME = self.GLOBAL_ACCOUNT["username"]
        self.GLOBAL_PASSWD = self.GLOBAL_ACCOUNT["password"]
        self.INPUT_NAME = self.helper.get_input_stanza_names()
        self.VERIFY_SSL = False if str(self.GLOBAL_ACCOUNT["verify_ssl"]) == "0" else True
        self._verify_input_type()
        self._create_ecs_connect_obj()
        self.ew = ClassicEventWriter()

    def _verify_input_type(self):
        """Verify if given input type valid."""
        if self.input_type not in ["default", "namespace", "bucket"]:
            raise Exception("Invalid input type is provided!")

    def _create_ecs_connect_obj(self):
        """Created ECS connect object."""
        now = datetime.datetime.utcnow()
        self.END_TIME = now.strftime("%Y-%m-%dT%H:%M")

        # get connection object
        self.ecsconnect_obj = ECSConnect(self.GLOBAL_SERVER_ADDRESS, self.PORT,
                                         self.GLOBAL_USERNAME,
                                         self.GLOBAL_PASSWD,
                                         self.END_TIME,
                                         self.helper,
                                         self.VERIFY_SSL)

        # handle token behaviour(set working token)
        self.TOKEN_NAME = "x-sds-auth-token:{}".format(
            self.GLOBAL_SERVER_ADDRESS)
        self.ecsconnect_obj.handle_token(self.helper, self.TOKEN_NAME)

    def handle_flux_endpoint_responses(self, response, source_type):
        """
        Process response of Flux API.

        :param response: rest api response
        :param source_type: source_type in which data is to be ingested
        """
        try:
            for entities in response:  # Iterate over all entities in parent response
                send_data_to_splunk = {}
                index_column_name = {}  # Mapping of which value is at which index
                field_name = entities.get("Columns")  # Get list of all columns
                field_value = entities.get("Values")  # Get list of all values
                if field_name and field_value:
                    for index in range(len(field_name)):
                        # the API can consists of extra field so keep only required fields
                        if source_type in ["dell:flux:disk:read", "dell:flux:disk:write"] and field_name[index] not in ["table"]:  # noqa:E501
                            index_column_name[index] = field_name[index]
                        else:
                            if field_name[index] in ["_time", "_value", "_field", "_start", "_stop", "code", "head"]:
                                index_column_name[index] = field_name[index]
                    if len(index_column_name) != 0:
                        for single_entity in field_value:  # field_value will be list of list hence iterate over it
                            resp_dict = {}
                            # Pick values of all required entities, so iterate over dict
                            for index in index_column_name:
                                resp_dict[index_column_name[index]] = single_entity[index]
                            resp_dict_keys = list(resp_dict.keys())

                            key = resp_dict["_time"]
                            # Don't ingest keys with _ in starting in Splunk
                            resp_dict["time"] = resp_dict.pop('_time')

                            if "_value" and "_field" in resp_dict_keys:
                                resp_dict[resp_dict.get(
                                    '_field')] = resp_dict.get('_value')
                                resp_dict.pop('_field')
                                resp_dict.pop('_value')
                            if "_start" in resp_dict_keys:
                                resp_dict["start"] = resp_dict.pop('_start')
                            if "_stop" in resp_dict_keys:
                                resp_dict["stop"] = resp_dict.pop('_stop')
                            if "head" in resp_dict_keys:
                                resp_dict["value"] = resp_dict.pop('_value')
                                key = "{time}:head:{head}".format(time=key, head=resp_dict["head"])
                            if "code" in resp_dict_keys:
                                resp_dict["value"] = resp_dict.pop('_value')
                                key = "{time}:code:{code}".format(time=key, code=resp_dict["code"])

                            if key in send_data_to_splunk:
                                send_data_to_splunk[key].update(resp_dict)
                            else:
                                send_data_to_splunk[key] = resp_dict

                if len(send_data_to_splunk) > 0:
                    event = self.transform_events(send_data_to_splunk, source_type, endpoint_type="Flux Data")
                    self.collect_events_into_splunk(event, source_type)
        except Exception as e:
            self.helper.log_warning(
                "Flux Endpoint facing json parsing problem in response.")
            raise Exception(e)

    def handle_endpoints_conf_responses(self, response, endpoint, source_type):
        """
        Get the data from responses.

        :param response: rest api response
        :param endpoint: rest api
        """
        try:
            response = json.loads(response.text)
        except Exception as e:
            self.helper.log_warning(
                "Endpoint {} facing json parsing problem in response: Message: {} \nError: {}"
                .format(endpoint, str(e), traceback.format_exc()))

        if endpoint in list(self.stanza_dict.keys()) and source_type is not None:
            if "fields" in self.stanza_dict[endpoint]:
                fields = self.conf_parser.get(endpoint, "fields")
                fields_list = fields.split(",")
                self.handle_list_response(fields_list, response,
                                          source_type)
            else:
                try:
                    event = self.transform_events(response, source_type)
                    self.collect_events_into_splunk(
                        [event], source_type)
                except Exception:
                    self.helper.log_warning(
                        "Skipped data collection for {} source_type \nError: {}".format(
                            source_type, traceback.format_exc()))

    def handle_list_response(self, fields_list, response, source_type):
        """
        Handle the response of api incase of it is list.

        :param fields_list: fields list from conf
        :param response: rest api response
        :param source_type: sourcetype to ingest
        """
        for field in fields_list:
            if isinstance(response[field], list):
                if len(response[str(field)]) > 0:
                    event_list = []
                    for response in response[str(field)]:
                        event = self.transform_events(
                            response, source_type)
                        event_list.append(event)
                    if len(event_list) > 0:
                        self.collect_events_into_splunk(
                            event_list, source_type)
            else:
                event = self.transform_events(
                    response.get(field), source_type)
                self.collect_events_into_splunk([event],
                                                source_type)

    def collect_events_into_splunk(self, response, source_type):
        """
        Index events into splunk.

        :param response: rest api response
        :param source_type: sorcetype to index data
        """
        try:
            self.ew.write_events(response)
        except Exception:
            self.helper.log_critical(
                "Error in indexing list of events. \nError: {}".format(traceback.format_exc()))

    def transform_events(self, response, source_type, endpoint_type=None):
        """
        Adding vdcIP and current time in events.

        :param response: response from the API
        :param source_type: sourcetype of event to ingest
        :return event: return transformed events
        """
        event = None
        if response:
            time_index = None
            try:
                if endpoint_type == "Flux Data":
                    event = []
                    for value in list(response.values()):
                        time_index = None
                        value['vdcIp'] = self.GLOBAL_ACCOUNT["server_address"]
                        if value.get('time'):
                            # taking time of event as a _time
                            time_index = (datetime.datetime.strptime(
                                value['time'], "%Y-%m-%dT%H:%M:%SZ") - datetime.datetime(1970, 1, 1)).total_seconds()
                        event.append(self.ew.create_event(source=self.helper.get_input_type(),
                                                          index=self.helper.get_output_index(),
                                                          sourcetype=str(source_type),
                                                          data=json.dumps(value), time=time_index))
                else:
                    response['vdcIp'] = self.GLOBAL_ACCOUNT["server_address"]
                    if response.get('timestamp'):
                        response['time'] = response.pop('timestamp')
                        # taking time of event as a _time
                        time_index = (datetime.datetime.strptime(
                            response['time'], "%Y-%m-%dT%H:%M:%S") - datetime.datetime(1970, 1, 1)).total_seconds()
                    event = self.ew.create_event(source=self.helper.get_input_type(),
                                                 index=self.helper.get_output_index(),
                                                 sourcetype=str(source_type),
                                                 data=json.dumps(response), time=time_index)
            except TypeError:
                self.helper.log_critical(
                    "ERROR Occured during adding vdcIp \nError: {}".format(traceback.format_exc()))
        return event

    def handle_endpoint_conf_api(self):
        """Implemented api calling mechanism."""
        if len(self.stanzas) == 0:
            raise Exception(
                "No independent stanzas found for data collection!")
        for endpoint in self.stanzas:
            source_type = None
            try:
                source_type = self.conf_parser.get(endpoint, "sourcetype")
            except Exception:
                self.helper.log_critical("Error reading sourcetype {} \nError: {}".format(
                    source_type, traceback.format_exc()))
            if source_type and self.conf_parser.get(endpoint, "type") == self.input_type:
                markervalue = 'NotSet'
                if "checkpoint" in self.stanza_dict.get(endpoint) and "yes" == self.conf_parser.get(
                        endpoint, "checkpoint"):
                    try:
                        self.handle_markers_for_endpoint_conf(
                            endpoint, markervalue, source_type)
                    except Exception as e:
                        self.helper.log_warning(
                            'Error occured while processing marker with endpoint: {} Message: {} \nError: {}'
                            .format(endpoint, str(e), traceback.format_exc()))
                else:
                    self.handle_response_endpoint_conf(endpoint, source_type)

    def handle_checkpoint_dict(self, source_type):
        """
        Handle checkpoint dictionary.

        If no checkpoint is availbale then it will be None otherwise it will contain start_time, end_time, marker_value
        :parma source_type: source type of endpoint
        :return checkpoint_start_time: start time for data collection
        :return checkpoint_end_time: end time for data collection
        :return checkpoint_marker_value: marker for data collection
        """
        checkpoint_dict = self.helper.get_check_point("{}:{}".format(self.INPUT_NAME, source_type))
        temp_checkpoint_dict = {}
        if checkpoint_dict:
            # checkpoint_dict = json.loads(checkpoint_dict)
            temp_checkpoint_dict["marker_value"] = checkpoint_dict.get(
                "marker_value") if checkpoint_dict.get("marker_value") else "NotSet"
            temp_checkpoint_dict["start_time"] = checkpoint_dict.get(
                "end_time") if temp_checkpoint_dict["marker_value"] == "NotSet" else checkpoint_dict.get("start_time")
            temp_checkpoint_dict["end_time"] = self.END_TIME if temp_checkpoint_dict["marker_value"] == "NotSet" else checkpoint_dict.get("end_time")  # noqa:E501
        else:
            temp_checkpoint_dict["start_time"] = self.helper.get_arg('start_time')
            temp_checkpoint_dict["end_time"] = self.END_TIME
            temp_checkpoint_dict["marker_value"] = "NotSet"

            # if the start_time is not given then by default one week data collection will be start
            if temp_checkpoint_dict["start_time"] is None:
                last_seven_days = datetime.datetime.utcnow() - datetime.timedelta(days=7)
                temp_checkpoint_dict["start_time"] = last_seven_days.strftime("%Y-%m-%dT%H:%M")

        return temp_checkpoint_dict

    def handle_markers_for_endpoint_conf(self, endpoint, markervalue, source_type):
        """
        Function will handle marker logic for those endpoints, which are listed in endpoint.conf.

        :param endpoint: rest api endpoint
        :param markervalue: provide the markervalue
        :param source_type: sourcetype of endpoint
        """
        checkpoint_dict = self.handle_checkpoint_dict(
            source_type)
        if markervalue or not markervalue:
            markervalue = checkpoint_dict["marker_value"]
        while markervalue:
            querystring = {
                "limit": "500",
                "start_time": checkpoint_dict["start_time"],
                "end_time": checkpoint_dict["end_time"]
            }
            querystring if str(markervalue) == 'NotSet' else querystring.update(
                {"marker": str(markervalue)})
            response = self.ecsconnect_obj.get_endpoint_response(
                endpoint, querystring)
            if response:
                try:
                    self.handle_endpoints_conf_responses(
                        response, endpoint, source_type)
                except KeyError:
                    self.helper.log_warning(
                        'please checkout field value for endpoint: {} \nError: {}'.format(
                            endpoint, traceback.format_exc()))
                except Exception:
                    pass
                try:
                    json_response = json.loads(response.text)
                    markervalue = json_response.get("NextMarker")
                except Exception:
                    self.helper.log_critical(
                        "Error occured while parsing response in json \nError: {}".format(traceback.format_exc()))
                checkpoint_dict["marker_value"] = markervalue
                if markervalue is None:
                    checkpoint_dict.pop("marker_value")
                self.helper.save_check_point("{}:{}".format(
                    self.INPUT_NAME, source_type), checkpoint_dict)
        if checkpoint_dict.get("marker_value") == "NotSet":
            checkpoint_dict.pop("marker_value")
        self.helper.save_check_point("{}:{}".format(
            self.INPUT_NAME, source_type), checkpoint_dict)

    def handle_response_endpoint_conf(self, endpoint, source_type):
        """Function will handle those endpoints which are listed in endpoint.conf."""
        querystring = {}
        if "dynamic_time" in self.stanza_dict.get(endpoint):
            querystring["startTime"] = int(
                (datetime.datetime.utcnow() - datetime.timedelta(days=1) - datetime.datetime(1970, 1, 1)).total_seconds())  # noqa:E501
            querystring["endTime"] = int(
                (datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds())
            querystring["interval"] = 300
        response = self.ecsconnect_obj.get_endpoint_response(
            endpoint, querystring)
        if response:
            try:
                self.handle_endpoints_conf_responses(
                    response, endpoint, source_type)
            except KeyError:
                self.helper.log_warning(
                    'please checkout field value for endpoint: {} \nError: {}'.format(
                        endpoint, traceback.format_exc()))
            except Exception:
                pass

    def to_persist_data(self, response, endpoint, endpoint_dict_details, source_type):
        """
        Store information of root endpoints.

        :param response: rest api response
        :param endpoint: rest api endpoint
        :param endpoint_dict_details: details endpoint whose data needs to be stored
        (root_endpoint_dict | dependent_endpoint_dict)
        :param source_type: source type of endpoint
        :return data: list of extracted value from api response
        """
        data = []
        flux_hostname = None
        if not source_type:
            return data
        try:
            json_response = json.loads(response.text)
        except Exception:
            self.helper.log_warning(
                "Endpoint {} facing json parsing problem in response \nError: {}".format(
                    endpoint, traceback.format_exc()))

        if "fields" in list(endpoint_dict_details[endpoint].keys()):
            for response_data in json_response[endpoint_dict_details[endpoint]
                                               ["fields"]]:
                if not(endpoint_dict_details[endpoint].get("ingest") and endpoint_dict_details[endpoint]["ingest"] == "false"):  # noqa:E501
                    event = self.transform_events(
                        response_data, source_type)
                    self.collect_events_into_splunk(
                        [event], source_type)
                if "store_data" in list(endpoint_dict_details[endpoint].keys()):
                    data.append(response_data[endpoint_dict_details[endpoint]
                                              ["store_data"]])
                # store value of API response field in dict
                if "flux_node_fields" in list(endpoint_dict_details[endpoint].keys()):
                    for fields in endpoint_dict_details[endpoint]['flux_node_fields']:
                        if response_data[fields] == self.GLOBAL_SERVER_ADDRESS:
                            flux_hostname = response_data["nodename"]
        return data, flux_hostname

    def handle_marker_for_dependent_endpoint(self, dict_value, markervalue,
                                             endpoint, root_endpoint_dict,
                                             build_endpoint):
        """
        Marker logic implementation for dependent_endpoint.conf.

        :param markervalue: markervalue for api
        :praram endpoint: rest api endpoint
        :pararm dict: filterd value to replace in url
        :param root_endpoint_dict: root_endpoint section in dependent.conf
        :param build_endpoint: endpoint url is fully build
        return dict_value: filterd value to replace in url
        """
        if not build_endpoint:
            build_endpoint = endpoint
        source_type = None
        try:
            source_type = (root_endpoint_dict.get(endpoint)).get("sourcetype")
        except AttributeError:
            self.helper.log_critical(
                "Error while reading sourcetype. \nError :{}".format(traceback.format_exc()))
        while markervalue:
            querystring = {
                "limit": "500"
            } if markervalue == 'NotSet' else {
                "limit": "500",
                "marker": markervalue
            }

            response = self.ecsconnect_obj.get_endpoint_response(
                build_endpoint, querystring)
            data, _ = self.to_persist_data(
                response, endpoint, root_endpoint_dict, source_type)
            if dict_value.get(endpoint):
                dict_value[endpoint] = dict_value[endpoint] + data
            else:
                dict_value[endpoint] = data
            try:
                json_response = json.loads(response.text)
                markervalue = json_response.get("NextMarker")
            except Exception:
                self.helper.log_warning(
                    "Endpoint {} facing json parsing problem in response \nError: {}".
                    format(endpoint, traceback.format_exc()))
                break
        return dict_value

    def call_flux_endpoint(self, flux_endpoint, api_query, source_type, checkpoint_key, end_time):
        """
        Fetch data from flux endpoint.

        :praram flux_endpoint: rest api endpoint
        :pararm api_query: payload to be passed in URL
        :param root_endpoint_dict: root_endpoint section in dependent.conf
        :param source_type: source type in which data is to be ingested
        """
        method = "POST"
        payload = json.dumps({"query": api_query})
        try:
            self.helper.log_info(
                'Fetching flux data for Host: {} Endpoint: {} Payload: {}'.format(
                    self.GLOBAL_SERVER_ADDRESS, flux_endpoint, payload))
            api_response = self.ecsconnect_obj.get_endpoint_response(flux_endpoint, payload, method=method)
            if api_response:
                api_response = json.loads(api_response.text)
                if api_response.get("Series") and source_type:
                    try:
                        self.handle_flux_endpoint_responses(api_response.get("Series"), source_type)
                        checkpoint_dict = {"end_time": end_time}
                        self.helper.save_check_point(
                            "{}".format(checkpoint_key), checkpoint_dict)
                        self.helper.log_debug("Updated {} checkpoint with value {}".format(
                            checkpoint_key, checkpoint_dict))
                    except Exception as err:
                        self.helper.log_error(
                            'Error occured while fetching Flux Data for URL: {}'
                            'Payload: {} Error: {} Traceback: {}'.format(
                                flux_endpoint, payload, err, traceback.format_exc()))
        except Exception as err:
            self.helper.log_error(
                'Error occured while fetching Flux Data for URL: {} Payload: {}.'.format(
                    flux_endpoint, payload))
            raise Exception(err)

    def chunk_datetime(self, start, end, last_one_day_data):
        """
        Chunk the start time and end time.

        We will create chunk of the period
        So that if data collection stops abruptly
        We don't have to collect the whole data again.
        Quering data over large timerange (even though it will return
        number of events equels to pagesize) will result in low performance.
        """
        append_5_minutes = int(datetime.timedelta(minutes=5).total_seconds())
        append_time = int(datetime.timedelta(days=1).total_seconds()) if last_one_day_data else int(datetime.timedelta(hours=1).total_seconds())   # noqa:E501

        if last_one_day_data:
            while True:
                new_end = start + append_time
                if (new_end > end):
                    self.helper.log_info("Break for: {} ({}) -> {} ({}) ".format(
                        start, datetime.datetime.fromtimestamp(start), new_end, datetime.datetime.fromtimestamp(new_end)))
                    break
                else:
                    yield start, new_end
                    start = start + 3600

        else:
            while True:
                if (end - start <= 0):
                    self.helper.log_info("Break for: {} ({}) -> {} ({}) ".format(
                        start, datetime.datetime.fromtimestamp(start), end, datetime.datetime.fromtimestamp(end)))
                    break
                else:
                    new_end = start + append_time
                    if new_end > end:
                        new_end = end
                    # if I pass 00:00:00 in API's start_time, then it will return values starting from start + 5 min
                    # Deduct 5min even if it's window of 2m/5m/50m ...
                    yield start - append_5_minutes, new_end
                start = new_end

    def handle_dependent_endpoint_conf_api(self):
        """Get the dict of root endpoints and dependent endpoints."""
        if len(self.dep_stanzas) == 0:
            raise Exception(
                "No dependent stanzas found for data collection!")

        for stanza in self.dep_stanzas:
            if self.dep_conf_parser.get(stanza, "type") == self.input_type:
                dict_value = {}
                flux_hostname = None
                try:
                    root_endpoint_dict = json.loads(
                        self.dep_conf_parser.get(stanza, "root_endpoint"))
                    dependent_endpoint_dict = json.loads(
                        self.dep_conf_parser.get(stanza, "dependent_endpoint"))
                except Exception as e:
                    self.helper.log_critical(
                        "Something wrong with dependent.conf file, Error message : {} \n Error: {}"
                        .format(e, traceback.format_exc()))
                markervalue = 'NotSet'
                for endpoint in list(root_endpoint_dict.keys()):
                    if (root_endpoint_dict.get(endpoint)).get("marker"):
                        filled_dict = self.handle_marker_for_dependent_endpoint(
                            dict_value,
                            markervalue,
                            endpoint,
                            root_endpoint_dict,
                            build_endpoint=None)
                        dict_value = filled_dict
                    else:
                        # Get hostname for Flux API
                        filled_dict, flux_hostname = self.get_dict_dependent_endpoint(
                            endpoint, root_endpoint_dict, dict_value)
                        dict_value = filled_dict
                try:
                    second_dependent_dict = json.loads(
                        self.dep_conf_parser.get(stanza,
                                                 "second_dependent_endpoint"))
                except Exception:
                    self.helper.log_debug(
                        "{} stanza doesnot have second_dependent_dict".format(stanza))
                    second_dependent_dict = None
                self.execute_handled_dependent_endpoint(dependent_endpoint_dict,
                                                        second_dependent_dict,
                                                        dict_value, root_endpoint_dict)
                try:
                    flux_endpoint_dict = json.loads(
                        self.dep_conf_parser.get(stanza, "flux_endpoint"))
                except Exception as e:
                    self.helper.log_debug(
                        "{} stanza doesnot have flux_endpoint_dict: {}".format(stanza, e))
                    self.helper.log_debug(traceback.format_exc())
                    flux_endpoint_dict = {}

                if flux_endpoint_dict and flux_hostname and flux_endpoint_dict["product_version"].split(".")[:2] <= self.GLOBAL_ACCOUNT["product_version"].split(".")[:2]:  # noqa:E501
                    end_time_utc = datetime.datetime.utcnow()

                    if self.helper.get_arg('start_time'):
                        orig_start_time = int((datetime.datetime.strptime(self.helper.get_arg(
                            'start_time'), "%Y-%m-%dT%H:%M") - datetime.datetime(1970, 1, 1)).total_seconds())
                    else:
                        orig_start_time = int((end_time_utc - datetime.timedelta(days=1) - datetime.datetime(1970, 1, 1)).total_seconds())  # noqa:E501
                    flux_endpoint = flux_endpoint_dict["endpoint"]

                    actual_end_time = int((end_time_utc - datetime.datetime(1970, 1, 1)).total_seconds())

                    for dict_key, query_fields in list(flux_endpoint_dict["flux_entities"].items()):
                        source_type = query_fields["sourcetype"]
                        has_metrics = query_fields.get('fields')
                        last_one_day_data = query_fields.get('last_one_day_data')

                        checkpoint_key = "{}:{}:{}".format(
                            self.INPUT_NAME, source_type, dict_key)
                        time_in_checkpoint = self.helper.get_check_point(
                            checkpoint_key)
                        if time_in_checkpoint:
                            checkpoint_time = time_in_checkpoint.get("end_time")
                            # you need to add 3600 only when we fetch from checkpoint else will collect data on time given by user
                            actual_start_time = checkpoint_time + 3600 if last_one_day_data else checkpoint_time
                        else:
                            actual_start_time = orig_start_time

                        last_60_days = int(datetime.timedelta(days=60).total_seconds())
                        if actual_start_time < actual_end_time - last_60_days:
                            actual_start_time = actual_end_time - last_60_days
                            self.helper.log_warning(
                                "Flux: Start date is greater than 60 days. Collecting last 60 days data for Flux.")

                        self.helper.log_info("Fetch flux data between {} ({}) and {} ({}) for sourcetype: {}".format(
                            actual_start_time, datetime.datetime.fromtimestamp(actual_start_time),
                            actual_end_time, datetime.datetime.fromtimestamp(actual_end_time), source_type))

                        for start_time, end_time in self.chunk_datetime(actual_start_time, actual_end_time, last_one_day_data):  # noqa:E501
                            self.helper.log_info("Chunk formed: {} ({}) -> {} ({}) ".format(  # noqa:E501
                                start_time, datetime.datetime.fromtimestamp(start_time), end_time, datetime.datetime.fromtimestamp(end_time)))
                            try:
                                send_in_checkpoint = start_time if last_one_day_data else end_time
                                if has_metrics:
                                    for field in has_metrics:
                                        api_query = query_fields['api_query'].format(
                                            host=flux_hostname, start_time=start_time, end_time=end_time, fields=field) + "|> rename(columns: {" + str(has_metrics[field]) + "}"  # noqa:E501
                                        self.call_flux_endpoint(
                                            flux_endpoint, api_query, source_type, checkpoint_key, send_in_checkpoint)
                                else:
                                    api_query = query_fields['api_query'].format(
                                        host=flux_hostname, start_time=start_time, end_time=end_time)
                                    self.call_flux_endpoint(
                                        flux_endpoint, api_query, source_type, checkpoint_key, send_in_checkpoint)
                            except Exception as err:
                                self.helper.log_error("Error Occurred while handling flux data. Error: {} Traceback: {}".format(  # noqa:E501
                                    err, traceback.format_exc()))

    def execute_handled_dependent_endpoint(self, dependent_endpoint_dict,
                                           second_dependent_dict, dict_value,
                                           root_endpoint_dict):
        """
        Execute the api call with filled value.

        This function will be call recursively in case of second dependent dict is present in stanza
        :param dependent_endpoint_dict: dependent endpoint dict with details
        :pararm dict_value: filterd value to replace in url
        :param root_endpoint_dict: root_endpoint section in dependent.conf
        """
        for endpoint in list(dependent_endpoint_dict.keys()):
            source_type = None
            try:
                source_type = dependent_endpoint_dict[endpoint].get("sourcetype")
            except KeyError:
                self.helper.log_critical("Error while reading sourcetype. \nError :{}".format(traceback.format_exc()))
            if source_type:
                endpoint_list = self.get_dep_main_endpoint(endpoint, dict_value,
                                                           root_endpoint_dict,
                                                           dependent_endpoint_dict)
                for build_endpoint in endpoint_list:
                    response = self.ecsconnect_obj.get_endpoint_response(
                        build_endpoint)
                    try:
                        if second_dependent_dict and dependent_endpoint_dict[
                                endpoint].get("store_data"):
                            self.process_second_dependent_endpoint(
                                response, endpoint, dependent_endpoint_dict,
                                second_dependent_dict, build_endpoint)
                        else:
                            self.handle_dependent_endpoint_fields(
                                response, source_type, dependent_endpoint_dict,
                                endpoint)
                    except Exception:
                        self.helper.log_warning(
                            "Skipped data collection for {} source_type".
                            format(source_type))

    def process_second_dependent_endpoint(self, response, endpoint,
                                          dependent_endpoint_dict,
                                          second_dependent_dict,
                                          build_endpoint):
        """
        Process to resolve second dependency by persisting data from first dependent endpoint.

        :param response: rest api response
        :param endpoint: rest api endpoint
        :param dependent_endpoint_dict: details of endpoints from dependent_endpoint
        :param second_dependent_dict: details of endpoints from second_dependent_endpoint
        :param build_endpoint: fully build endpoint url
        """
        source_endpoint_dict = second_dependent_dict
        second_dependent_dict = None
        dict_value = {}
        markervalue = 'NotSet'
        source_type = None
        try:
            source_type = (dependent_endpoint_dict.get(endpoint)).get("sourcetype")
        except AttributeError:
            self.helper.log_critical("Error while reading sourcetype. \nError :{}".format(traceback.format_exc()))
        if "marker" in dependent_endpoint_dict.get(endpoint):
            dict_value = self.handle_marker_for_dependent_endpoint(
                dict_value, markervalue, endpoint, dependent_endpoint_dict,
                build_endpoint)
        else:
            data, _ = self.to_persist_data(response, endpoint, dependent_endpoint_dict, source_type)
            dict_value[endpoint] = data
        self.execute_handled_dependent_endpoint(source_endpoint_dict,
                                                second_dependent_dict,
                                                dict_value,
                                                dependent_endpoint_dict)

    def handle_dependent_endpoint_fields(self, response, source_type,
                                         dependent_endpoint_dict, endpoint):
        """
        To ingest specific content of events in splunk.

        :param response: rest api response
        :param source_type: sorcetype to index data
        :param dependent_endpoint_dict: dependent endpoint dict details
        :param endpoint : name of endpoint to ingest events
        """
        try:
            json_response = json.loads(response.text)
        except Exception:
            self.helper.log_warning(
                "response from {} endpoint is not parsed".format(endpoint))
            return
        if not(
                dependent_endpoint_dict[endpoint].get("ingest") and dependent_endpoint_dict[endpoint]["ingest"] == "false"):  # noqa:E501
            if "fields" in list(dependent_endpoint_dict[endpoint].keys()):
                if isinstance(json_response[dependent_endpoint_dict[endpoint]["fields"]], list):
                    if len(json_response[dependent_endpoint_dict[endpoint]["fields"]]) > 0:
                        event_list = []
                        for response_data in json_response[dependent_endpoint_dict[endpoint]["fields"]]:
                            event = self.transform_events(
                                response_data, source_type)
                            event_list.append(event)
                        if len(event_list) > 0:
                            self.collect_events_into_splunk(
                                event_list, source_type)
                else:
                    event = self.transform_events(
                        json_response[dependent_endpoint_dict[endpoint]["fields"]], source_type)
                    self.collect_events_into_splunk([event],
                                                    source_type)
            else:
                event = self.transform_events(json_response, source_type)
                self.collect_events_into_splunk(
                    [event], source_type)

    def get_dict_dependent_endpoint(self, endpoint, root_endpoint_dict,
                                    dict_value):
        """
        Provide the dict of filtered value to replace those values with API url.

        :param endpoint: rest api url
        :param root_endpoint_dict: root_endpoint section in dependent.conf
        :pararm dict_value: filterd value to replace in url
        :return dict_value: new values will be append
        """
        response = self.ecsconnect_obj.get_endpoint_response(endpoint)
        source_type = None
        try:
            source_type = (root_endpoint_dict.get(endpoint)).get("sourcetype")
        except AttributeError:
            self.helper.log_critical("Error while reading sourcetype. \nError :{}".format(traceback.format_exc()))
        data, flux_hostname = self.to_persist_data(
            response, endpoint, root_endpoint_dict, source_type)
        dict_value[endpoint] = data
        return dict_value, flux_hostname

    def get_dep_main_endpoint(self, endpoint, dict_value, root_endpoint_dict,
                              dependent_endpoint_dict):
        """
        Dependent endpoint identify and provide those endpoint details.

        :param endpoint: rest api endpoint
        :param dict_value: dict of root endpoint with necessary data to use in dependent endpoint
        :param root_endpoint_dict: details of root endpoints
        :return main_endpoints: main_endpoint with replaced value
        """
        main_endpoints = []
        json_mapping_path = os.path.join(make_splunkhome_path(["etc", "apps", __file__.split(
            os.sep)[-3], "bin", "config_json", "endpointMapping.json"]))
        mapped_json = None
        try:
            with open(json_mapping_path, "r") as fh:
                mapped_json = json.load(fh)
        except Exception:
            self.helper.log_error(
                "Error Occured while reading endpointMapping json. \nError: {}".format(traceback.format_exc()))
            return main_endpoints
        dict_dependency = mapped_json.get('dict_dependency')
        extract_dict = mapped_json.get('extract_dict')

        for key in list(dict_dependency.keys()):
            if key in endpoint and dict_dependency[key] in list(dict_value.keys()):
                data_detail = dict_value[dict_dependency[key]]
                for data in data_detail:
                    replaced_data = str(data.replace(
                        ".", "/")) if (dependent_endpoint_dict.get(endpoint)
                                       ).get('split') else str(data)
                    replaced_endpoint = endpoint.replace(
                        extract_dict.get(key), replaced_data)
                    main_endpoints.append(replaced_endpoint)

        return main_endpoints
