import time
from datetime import datetime
import re
import requests
import json


VULN_SOURCETYPE = "nessus:pro:vuln"
PLUGIN_SOURCETYPE = "nessus:pro:plugin"

PLUGIN_MV_FIELDS = ("bid", "cve", "osvdb", "xref", "msft", "cert")


API_CALL_TIMEOUT = 280



class NessusProAPI:
    def __init__(self, logger, addon_input, account_details, http_scheme="https", verify_ssl=True, proxy_settings=None):
        self.logger = logger
        self.addon_input = addon_input
        self.input_name = addon_input.input_name
        self.input_item = addon_input.input_item
        self.account_details = account_details
        self.proxy_settings = proxy_settings
        self.verify = verify_ssl

        self.base_url = f"{http_scheme}://{account_details.nessus_url}"
        # self._login()
        self.logger.debug("NessusProAPI class initialized.")


    def make_api_call(self, url, method="GET", params=None, data=None):
        headers = {'X-ApiKeys': 'accessKey={0} ; secretKey={1}'.format(self.account_details.client_id, self.account_details.client_secret), 'content-type': 'application/json'}
        full_url = f'{self.base_url.rstrip("/")}/{url.lstrip("/")}'

        self.logger.debug(f"HTTP request to Nessus Professional. URL={full_url}, params={params}")
        # self.logger.debug(f"HTTP request to Nessus Professional. data={data}")

        try:
            response = requests.request(method, full_url, params=params, json=data, headers=headers, proxies=self.proxy_settings, verify=self.verify, timeout=API_CALL_TIMEOUT)
            status_code = response.status_code

            self.logger.info("HTTP response from Nessus Professional. URL={}: status_code={}".format(full_url, status_code))
            # self.logger.debug("HTTP response from Nessus Professional. response_text={}".format(response.text))

            if response.ok:
                try:
                    return response.json()
                except:
                    self.logger.warning("Unable to parse the response text to JSON, returning as text.")
                    return response.text
            else:
                self.logger.error('Error while making the API call to URL={}, status_code={}'.format(full_url, status_code))
                return None

        except Exception as exception:
            self.logger.exception(
                'Error while making the API call to URL={}, error={}'.format(full_url, exception))
            return False


    def _collect_all_scans(self):
        """
        The method to collect the outline info of all the scans.
        """
        response = self.make_api_call("/scans")

        if not response or "scans" not in response:
            err_msg = "No scans found in response of /scans api call."
            self.logger.error(err_msg)
            raise Exception(err_msg)

        if "folders" not in response:
            self.logger.warning("No folders found, ignore adding folder_name attribute to scans.")
        else:
            # Create a dictionary to map folder IDs to folder names
            folder_map = {folder["id"]: folder["name"] for folder in response["folders"]}

            # Add the "folder_name" field to each element in the "scans" list
            for scan in response["scans"]:
                folder_id = scan["folder_id"]
                scan["folder_name"] = folder_map.get(folder_id)

        return response["scans"]


    def _get_last_scan_history_id(self, scan_results_content):
        """
        The method to get the history_id of an scan.
        The history_id is the largest id.
        """

        histories = scan_results_content.get('history', None)
        if not histories:
            return None

        for his in histories[::-1]:
            if his.get("status").lower().strip() in ('running', 'paused'):
                # Ignoring currently running scans
                continue
            else:
                return his
        return None


    def _get_scan_info(self, scan_results_content):
        """
        The method to get the scan_info part in the scan_results_content.
        It removes the 'acls' part and the field with null value which is not needed.
        """
        scan_info = scan_results_content.get("info", {})

        if 'acls' in scan_info:
            del scan_info['acls']
        for k in list(scan_info.keys()):
            if scan_info[k] is None:
                del scan_info[k]
        return scan_info
    

    def _get_host_vuln_details(self, _host_uri, plugin_id):
        _plugin_uri = f"{_host_uri}/plugins/{plugin_id}"
        port_info = []

        ports = []
        plugin_content = self.make_api_call(_plugin_uri)
        if plugin_content is None:
            self.logger.error("There is an exception in request or content key has None value.")
        else:
            plugin_outputs = plugin_content.get("outputs", [])

            if plugin_outputs is None:
                self.logger.error("There is an exception in request or outputs key has None value.") 
            if plugin_outputs:
                for output in plugin_outputs:
                    ports.extend(output.get("ports", {}).keys())
                for port in ports:
                    port_elem = {}
                    port_items = re.split(r"\s*/\s*", port)
                    port_elem["port"] = int(port_items[0])
                    if port_items[1]:
                        port_elem["transport"] = port_items[1]
                    if port_items[2]:
                        port_elem["protocol"] = port_items[2]
                    port_info.append(port_elem)

        return port_info, plugin_content


    def _collect_vulns_for_host(self, ckpt, sid, host_id, scan_info):
        """
        The method to collect all the vulnerabilities of one host and generate the event data.
        """
        count = 0
        _host_uri = f'scans/{sid}/hosts/{host_id}'
        result = self.make_api_call(_host_uri)
        if not result:
            self.logger.error(f"There is error in getting {_host_uri}.")
            return None

        host_info = result.get("info", {})
        host_end_time = host_info.get("host_end", "")
        if ckpt.is_new_host_scan(host_end_time):
            source = f"{self.base_url}/scans/{sid}/hosts/{host_id}"

            # Checking and storing when this vulnerability last detected into the checkpoint for ta_nessus_pro_vuln_status field
            if "vulnerabilities" in ckpt.contents[self.base_url]:
                if f"{host_id}" in ckpt.contents[self.base_url]["vulnerabilities"]:
                    pass
                else:
                    # This host was not seen previously
                    ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"] = {}
            else:
                # Writing vulnerabilities in the checkpoint for the first time
                ckpt.contents[self.base_url]["vulnerabilities"] = {
                    f"{host_id}" : {}
                }

            for vuln in result.get("vulnerabilities", []):
                vuln["sid"] = sid
                vuln["host_id"] = host_id

                # get the port info
                plugin_id = vuln.get("plugin_id", "")
                if plugin_id:

                    # Checking and storing when this vulnerability last detected into the checkpoint for ta_nessus_pro_vuln_status field
                    if f"{plugin_id}" in ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"]:
                        # Vulnerability was detected previously as well
                        ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"][f"{plugin_id}"] = f"{sid}"
                    else:
                        # host is found previously but new vulnerability
                        ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"][f"{plugin_id}"] = f"{sid}"

                    port_info, plugin_content = self._get_host_vuln_details(_host_uri, plugin_id)
                    if port_info:
                        vuln["port"] = port_info
                    # TODO - need to dedug on what's the output of plugin_content and see if anything useful that needs to be ingested
                    if "info" in plugin_content and "plugindescription" in plugin_content["info"]:
                        vuln["plugin"] = plugin_content["info"]["plugindescription"]

                else:
                    self.logger.warning(f"No plugin_id found in : {vuln}")

                vuln["ta_nessus_pro_vuln_status"] = "open"

                vuln["scan"] = scan_info
                vuln = dict(vuln, **host_info)

                self.addon_input.write_event(json.dumps(vuln), timestamp=vuln.get("timestamp"), sourcetype=VULN_SOURCETYPE, source=source)
                ckpt.write()
                count += 1

            # Writing vulnerabilities which are fixed since previous scan
            count += self._collect_fixed_vulns_for_host(ckpt, sid, host_id)

        return count


    def _collect_fixed_vulns_for_host(self, ckpt, current_sid, host_id):
        count = 0

        _fixed_vul_ids = list(ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"].keys())

        for _fixed_vul_id in _fixed_vul_ids:
            _fixed_scan_id = ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"][_fixed_vul_id]

            if _fixed_scan_id == current_sid:
                # Vulnerability found in the last scan, nothing to do
                continue

            _fixed_host_uri = f'scans/{_fixed_scan_id}/hosts/{host_id}'
            _fixed_source = f"{self.base_url}/scans/{_fixed_scan_id}/hosts/{host_id}"

            fixed_scan_results = self.make_api_call(f"scans/{_fixed_scan_id}")
            fixed_scan_info = self._get_scan_info(fixed_scan_results)

            fixed_result = self.make_api_call(_fixed_host_uri)
            if not fixed_result:
                self.logger.error(f"There is error in getting {_fixed_host_uri}.")
                return None

            fixed_host_info = fixed_result.get("info", {})

            for vuln in fixed_result.get("vulnerabilities", []):

                if vuln.get("plugin_id", "") == _fixed_vul_id:
                    # Find until the same plugin_id found from previous scan
                    continue

                vuln["sid"] = _fixed_scan_id
                vuln["host_id"] = host_id

                fixed_port_info, fixed_plugin_content = self._get_host_vuln_details(_fixed_host_uri, _fixed_vul_id)
                if fixed_port_info:
                    vuln["port"] = fixed_port_info
                # TODO - need to dedug on what's the output of plugin_content and see if anything useful that needs to be ingested
                if "info" in fixed_plugin_content and "plugindescription" in fixed_plugin_content["info"]:
                    vuln["plugin"] = fixed_plugin_content["info"]["plugindescription"]

                vuln["ta_nessus_pro_vuln_status"] = "fixed"

                vuln["scan"] = fixed_scan_info
                vuln = dict(vuln, **fixed_host_info)

                self.addon_input.write_event(json.dumps(vuln), timestamp=vuln.get("timestamp"), sourcetype=VULN_SOURCETYPE, source=_fixed_source)
                # TODO - Here the source say previous scan-id, which is incorrect, as the very latest scan-id that is where vulnerability is gone, so that's the scan-id where vulnerability is actually fixed

                # Removing the plugin_id from the checkpoint as the vulnerability is marked as fixed in ta_nessus_pro_vuln_status field
                del ckpt.contents[self.base_url]["vulnerabilities"][f"{host_id}"][f"{_fixed_vul_id}"]
                ckpt.write()
                count += 1
                break

            else:
                # Handling unexpected scenario
                self.logger.warning(f"We expect plugin_id={_fixed_vul_id} to be found in scan_id={_fixed_scan_id} for host_id={host_id} but couldn't find it.")

        return count


    def collect_scan_data(self, ckpt):
        """
        The entrance method to collect scan report data.
        """
        total_no_of_events = 0

        self.logger.info(f"Vuln Input Checkpoint = {ckpt.contents}")
 
        scans = self._collect_all_scans()
        if not scans:
            self.logger.info("There are no scans found.")
            ckpt.contents[self.base_url]["scans"] = dict()
            self.logger.debug(f"Vuln Input Checkpoint (write) (no scans found) = {ckpt.contents}")
            ckpt.write()

        else:
            scan_ids_set = list(set([str(scan.get("id")) for scan in scans]))

            # Remove the sids which does not exist anymore from checkpoint
            keys_to_remove = []
            for sid in ckpt.contents[self.base_url]["scans"].keys():
                if sid not in scan_ids_set:
                    keys_to_remove.append(sid)

            for sid in keys_to_remove:
                del ckpt.contents[self.base_url]["scans"][sid]

            # Getting more details about a scan
            for sid in scan_ids_set:
                scan_results = self.make_api_call(f"scans/{sid}")

                last_his = self._get_last_scan_history_id(scan_results)

                if not last_his:
                    self.logger.info(f"No previous completed scan history found. scan_id={sid}")
                    continue

                scan_info = self._get_scan_info(scan_results)

                hid = last_his.get('history_id')
                if ckpt.is_new_scan(sid, hid):
                    ckpt.contents[self.base_url]["scans"][str(sid)] = dict()
                    ckpt.contents[self.base_url]["scans"][str(sid)]["history_id"] = hid

                    hosts = [_host.get("host_id") for _host in scan_results.get("hosts", [])]
                    # TODO - We can try and implement similar logic to Plugins endpoint to handle scenario
                    # where if input corrupts in between the Input will not collect the host which were previously collected.

                    no_of_events_for_scan = 0
                    for host_id in hosts:
                        no_of_events = self._collect_vulns_for_host(ckpt, sid, host_id, scan_info)
                        no_of_events_for_scan += no_of_events
                        total_no_of_events += no_of_events

                    self.logger.info(f"scan_id={sid} -> Number_of_events={no_of_events_for_scan}")

                    self.logger.debug(f"Vuln Input Checkpoint (write) (one sid ingested) = {ckpt.contents}")
                    ckpt.write()

                else:
                    self.logger.info(f"scan_id={sid} with history_id={hid} is already been explored previously as per the checkpoint value.")

            self.logger.debug(f"Vuln Input Checkpoint (write) (scan found) = {ckpt.contents}")
            ckpt.write()

        ckpt.write()
        self.logger.info(f"Total {total_no_of_events} number of events written.", )


    def _collect_plugin_families(self):
        """
        the method to collect all of the plugin families.
        """
        response = self.make_api_call("/plugins/families")
        plugin_family_id_set = set()
        if response.get("families"):
            for plugin_family in response.get("families"):
                plugin_family_id_set.add(plugin_family.get("id"))
        return plugin_family_id_set


    def _collect_plugin_ids(self, plugin_family_id):
        plugin_set = set()
        response = self.make_api_call(f"/plugins/families/{plugin_family_id}")
        plugins = response.get("plugins", [])
        if not plugins:
            return None
        for plugin in plugins:
            plugin_set.add(plugin.get("id"))

        return list(plugin_set)


    def _collect_plugin_info(self, plugin_id):
        """
        :param plugin_id:
        :return: the detail info of the plugin with id  plugin_id
        """
        result = {}
        response = self.make_api_call(f"/plugins/plugin/{plugin_id}")
        if response.get("id"):
            result["id"] = response.get("id")
        if response.get("family_name"):
            result["family_name"] = response.get("family_name")
        if response.get("attributes"):
            attributes_set = response.get("attributes")
            for attribute in attributes_set:
                attribute_name = attribute.get("attribute_name").replace(
                    '"', "'").lower().strip()
                attribute_value = attribute.get("attribute_value").replace(
                    '"', "'").lower().strip()

                # split "see_also" to mv
                if attribute_name == "see_also":
                    result["see_also"] = re.split(r"[\n\r\s]+",
                                                    attribute_value)
                    continue

                # split "cpe" to mv, and see if has multiple cpe fields originally
                if attribute_name == "cpe":
                    if "cpe" not in result:
                        result["cpe"] = []
                    values = re.split(r"[\n\r\s]+", attribute_value)
                    result["cpe"].extend(values)
                    continue

                if attribute_name in result:
                    if isinstance(result[attribute_name],
                                    list) and attribute_value not in result[
                                        attribute_name]:
                        result[attribute_name].append(attribute_value)
                    elif result[attribute_name] != attribute_value:
                        result[attribute_name] = [result[attribute_name],
                                                    attribute_value]
                elif attribute_name in PLUGIN_MV_FIELDS:
                    result[attribute_name] = [attribute_value]
                else:
                    result[attribute_name] = attribute_value

            return result
        # if there is exception in request, return None
        else:
            self.logger.error("There is exception in request, return None")
            return None


    def collect_plugin_data(self, plugin_ckpt):
        """
        The entrance method to collect plugin data.
        """
        total_event = 0

        self.logger.info(f"plugin_ckpt.contents at start = {plugin_ckpt.contents}")
        if len(plugin_ckpt.contents.get("plugin_ids", [])) == 0:
            plugin_families = self._collect_plugin_families()

            plugin_ids = set()
            for plugin_family_id in plugin_families:
                plugin_id_set = self._collect_plugin_ids(plugin_family_id)
                plugin_ids.update(plugin_id_set)

            if plugin_ids is None:
                self.logger.error("Exception when request plugin_ids")
                return (0, 0)

            plugin_ckpt.contents["plugin_ids"] = list(plugin_ids)
            plugin_ckpt.write()

        while True:
            plugin_id = plugin_ckpt.contents["plugin_ids"][-1]
            plugin_info = self._collect_plugin_info(plugin_id)

            # If plugin_info is None, the plugin_id is not popped
            if plugin_info is not None:
                last_modified_time = plugin_info.get(
                    "plugin_modification_date", plugin_info.get("plugin_publication_date", plugin_ckpt.contents.get("start_date")))

                if plugin_ckpt.is_there_updated_plugin(last_modified_time):
                    self.logger.info(f"This is new plugin. plugin_id={plugin_id}")

                    self.logger.debug(f"plugin_modification_date = {plugin_info.get('plugin_modification_date')}")
                    self.logger.debug(f"plugin_publication_date = {plugin_info.get('plugin_publication_date')}")
                    self.logger.debug(f"plugin_ckpt_start_date = {plugin_ckpt.contents.get('start_date')}")
                    self.logger.debug(f"plugin_ckpt_last_process_time = {plugin_ckpt.contents.get('last_process_time')}")

                    source = f"{self.base_url}/plugins/plugin/{plugin_id}"
                    self.addon_input.write_event(json.dumps(plugin_info), timestamp=time.time(), sourcetype=PLUGIN_SOURCETYPE, source=source)
                    total_event += 1

                plugin_ckpt.contents["plugin_ids"].pop()
                plugin_ckpt.write()

            if len(plugin_ckpt.contents["plugin_ids"]) == 0:
                break

        plugin_ckpt.contents["last_process_time"] = datetime.utcnow().date().strftime("%Y/%m/%d")
        self.logger.info(f"plugin_ckpt.contents at the end = {plugin_ckpt.contents}")
        plugin_ckpt.write()
        self.logger.info(f"Total {total_event} new plugins collected.")
