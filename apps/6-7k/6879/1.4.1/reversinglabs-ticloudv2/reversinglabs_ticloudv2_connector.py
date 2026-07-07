# File: reversinglabs_ticloudv2_connector.py
#
# Copyright (c) ReversingLabs, 2024-2025
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.
#
# Python 3 Compatibility imports

import json
import os
import re
from urllib.parse import urlparse

# Phantom App imports
import phantom.app as phantom
import requests
from phantom import vault
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector
from phantom.vault import Vault
from ReversingLabs.SDK.ticloud import (
    AdvancedSearch,
    AnalyzeURL,
    AVScanners,
    CustomerUsage,
    DomainThreatIntelligence,
    DynamicAnalysis,
    FileAnalysis,
    FileDownload,
    FileReputation,
    FileReputationUserOverride,
    ImpHashSimilarity,
    IPThreatIntelligence,
    NetworkReputation,
    NetworkReputationUserOverride,
    ReanalyzeFile,
    RHA1FunctionalSimilarity,
    URIIndex,
    URIStatistics,
    URLThreatIntelligence,
    YARAHunting,
    YARARetroHunting,
)


# Our helper lib reversinglabs-sdk-py3 internally utilizes pypi requests (with named parameters) which is shadowed by Phantom
# requests (which has renamed parameters (url>>uri), hence this workarounds
old_get = phantom.requests.get


def new_get(url, **kwargs):
    return old_get(url, **kwargs)


phantom.requests.get = new_get
old_post = phantom.requests.post


def new_post(url, **kwargs):
    return old_post(url, **kwargs)


phantom.requests.post = new_post
old_delete = phantom.requests.delete


def new_delete(url, **kwargs):
    return old_delete(url, **kwargs)


phantom.requests.delete = new_delete


