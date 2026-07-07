import json
import requests
from config import max_retry
from lumeta_exceptions import ResourceNotFoundError
from lumeta_exceptions import ConnectionTimedOutError
from lumeta_exceptions import NoDataError
from lumeta_exceptions import NoDataFromURL
from itertools import permutations



class DeviceInfo(object):

    source_name = []

    def __init__(self, helper, ew, api_key, url, proxy=None):
        self._helper = helper
        self._ew = ew
        self._api_key = api_key
        self._url = url
        self._proxy = proxy

    def device_stats_info(self, query_name=None, retry_count=0):
        device_stats_url = "{}?fmt=json&queryName={}".format(self._url, query_name)
        self._helper.log_info("Connecting to URL : {}".format(device_stats_url))
        try:
            device_stats = self.connect_to_url(device_stats_url, self._api_key, self._proxy)
            if query_name == "integration_status":
                self.source_name = [data['src'] for data in device_stats]
            for each_stat in device_stats:
                if query_name == "All%20Devices%20-%20All%20Zones_with_ts":
                    try:
                        each_stat['IP_Address'] = each_stat.pop('ip', '')
                        each_stat['MAC_Address'] = each_stat.pop('mac', '')
                        each_stat['Device_Type'] = each_stat.pop('devicetype', '')
                        each_stat['Operating_System'] = each_stat.pop('os', '')
                    except KeyError as error:
                        self._helper.log_info("Key Error found {}".format(error))
                    except Exception as e:
                        self._helper.log_info("Error found {}".format(e))

                stat_data = json.dumps(each_stat)
                event = self._helper.new_event(source=self._helper.get_input_type(), index=self._helper.get_output_index(),
                                               sourcetype=self._helper.get_sourcetype(), data=stat_data)
                self._ew.write_event(event)
            self._helper.log_info("Data ingested for {} ".format(device_stats_url))
        except ResourceNotFoundError as e:
            self._helper.log_info("Error found : {}".format(e))
        except ConnectionTimedOutError as e:
            self._helper.log_info("Error found : {}".format(e))
            while retry_count < max_retry:
                self._helper.log_info("Retrying the call for URL {} for {}".format(self.device_stats_info, retry_count))
                retry_count += 1
                return self.device_stats_info(query_name=query_name, retry_count=retry_count)
        except NoDataError as e:
            self._helper.log_info("Error found : {}".format(e))
        except NoDataFromURL as e:
            self._helper.log_info("Error found : {}".format(e))
        except Exception as e:
            self._helper.log_info("Error found : {}".format(e))

    def device_esi_data(self, query_name=None, retry_count=0):
        for source in self.source_name:
            device_stats_url = "{}?fmt=json&queryName={}".format(self._url, query_name)
            device_stats_url = '%s[{"name":"source","value":"%s","type":"STRING"}]' % (device_stats_url, source)
            self._helper.log_info("Connecting to URL : {}".format(device_stats_url))
            try:
                device_esi_stats = self.connect_to_url(device_stats_url, self._api_key, self._proxy)
                for esi_stat in device_esi_stats:
                    esi_stat.update(source_name=source)
                    stat_data = json.dumps(esi_stat)
                    event = self._helper.new_event(source=self._helper.get_input_type(), index=self._helper.get_output_index(),
                                               sourcetype=self._helper.get_sourcetype(), data=stat_data)
                    self._ew.write_event(event)
                self._helper.log_info("Data ingested for {} ".format(device_stats_url))
            except ResourceNotFoundError as e:
                self._helper.log_info("Error found : {}".format(e))
            except ConnectionTimedOutError as e:
                self._helper.log_info("Error found : {}".format(e))
                while retry_count < max_retry:
                    self._helper.log_info(
                        "Retrying the call for URL {} for {}".format(self.device_stats_info, retry_count))
                    retry_count += 1
                    return self.device_stats_info(query_name=query_name, retry_count=retry_count)
            except NoDataError as e:
                self._helper.log_info("Error found : {}".format(e))
            except NoDataFromURL as e:
                self._helper.log_info("Error found : {}".format(e))
            except Exception as e:
                self._helper.log_info("Error found : {}".format(e))

    def device_comparison_data(self, query_name=None, retry_count=0):
        self._helper.log_info("Into device_comparison_data")
        combinations = permutations(self.source_name, 2)
        for pair in combinations:
            pair_name = '%s_%s' %(pair[0], pair[1])
            device_comp_url = "{}?fmt=json&queryName={}".format(self._url, query_name)
            device_comp_url = '%s[{"name":"source1","value":"%s","type":"STRING"}, {"name":"source2","value":"%s","type":"STRING"}]' % (device_comp_url, pair[0], pair[1])
            self._helper.log_info("Connecting to URL : {}".format(device_comp_url))
            try:
                device_comp_stats = self.connect_to_url(device_comp_url, self._api_key, self._proxy)
                for comp_data in device_comp_stats:
                    comp_data.update(comp_name=pair_name)
                    comp_data_dump = json.dumps(comp_data)
                    event = self._helper.new_event(source=self._helper.get_input_type(), index=self._helper.get_output_index(),
                                           sourcetype=self._helper.get_sourcetype(), data=comp_data_dump)
                    self._ew.write_event(event)
                self._helper.log_info("Data ingested for {} ".format(device_comp_url))
            except ResourceNotFoundError as e:
                self._helper.log_info("Error found : {}".format(e))
            except ConnectionTimedOutError as e:
                self._helper.log_info("Error found : {}".format(e))
                while retry_count < max_retry:
                    self._helper.log_info(
                        "Retrying the call for URL {} for {}".format(self.device_stats_info, retry_count))
                    retry_count += 1
                    return self.device_stats_info(query_name=query_name, retry_count=retry_count)
            except NoDataError as e:
                self._helper.log_info("Error found : {}".format(e))
            except NoDataFromURL as e:
                self._helper.log_info("Error found : {}".format(e))
            except Exception as e:
                self._helper.log_info("Error found : {}".format(e))


    def connect_to_url(self, url, api_key, proxy):

        headers = {
            'Authorization': 'Bearer {}'.format(api_key)
        }

        response = requests.request("GET", url, headers=headers, verify=False, proxies=proxy)
        if response.status_code == 404:
            raise ResourceNotFoundError("Cannot connect to API {}".format(url))
        elif response.status_code == 522:
            raise ConnectionTimedOutError("Connection timed out while getting data for url {}".format(url))
        device_info = json.loads(response.text)
        if isinstance(device_info, dict):
            if device_info['status'] == 'ERROR':
                raise NoDataError("Data from url_device is empty {}".format(url))
            else:
                return device_info
        if len(device_info) == 0:
            raise NoDataFromURL("No Data received from URL {}".format(url))
        return device_info
