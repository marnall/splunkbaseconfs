#
# SPDX-FileCopyrightText: 2025 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import base64
import xml.etree.ElementTree as ET
import xml.dom.minidom
import xmltodict
from collections import OrderedDict
from typing import Dict, List, Union, Tuple, Optional
from requests import HTTPError
from palo_utils import make_post_request
from solnlib import log


class FirewallClient:
    """
    A client for interacting with a firewall or panorama API.

    :param host: The host of the firewall.
    :param username: The username for authentication.
    :param password: The password for authentication.
    :param logger: The logger for logging events.
    :param proxy: Optional proxy settings.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        logger,
        proxy=None,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.logger = logger
        self.proxy = proxy

    @property
    def base64_encoded_credentials(self) -> str:
        """
        Returns the base64 encoded credentials.

        :returns: The base64 encoded credentials.
        """
        return base64.b64encode(
            bytes(f"{self.username}:{self.password}", "utf-8")
        ).decode("utf-8")

    @property
    def create_uidmessage(self) -> Tuple[ET.Element, ET.Element]:
        """
        Returns the root and payload elements for the UID message.

        :returns: The root and payload elements for the UID message.
        """
        root = ET.fromstring(
            "<uid-message>"
            + "<version>1.0</version>"
            + "<type>update</type>"
            + "<payload/>"
            + "</uid-message>"
        )
        payload = root.find("payload")
        return root, payload

    @property
    def headers(self) -> Dict[str, str]:
        """
        Returns the headers for the API request.

        :returns: The headers for the API request.
        """
        return {"Content-Type": "application/x-www-form-urlencoded"}

    @property
    def get_api_key(self) -> str:
        """
        Creates firewall API key.

        :returns: The firewall API key.
        """
        headers = self.headers
        payload = {"user": self.username, "password": self.password}
        response_api_key = make_post_request(
            f"https://{self.host}/api/?type=keygen",
            data=payload,
            headers=headers,
            proxies=self.proxy,
        )
        if not response_api_key.ok:
            raise HTTPError(
                "Failed to retrive API key. "
                "Invalid Firewall/Panorama information provided or if connection requires proxy, "
                "please make sure that Configuration => Proxy settings are correct",
            )
        try:
            parsed_response = xmltodict.parse(response_api_key.text)
            api_key = parsed_response["response"]["result"]["key"]
        except (KeyError, TypeError) as e:
            raise HTTPError(f"Failed to parse API key from response. Error: {e}")
        return api_key

    def _send_tags_to_firewall(self, xml_str: str) -> None:
        """
        Sends the tags to the firewall API.

        :param xml_str: The XML string containing the tags.
        """
        params = {"type": "user-id", "key": self.get_api_key}

        headers = self.headers
        response = make_post_request(
            f"https://{self.host}/api",
            data={"cmd": xml_str},
            headers=headers,
            params=params,
            proxies=self.proxy,
        )
        self.logger.info(
            f"Response received from Firewall: {response.text, response.status_code}"
        )
        root = ET.fromstring(response.text)
        status = root.attrib.get("status")
        if status != "success":
            raise HTTPError(
                f"Failed to send tags to firewall. Response: {response.text}"
            )

    def _validate_credentials(self) -> bool:
        """
        Validates the credentials by making a request to the firewall API.

        :returns: True if the credentials are valid, False otherwise.
        """
        response_authinticate = make_post_request(
            f"https://{self.host}/api?type=op&cmd=<show><system><info></info></system></show>",
            headers={"Authorization": f"Basic {self.base64_encoded_credentials}"},
            proxies=self.proxy,
        )
        if response_authinticate.ok:
            return True
        return False

    def get_predefined_threats_or_applications(
        self, request_type: str
    ) -> List[Dict[str, str]]:
        """
        Fetches predefined threats or applications from the firewall API.

        :param request_type: The type of request ('threats' or 'apps').

        :returns: The parsed data in CSV format.
        """
        try:
            response_xml = make_post_request(
                f"https://{self.host}/api?type=config&action=get&xpath=/config/predefined/{'application' if request_type == 'apps' else 'threats'}",
                headers={"Authorization": f"Basic {self.base64_encoded_credentials}"},
                proxies=self.proxy,
            )
            if not response_xml.ok:
                raise HTTPError(
                    f"Failed to get predefined {request_type}. Status code: {response_xml.status_code}"
                )
            csv_parsed_data = (
                self.parse_applications(response_xml.text)
                if request_type == "apps"
                else self.parse_threats(response_xml.text)
            )
            if not csv_parsed_data:
                raise ValueError("Failed to parse data")
            return csv_parsed_data
        except HTTPError as e:
            log.log_exception(
                self.logger,
                e,
                "Custom search command (pancontentpack) error",
                msg_before=f"Failed to get predifined threats or applications. Error: {e}",
            )
        except ValueError as e:
            log.log_exception(
                self.logger,
                e,
                "Custom search command (pancontentpack) error",
                msg_before=f"Error: {e}",
            )

    def parse_threats(self, xml_data: str) -> Union[List[Dict[str, str]], None]:
        """
        Parses the threats data from the XML response.

        :param xml_data: The XML data containing threats information.

        :returns: A list of dictionaries containing parsed threats data.
        """
        obj = xmltodict.parse(xml_data)
        try:
            threats = []
            phone_home = obj["response"]["result"]["threats"].get("phone-home")
            vulnerability = obj["response"]["result"]["threats"].get("vulnerability")
            if phone_home and "entry" in phone_home:
                phone_home_entries = phone_home["entry"]
                if isinstance(phone_home_entries, dict):
                    phone_home_entries = [phone_home_entries]
                threats.extend(phone_home_entries)
            if vulnerability and "entry" in vulnerability:
                vulnerability_entries = vulnerability["entry"]
                if isinstance(vulnerability_entries, dict):
                    vulnerability_entries = [vulnerability_entries]
                threats.extend(vulnerability_entries)
        except KeyError as e:
            log.log_exception(
                self.logger,
                e,
                "Custom search command (pancontentpack) error",
                msg_before=f"Invalid response. Error: {e}",
            )
            return
        csv_threats = []
        for threat in threats:
            threats_dict = OrderedDict()
            try:
                threats_dict["threat_id"] = threat["@name"]
                threats_dict["threat:name"] = threat["threatname"]
                threats_dict["threat:category"] = threat.get("category", None)
                threats_dict["threat:severity"] = threat.get("severity", None)
                threats_dict["threat:cve"] = threat.get("cve", None)
                if threats_dict["threat:cve"] is not None:
                    threats_dict["threat:cve"] = threat["cve"]["member"]
                    if not isinstance(threats_dict["threat:cve"], str):
                        threats_dict["threat:cve"] = ", ".join(
                            threats_dict["threat:cve"]
                        )
                else:
                    threats_dict["threat:cve"] = ""
            except KeyError as e:
                log.log_exception(
                    self.logger,
                    e,
                    "Custom search command (pancontentpack) error",
                    msg_before=f"Key is missing in response. Error: {e}",
                )
                return
            threats_dict = {key: str(value) for key, value in threats_dict.items()}
            csv_threats.append(threats_dict)
        return csv_threats

    def parse_applications(self, xml_data: str) -> Union[List[Dict[str, str]], None]:
        """
        Parses the applications data from the XML response.

        :param xml_data: The XML data containing applications information.

        :returns: A list of dictionaries containing parsed applications data.
        """
        self.logger.info("Begin Parsing Apps")
        obj = xmltodict.parse(xml_data)
        try:
            apps = obj["response"]["result"]["application"]["entry"]
            if isinstance(apps, dict):
                apps = [apps]
        except KeyError as e:
            log.log_exception(
                self.logger,
                e,
                "Custom search command (pancontentpack) error",
                msg_before=f"Invalid response. Error: {e}",
            )
            return
        csv_apps = []
        for app in apps:
            apps_dict = OrderedDict()
            try:
                apps_dict["app"] = app["@name"]
                apps_dict["app:category"] = app.get("category", "")
                apps_dict["app:subcategory"] = app.get("subcategory", "")
                apps_dict["app:technology"] = app.get("technology", "")
                apps_dict["app:risk"] = app["risk"]
                apps_dict["app:evasive"] = app["evasive-behavior"]
                apps_dict["app:excessive_bandwidth"] = app["consume-big-bandwidth"]
                apps_dict["app:used_by_malware"] = app["used-by-malware"]
                apps_dict["app:able_to_transfer_file"] = app["able-to-transfer-file"]
                apps_dict["app:has_known_vulnerability"] = app[
                    "has-known-vulnerability"
                ]
                apps_dict["app:tunnels_other_application"] = app[
                    "tunnel-other-application"
                ]
                if (
                    apps_dict["app:tunnels_other_application"] != "yes"
                    and apps_dict["app:tunnels_other_application"] != "no"
                ):
                    apps_dict["app:tunnels_other_application"] = apps_dict[
                        "app:tunnels_other_application"
                    ]["#text"]
                apps_dict["app:prone_to_misuse"] = app["prone-to-misuse"]
                apps_dict["app:pervasive_use"] = app["pervasive-use"]
                apps_dict["app:is_saas"] = app.get("is-saas", "no")
                apps_dict["app:default_ports"] = ""
                try:
                    # Sometimes there are more than one default tag
                    # so make it a list and iterate over the default tags.
                    default = app["default"]
                    if isinstance(default, list):
                        for item in default:
                            apps_dict["app:default_ports"] = item["port"]["member"]
                            break
                    else:
                        apps_dict["app:default_ports"] = default["port"]["member"]
                except KeyError:
                    pass
                else:
                    if not isinstance(apps_dict["app:default_ports"], str):
                        apps_dict["app:default_ports"] = "|".join(
                            apps_dict["app:default_ports"]
                        )
            except Exception as e:
                log.log_exception(
                    self.logger,
                    e,
                    "Custom search command (pancontentpack) error",
                    msg_before=f"Key is missing in response. Error: {e}",
                )
                return
            apps_dict = {key: str(value) for key, value in apps_dict.items()}
            csv_apps.append(apps_dict)
        self.logger.info(f"Parsed total {len(csv_apps)} apps")
        return csv_apps

    def tag_user(
        self, users: List[str], tags: List[str], timeout: Optional[str] = None
    ):
        """
        Tags the user with the specified tags.

        :param users: The users to tag.
        :param tags: The list of tags to apply.
        :param timeout: (Optional) The timeout in seconds for the given tags
        """
        self.logger.info(f"Users to tag: {users}")
        if timeout is not None:
            timeout = int(timeout)

        root, payload = self.create_uidmessage

        # Find or create the register-user section
        register_user_section = payload.find("./register-user")
        if register_user_section is None:
            register_user_section = ET.SubElement(payload, "register-user")

        props = {}
        if timeout is not None:
            props["timeout"] = f"{timeout}"

        # Add tags for each user
        for user in users:
            # Find the entry for this user, if it exists
            entries = register_user_section.findall("./entry")
            for entry in entries:
                if entry.attrib.get("user") == user:
                    tag_element = entry.find("tag")
                    if tag_element is None:
                        tag_element = ET.SubElement(entry, "tag")
                    break
            else:
                # Entry not found, create a new one
                entry = ET.SubElement(register_user_section, "entry", {"user": user})
                tag_element = ET.SubElement(entry, "tag")

            # Add tags
            for tag in tags:
                ET.SubElement(tag_element, "member", props).text = tag

        # Send the constructed XML to the firewall
        str_formatted_request = ET.tostring(root, encoding="unicode")
        self._send_tags_to_firewall(str_formatted_request)

    def tag_ip(
        self, ips: List[str], tags: List[str], timeout: Optional[str] = None
    ) -> None:
        """
        Register an ip tag for a Dynamic Address Group

        :param ips: List of ips tags to be applied to.
        :param tags: String with tags to be applied to the ips.
        :param timeout: (Optional) Timeout in seconds for the tags.
        """
        self.logger.info(f"IP addresses to tag: {ips}")
        root, payload = self.create_uidmessage
        register_element = payload.find("register")
        if register_element is None:
            register_element = ET.SubElement(payload, "register")

        unique_tags = list(set(tags))
        if not unique_tags:
            return

        props = {}
        if timeout is not None:
            props["timeout"] = str(timeout)

        for current_ip in ips:
            tag_element = register_element.find(f"./entry[@ip='{current_ip}']/tag")
            if tag_element is None:
                entry = ET.SubElement(register_element, "entry", {"ip": current_ip})
                tag_element = ET.SubElement(entry, "tag")
            for tag in unique_tags:
                ET.SubElement(tag_element, "member", props).text = tag
        str_formatted_request = ET.tostring(root, encoding="unicode")
        self._send_tags_to_firewall(str_formatted_request)

    def untag_user(self, users: List[str], tags: List[str]):
        """
        Removes tags associated with a users.

        :param users: The users from whom tags should be removed.
        :param tags: The tags to remove.
        """
        self.logger.info(f"Users to untag: {users}")
        root, payload = self.create_uidmessage

        # Find or create the unregister-user section
        unregister_user_section = payload.find("./unregister-user")
        if unregister_user_section is None:
            unregister_user_section = ET.SubElement(payload, "unregister-user")

        unique_tags = list(set(tags))

        # Remove tags for each user
        for user in users:
            # Find the entry for this user, if it exists
            entries = unregister_user_section.findall("./entry")
            for entry in entries:
                if entry.attrib.get("user") == user:
                    break
            else:
                # Entry not found, create a new one
                entry = ET.SubElement(unregister_user_section, "entry", {"user": user})

            # Find or create the tag section for this user
            tag_element = entry.find("tag")
            if tag_element is None:
                tag_element = ET.SubElement(entry, "tag")

            # Add members to remove
            for tag in unique_tags:
                ET.SubElement(tag_element, "member").text = tag

        # Send the constructed XML to the firewall
        str_formatted_request = ET.tostring(root, encoding="unicode")
        self._send_tags_to_firewall(str_formatted_request)

    def untag_ip(self, ips: List[str], tags: List[str]) -> None:
        """
        Unregister an ip tag for a Dynamic Address Group

        :param ips: List of ips tags to be applied to.
        :param tags: String with tags to be applied to the ips.
        """
        self.logger.info(f"IP addresses to untag: {ips}")
        root, payload = self.create_uidmessage
        unregister_element = payload.find("unregister")
        if unregister_element is None:
            unregister_element = ET.SubElement(payload, "unregister")

        unique_tags = list(set(tags))
        for current_ip in ips:
            tag_element = unregister_element.find(f"./entry[@ip='{current_ip}']/tag")
            if tag_element is None:
                entry = ET.SubElement(unregister_element, "entry", {"ip": current_ip})
                tag_element = ET.SubElement(entry, "tag")
            for tag in unique_tags:
                member = ET.SubElement(tag_element, "member")
                member.text = tag

        str_formatted_request = ET.tostring(root, encoding="unicode")
        self._send_tags_to_firewall(str_formatted_request)