class ReversinglabsTitaniumCloudV2Connector(BaseConnector):
    ticloud_spex_url = "/api/spex/upload/"
    USER_AGENT = "ReversingLabs Splunk SOAR TitaniumCloudv2 v1.4.0"

    # The actions supported by this connector
    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"
    ACTION_ID_FILE_REPUTATION = "file_reputation"
    ACTION_ID_ADVANCED_SEARCH = "advanced_search"
    ACTION_ID_URI_STATISTICS = "uri_statistics"
    ACTION_ID_AV_SCANNERS = "av_scanners"
    ACTION_ID_FILE_ANALYSIS = "file_analysis"
    ACTION_ID_FUNCTIONAL_SIMILARITY = "functional_similarity"
    ACTION_ID_URL_THREAT_INTELLIGENCE = "url_reputation"
    ACTION_ID_ANALYZE_URL = "analyze_url"
    ACTION_ID_URI_INDEX = "uri_index"
    ACTION_ID_SUBMIT_FOR_DYNAMIC_ANALYSIS = "submit_for_dynamic_analysis"
    ACTION_ID_SUBMIT_URL_FOR_DYNAMIC_ANALYSIS = "submit_url_for_dynamic_analysis"
    ACTION_ID_DYNAMIC_ANALYSIS_RESULTS = "get_report"
    ACTION_ID_DYNAMIC_URL_ANALYSIS_RESULTS = "get_url_report"
    ACTION_ID_REANALYZE_FILE = "reanalyze_file"
    ACTION_ID_FILE_UPLOAD = "upload_file"
    ACTION_ID_FILE_DOWNLOAD = "get_file"
    ACTION_ID_IMPHASH_SIMILARITY = "imphash_similarity"
    ACTION_ID_YARA_CREATE_RULESET = "yara_create_ruleset"
    ACTION_ID_YARA_DELETE_RULESET = "yara_delete_ruleset"
    ACTION_ID_YARA_GET_RULESET_INFO = "yara_get_ruleset_info"
    ACTION_ID_YARA_GET_RULESET_TEXT = "yara_get_ruleset_text"
    ACTION_ID_GET_YARA_MATCHES = "get_yara_matches"
    ACTION_ID_YARA_RETRO_ENABLE_HUNT = "yara_retro_enable_hunt"
    ACTION_ID_YARA_RETRO_START_HUNT = "yara_retro_start_hunt"
    ACTION_ID_YARA_RETRO_CHECK_STATUS = "yara_retro_check_status"
    ACTION_ID_YARA_RETRO_CANCEL_HUNT = "yara_retro_cancel_hunt"
    ACTION_ID_GET_YARA_RETRO_MATCHES = "get_yara_retro_matches"
    ACTION_ID_GET_URL_DOWNLOADED_FILES = "get_url_downloaded_files"
    ACTION_ID_GET_LATEST_URL_ANALYSIS_FEED = "get_latest_url_analysis_feed"
    ACTION_ID_GET_URL_ANALYSIS_FEED_FROM_DATE = "get_url_analysis_feed_from_date"
    ACTION_ID_GET_NETWORK_REPUTATION = "get_network_reputation"
    ACTION_ID_GET_LIST_USER_OVERRIDES = "get_list_user_overrides"
    ACTION_ID_GET_LIST_USER_OVERRIDES_AGGREGATED = "get_list_user_overrides_aggregated"
    ACTION_ID_NETWORK_REPUTATION_USER_OVERRIDE = "network_reputation_user_override"
    ACTION_ID_FILE_REPUTATION_USER_OVERRIDE = "file_reputation_user_override"
    ACTION_ID_LIST_ACTIVE_FILE_REPUTATION_USER_OVERRIDE = "list_active_file_reputation_user_overrides"
    ACTION_ID_CUSTOMER_DAILY_USAGE = "customer_daily_usage"
    ACTION_ID_CUSTOMER_MONTHLY_USAGE = "customer_monthly_usage"
    ACTION_ID_CUSTOMER_MONTHRANGE_USAGE = "customer_monthrange_usage"
    ACTION_ID_CUSTOMER_DAYRANGE_USAGE = "customer_dayrange_usage"
    ACTION_ID_CUSTOMER_YARA_API_USAGE = "customer_yara_api_usage"
    ACTION_ID_CUSTOMER_QUOTA_LIMITS = "customer_quota_limits"
    ACTION_ID_GET_DOMAIN_REPORT = "get_domain_report"
    ACTION_ID_GET_DOMAIN_DOWNLOADED_FILES = "get_domain_downloaded_files"
    ACTION_ID_GET_URLS_FROM_DOMAIN = "get_urls_from_domain"
    ACTION_ID_GET_RESOLUTIONS_FROM_DOMAIN = "get_resolutions_from_domain"
    ACTION_ID_GET_RELATED_DOMAINS = "get_related_domains"
    ACTION_ID_GET_IP_REPORT = "get_ip_report"
    ACTION_ID_GET_IP_DOWNLOADED_FILES = "get_ip_downloaded_files"
    ACTION_ID_GET_URLS_FROM_IP = "get_urls_from_ip"
    ACTION_ID_GET_RESOLUTIONS_FROM_IP = "get_resolutions_from_ip"

    def __init__(self):
        # Call the BaseConnectors init first
        super().__init__()

        self.ACTIONS = {
            self.ACTION_ID_TEST_CONNECTIVITY: self._handle_test_connectivity,
            self.ACTION_ID_FILE_REPUTATION: self._handle_file_reputation,
            self.ACTION_ID_ADVANCED_SEARCH: self._handle_advanced_search,
            self.ACTION_ID_URI_STATISTICS: self._handle_uri_statistics,
            self.ACTION_ID_AV_SCANNERS: self._handle_av_scanners,
            self.ACTION_ID_FILE_ANALYSIS: self._handle_file_analysis,
            self.ACTION_ID_FUNCTIONAL_SIMILARITY: self._handle_functional_similarity,
            self.ACTION_ID_URL_THREAT_INTELLIGENCE: self._handle_url_reputation,
            self.ACTION_ID_ANALYZE_URL: self._handle_analyze_url,
            self.ACTION_ID_URI_INDEX: self._handle_uri_index,
            self.ACTION_ID_SUBMIT_FOR_DYNAMIC_ANALYSIS: self._handle_submit_for_dynamic_analysis,
            self.ACTION_ID_SUBMIT_URL_FOR_DYNAMIC_ANALYSIS: self._handle_submit_url_for_dynamic_analysis,
            self.ACTION_ID_DYNAMIC_ANALYSIS_RESULTS: self._handle_get_report,
            self.ACTION_ID_DYNAMIC_URL_ANALYSIS_RESULTS: self._handle_get_url_report,
            self.ACTION_ID_REANALYZE_FILE: self._handle_reanalyze_file,
            self.ACTION_ID_FILE_UPLOAD: self._handle_upload_file,
            self.ACTION_ID_FILE_DOWNLOAD: self._handle_get_file,
            self.ACTION_ID_IMPHASH_SIMILARITY: self._handle_imphash_similarity,
            self.ACTION_ID_YARA_CREATE_RULESET: self._handle_yara_create_ruleset,
            self.ACTION_ID_YARA_DELETE_RULESET: self._handle_yara_delete_ruleset,
            self.ACTION_ID_YARA_GET_RULESET_INFO: self._handle_yara_get_ruleset_info,
            self.ACTION_ID_YARA_GET_RULESET_TEXT: self._handle_yara_get_ruleset_text,
            self.ACTION_ID_GET_YARA_MATCHES: self._handle_get_yara_matches,
            self.ACTION_ID_YARA_RETRO_ENABLE_HUNT: self._handle_yara_retro_enable_hunt,
            self.ACTION_ID_YARA_RETRO_START_HUNT: self._handle_yara_retro_start_hunt,
            self.ACTION_ID_YARA_RETRO_CHECK_STATUS: self._handle_yara_retro_check_status,
            self.ACTION_ID_YARA_RETRO_CANCEL_HUNT: self._handle_yara_retro_cancel_hunt,
            self.ACTION_ID_GET_YARA_RETRO_MATCHES: self._handle_get_yara_retro_matches,
            self.ACTION_ID_GET_URL_DOWNLOADED_FILES: self._handle_get_url_downloaded_files,
            self.ACTION_ID_GET_LATEST_URL_ANALYSIS_FEED: self._handle_get_latest_url_analysis_feed,
            self.ACTION_ID_GET_URL_ANALYSIS_FEED_FROM_DATE: self._handle_get_url_analysis_feed_from_date,
            self.ACTION_ID_GET_NETWORK_REPUTATION: self._handle_get_network_reputation,
            self.ACTION_ID_GET_LIST_USER_OVERRIDES: self._handle_get_list_user_overrides,
            self.ACTION_ID_GET_LIST_USER_OVERRIDES_AGGREGATED: self._handle_get_list_user_overrides_aggregated,
            self.ACTION_ID_NETWORK_REPUTATION_USER_OVERRIDE: self._handle_network_reputation_user_override,
            self.ACTION_ID_FILE_REPUTATION_USER_OVERRIDE: self._handle_file_reputation_user_override,
            self.ACTION_ID_LIST_ACTIVE_FILE_REPUTATION_USER_OVERRIDE: self._handle_list_active_file_reputation_user_overrides,
            self.ACTION_ID_CUSTOMER_DAILY_USAGE: self._handle_customer_daily_usage,
            self.ACTION_ID_CUSTOMER_MONTHLY_USAGE: self._handle_customer_monthly_usage,
            self.ACTION_ID_CUSTOMER_MONTHRANGE_USAGE: self._handle_customer_monthrange_usage,
            self.ACTION_ID_CUSTOMER_DAYRANGE_USAGE: self._handle_customer_dayrange_usage,
            self.ACTION_ID_CUSTOMER_YARA_API_USAGE: self._handle_customer_yara_api_usage,
            self.ACTION_ID_CUSTOMER_QUOTA_LIMITS: self._handle_customer_quota_limits,
            self.ACTION_ID_GET_DOMAIN_REPORT: self._handle_get_domain_report,
            self.ACTION_ID_GET_DOMAIN_DOWNLOADED_FILES: self._handle_get_domain_downloaded_files,
            self.ACTION_ID_GET_URLS_FROM_DOMAIN: self._handle_get_urls_from_domain,
            self.ACTION_ID_GET_RESOLUTIONS_FROM_DOMAIN: self._handle_get_resolutions_from_domain,
            self.ACTION_ID_GET_RELATED_DOMAINS: self._handle_get_related_domains,
            self.ACTION_ID_GET_IP_REPORT: self._handle_get_ip_report,
            self.ACTION_ID_GET_IP_DOWNLOADED_FILES: self._handle_get_ip_downloaded_files,
            self.ACTION_ID_GET_URLS_FROM_IP: self._handle_get_urls_from_ip,
            self.ACTION_ID_GET_RESOLUTIONS_FROM_IP: self._handle_get_resolutions_from_ip,
        }

        self._state = None

    def initialize(self):
        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        # get the asset config
        config = self.get_config()
        self.ticloud_username = config["username"]
        self.ticloud_password = config["password"]
        self.ticloud_base_url = config["url"]

        return phantom.APP_SUCCESS

    def finalize(self):
        # Save the state, this data is saved across actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()
        action = self.ACTIONS.get(action_id)
        if not action:
            return

        action_result = self.add_action_result(ActionResult(dict(param)))

        try:
            action(action_result, param)
        except Exception as err:
            return action_result.set_status(phantom.APP_ERROR, str(err))

        return action_result.set_status(phantom.APP_SUCCESS)

    # TCA-0101
    def _handle_file_reputation(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        file_reputation = FileReputation(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = file_reputation.get_file_reputation(hash_input=param.get("hash"), extended_results=True, show_hashes_in_results=True)

        # Using appname+unique_id from config
        app_config = self.get_config()

        # pass values into summary to extract from view
        extra_data = {"directory": app_config["directory"]}
        action_result.set_summary(extra_data)

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    # TCA-0320
    def _handle_advanced_search(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        advanced_search = AdvancedSearch(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = advanced_search.search_aggregated(query_string=param.get("query"), max_results=int(param.get("limit")))

        self.debug_print("Executed", self.get_action_identifier())

        for result in response:
            action_result.add_data(result)

    # TCA-0402
    def _handle_uri_statistics(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        uri_statistics = URIStatistics(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = uri_statistics.get_uri_statistics(uri_input=param.get("uri"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0103
    def _handle_av_scanners(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        xref = AVScanners(host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT)
        response = xref.get_scan_results(hash_input=param.get("hash"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0104
    def _handle_file_analysis(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        rldata = FileAnalysis(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = rldata.get_analysis_results(hash_input=param.get("hash"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0301
    def _handle_functional_similarity(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        similarity = RHA1FunctionalSimilarity(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = similarity.get_similar_hashes_aggregated(hash_input=param.get("hash"), max_results=param.get("limit"))

        self.debug_print("Executed", self.get_action_identifier())

        for result in response:
            action_result.add_data(result)

    # TCA-0403
    def _handle_url_reputation(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        url_intelligence = URLThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = url_intelligence.get_url_report(url_input=param.get("url"))

        # Using appname+unique_id from config
        app_config = self.get_config()

        # pass values into summary to extract from view
        extra_data = {"directory": app_config["directory"]}
        action_result.set_summary(extra_data)

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0403
    def _handle_get_url_downloaded_files(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        url_intelligence = URLThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = url_intelligence.get_downloaded_files_aggregated(
            url_input=param.get("url"),
            extended=param.get("extended"),
            classification=param.get("classification"),
            last_analysis=param.get("last_analysis"),
            analysis_id=param.get("analysis_id"),
            results_per_page=param.get("results_per_page"),
            max_results=param.get("max_results"),
        )

        self.debug_print("Executed", self.get_action_identifier())
        for x in response:
            action_result.add_data(x)

    # TCA-0403
    def _handle_get_latest_url_analysis_feed(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        url_intelligence = URLThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = url_intelligence.get_latest_url_analysis_feed_aggregated(
            results_per_page=param.get("results_per_page"), max_results=param.get("max_results")
        )

        self.debug_print("Executed", self.get_action_identifier())
        for x in response:
            action_result.add_data(x)

        self.debug_print("ACTION RESULT DATA:", action_result)

    # TCA-0403
    def _handle_get_url_analysis_feed_from_date(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        url_intelligence = URLThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = url_intelligence.get_url_analysis_feed_from_date_aggregated(
            time_format=param.get("time_format"),
            start_time=param.get("start_time"),
            results_per_page=param.get("results_per_page"),
            max_results=param.get("max_results"),
        )

        self.debug_print("Executed", self.get_action_identifier())
        for x in response:
            action_result.add_data(x)

    # TCA-0404
    def _handle_analyze_url(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        analyze_url = AnalyzeURL(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = analyze_url.submit_url(url_input=param.get("url"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0401
    def _handle_uri_index(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        uri_index = URIIndex(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = uri_index.get_uri_index_aggregated(uri_input=param.get("uri"), max_results=param.get("limit"))

        self.debug_print("Executed", self.get_action_identifier())

        for result in response:
            action_result.add_data(result)

    # TCA-0302
    def _handle_imphash_similarity(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        imphash = ImpHashSimilarity(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = imphash.get_imphash_index_aggregated(imphash=param.get("imphash"), max_results=param.get("limit"))

        self.debug_print("Executed", self.get_action_identifier())

        for result in response:
            action_result.add_data(result)

    # TCA-0106 and TCA-0207
    def _handle_submit_for_dynamic_analysis(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        sandbox = DynamicAnalysis(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = sandbox.detonate_sample(sample_sha1=param.get("sha1"), platform=param.get("platform"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0106 and TCA_0207
    def _handle_submit_url_for_dynamic_analysis(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        sandbox = DynamicAnalysis(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = sandbox.detonate_url(url_string=param.get("url"), platform=param.get("platform"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0207
    def _handle_get_report(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        sandbox = DynamicAnalysis(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = sandbox.get_dynamic_analysis_results(
            sample_hash=param.get("sha1"), latest=param.get("latest"), analysis_id=param.get("analysis_id")
        )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    # TCA-0207
    def _handle_get_url_report(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        sandbox = DynamicAnalysis(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        url_input = param.get("url")

        # check if user provided sha1
        if re.match(r"^[a-fA-F0-9]*$", url_input):
            response = sandbox.get_dynamic_analysis_results(url_sha1=url_input, latest=param.get("latest"), analysis_id=param.get("analysis_id"))
        else:
            response = sandbox.get_dynamic_analysis_results(
                url=param.get("url"), latest=param.get("latest"), analysis_id=param.get("analysis_id")
            )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    # TCA-0205
    def _handle_reanalyze_file(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        reanalyze = ReanalyzeFile(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        reanalyze.renalyze_samples(sample_hashes=param.get("hash"))

        self.debug_print("Executed", self.get_action_identifier())

    # TCA-0202
    def _handle_upload_file(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        file_vault_id = param["vault_id"]
        success, msg, files_array = vault.vault_info(container_id=self.get_container_id())
        if not success:
            raise Exception(f"Unable to get Vault item details. Error details: {msg}")

        file = next(filter(lambda x: x["vault_id"] == file_vault_id, files_array), None)
        if not file:
            raise Exception(f"Unable to get Vault item details. Error details: {msg}")

        with open(file["path"], "rb") as file_handle:
            payload = file_handle.read()

            parse_url = urlparse(self.ticloud_base_url)

            if parse_url.scheme:
                base_url_with_schema = self.ticloud_base_url
            else:
                base_url_with_schema = "https://" + self.ticloud_base_url

            response = requests.post(
                url="{base_url}{ticloud_spex_url}{file_sha1}".format(
                    base_url=base_url_with_schema, ticloud_spex_url=self.ticloud_spex_url, file_sha1=file["metadata"]["sha1"]
                ),
                auth=(self.ticloud_username, self.ticloud_password),
                data=payload,
                verify=True,  # nosemgrep
                headers={"User-Agent": self.USER_AGENT, "Content-Type": "application/octet-stream"},
            )

            self.debug_print("Executed", self.get_action_identifier())

            if response.status_code != 200:
                raise Exception(f"Unable to upload file to TitaniumCloud. Status code: {response.status_code}")

            if param.get("file_name"):
                sample_name = param.get("file_name")
            else:
                sample_name = "sample"

            meta_xml = (
                f"<rl><properties><property><name>file_name</name><value>{sample_name}</value></property>"
                f"</properties><domain>{None}</domain></rl>"
            )

            response = requests.post(
                url="{base_url}{ticloud_spex_url}{file_sha1}/meta".format(
                    base_url=base_url_with_schema,
                    ticloud_spex_url=self.ticloud_spex_url,
                    file_sha1=file["metadata"]["sha1"],
                ),
                auth=(self.ticloud_username, self.ticloud_password),
                data=meta_xml,
                verify=True,  # nosemgrep
                headers={"User-Agent": self.USER_AGENT, "Content-Type": "application/octet-stream"},
            )

            self.debug_print("Executed", self.get_action_identifier())

            if response.status_code != 200:
                raise Exception(f"Unable to upload file meta to TitaniumCloud. Status code: {response.status_code}")

    # TCA-0201
    def _handle_get_file(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        file_download = FileDownload(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = file_download.download_sample(hash_input=param.get("hash"))

        self.debug_print("Executed", self.get_action_identifier())

        file_path = os.path.join(Vault.get_vault_tmp_dir(), param.get("hash"))
        with open(file_path, "wb") as file_obj:
            file_obj.write(response.content)

        success, msg, vault_id = vault.vault_add(file_location=file_path, container=self.get_container_id(), file_name=param.get("hash"))
        if not success:
            raise Exception(f"Unable to store file in Vault. Error details: {msg}")

    # TCA-0303
    def _handle_yara_create_ruleset(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara = YARAHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara.create_ruleset(ruleset_name=param.get("ruleset_name"), ruleset_text=param.get("ruleset_text"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0303
    def _handle_yara_delete_ruleset(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara = YARAHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        yara.delete_ruleset(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

    # TCA-0303
    def _handle_yara_get_ruleset_info(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara = YARAHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara.get_ruleset_info(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0303
    def _handle_yara_get_ruleset_text(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara = YARAHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara.get_ruleset_text(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0303
    def _handle_get_yara_matches(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara = YARAHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara.yara_matches_feed(time_format=param.get("time_format"), time_value=param.get("time_value"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0319
    def _handle_yara_retro_enable_hunt(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara_retro = YARARetroHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara_retro.enable_retro_hunt(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0319
    def _handle_yara_retro_start_hunt(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara_retro = YARARetroHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara_retro.start_retro_hunt(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0319
    def _handle_yara_retro_check_status(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara_retro = YARARetroHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara_retro.check_status(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0319
    def _handle_yara_retro_cancel_hunt(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara_retro = YARARetroHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara_retro.cancel_retro_hunt(ruleset_name=param.get("ruleset_name"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0319
    def _handle_get_yara_retro_matches(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        yara_retro = YARARetroHunting(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )
        response = yara_retro.yara_retro_matches_feed(time_format=param.get("time_format"), time_value=param.get("time_value"))

        self.debug_print("Executed", self.get_action_identifier())

        action_result.add_data(response.json())

    # TCA-0407
    def _handle_get_network_reputation(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        network_reputation = NetworkReputation(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = network_reputation.get_network_reputation(network_locations=list(param.get("network_locations").split()))

        self.debug_print("Executed", self.get_action_identifier())

        for x in response.json()["rl"]["entries"]:
            action_result.add_data(x)

        # Using appname+unique_id from config
        app_config = self.get_config()

        # pass valies into summary to extract from view
        extra_data = {"directory": app_config["directory"]}
        action_result.set_summary(extra_data)

        return action_result.get_status()

    # TCA-0408
    def _handle_get_list_user_overrides(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        list_user_override = NetworkReputationUserOverride(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = list_user_override.list_overrides(next_page_sha1=param.get("next_page_sha1"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0408
    def _handle_get_list_user_overrides_aggregated(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        override_list = NetworkReputationUserOverride(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = override_list.list_overrides_aggregated(max_results=param.get("max_results"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response)

    # TCA-0408
    def _handle_network_reputation_user_override(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        override_list = NetworkReputationUserOverride(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        list_override = [json.loads(param.get("override_list"))]
        remove_list_check = param.get("remove_overrides_list")

        if remove_list_check is None:
            remove_list = []
        else:
            remove_list = [json.loads(param.get("remove_overrides_list"))]

        response = override_list.reputation_override(override_list=list_override, remove_overrides_list=remove_list)

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    # TCA-0102
    def _handle_file_reputation_user_override(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        overrides_list = FileReputationUserOverride(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        list_override_check = param.get("override_samples")
        remove_list_check = param.get("remove_overrides")

        if list_override_check is None:
            list_override = []
        else:
            list_override = [json.loads(param.get("override_samples"))]

        if remove_list_check is None:
            remove_list = []
        else:
            remove_list = [json.loads(param.get("remove_overrides"))]

        response = overrides_list.override_classification(override_samples=list_override, remove_override=remove_list)

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json())

    # TCA-0102
    def _handle_list_active_file_reputation_user_overrides(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        list_user_override = FileReputationUserOverride(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = list_user_override.list_active_overrides(hash_type=param.get("hash_type"), start_hash=param.get("start_hash"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-9999
    def _handle_customer_daily_usage(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        customer_usage = CustomerUsage(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = customer_usage.daily_usage(single_date=param.get("date"), whole_company=param.get("company"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-9999
    def _handle_customer_dayrange_usage(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        customer_usage = CustomerUsage(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = customer_usage.daily_usage(from_date=param.get("from_date"), to_date=param.get("to_date"), whole_company=param.get("company"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-9999
    def _handle_customer_monthly_usage(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        customer_usage = CustomerUsage(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = customer_usage.monthly_usage(single_month=param.get("month"), whole_company=param.get("company"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-9999
    def _handle_customer_monthrange_usage(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        customer_usage = CustomerUsage(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = customer_usage.monthly_usage(
            from_month=param.get("from_month"), to_month=param.get("to_month"), whole_company=param.get("company")
        )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-9999
    def _handle_customer_yara_api_usage(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        customer_usage = CustomerUsage(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = customer_usage.active_yara_rulesets()

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-9999
    def _handle_customer_quota_limits(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        customer_usage = CustomerUsage(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = customer_usage.quota_limits(whole_company=param.get("company"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0405
    def _handle_get_domain_report(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        domain_report = DomainThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = domain_report.get_domain_report(domain=param.get("domain"))

        # Using appname+unique_id from config
        app_config = self.get_config()

        # pass valies into summary to extract from view
        extra_data = {"directory": app_config["directory"]}
        action_result.set_summary(extra_data)

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0405
    def _handle_get_domain_downloaded_files(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        downloaded_files = DomainThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = downloaded_files.get_downloaded_files(
            domain=param.get("domain"),
            extended=param.get("extended"),
            results_per_page=param.get("limit"),
            classification=param.get("classification"),
        )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0405
    def _handle_get_urls_from_domain(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        domain = DomainThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = domain.urls_from_domain(domain=param.get("domain"), page_string=param.get("page"), results_per_page=param.get("limit"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0405
    def _handle_get_resolutions_from_domain(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        resolutions = DomainThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = resolutions.domain_to_ip_resolutions(
            domain=param.get("domain"), page_string=param.get("page"), results_per_page=param.get("limit")
        )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0405
    def _handle_get_related_domains(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        domains = DomainThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = domains.related_domains(domain=param.get("domain"), page_string=param.get("page"), results_per_page=param.get("limit"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0406
    def _handle_get_ip_report(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        ip_report = IPThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = ip_report.get_ip_report(ip_address=param.get("ip_address"))

        # Using appname+unique_id from config
        app_config = self.get_config()

        # pass valies into summary to extract from view
        extra_data = {"directory": app_config["directory"]}
        action_result.set_summary(extra_data)

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0406
    def _handle_get_ip_downloaded_files(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        downloaded_files = IPThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = downloaded_files.get_downloaded_files(
            ip_address=param.get("ip_address"),
            extended=param.get("extended"),
            page_string=param.get("page"),
            results_per_page=param.get("limit"),
            classification=param.get("classification"),
        )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0406
    def _handle_get_urls_from_ip(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        ip_urls = IPThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = ip_urls.urls_from_ip(ip_address=param.get("ip_address"), page_string=param.get("page"), results_per_page=param.get("limit"))

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    # TCA-0406
    def _handle_get_resolutions_from_ip(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        resolutions = IPThreatIntelligence(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        response = resolutions.ip_to_domain_resolutions(
            ip_address=param.get("ip_address"), page_string=param.get("page"), results_per_page=param.get("limit")
        )

        self.debug_print("Executed", self.get_action_identifier())
        action_result.add_data(response.json()["rl"])

        return action_result.get_status()

    def _handle_test_connectivity(self, action_result, param):
        self.debug_print("Action handler", self.get_action_identifier())

        file_reputation = FileReputation(
            host=self.ticloud_base_url, username=self.ticloud_username, password=self.ticloud_password, user_agent=self.USER_AGENT
        )

        file_reputation.get_file_reputation(
            hash_input="6a95d3d00267c9fd80bd42122738e726",  # pragma: allowlist secret
            extended_results=True,
            show_hashes_in_results=False,
        )

        self.save_progress("Test Connectivity Passed")


def main():
    import argparse
    import sys

    argparser = argparse.ArgumentParser()
    args = argparser.parse_args()
    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)

        connector = ReversinglabsTitaniumCloudV2Connector()
        connector.print_progress_message = True

        connector._handle_action(json.dumps(in_json), None)
    sys.exit(0)


if __name__ == "__main__":
    main()
