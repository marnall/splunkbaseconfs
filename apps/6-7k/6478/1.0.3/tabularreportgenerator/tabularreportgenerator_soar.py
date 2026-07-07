# Copyright (c) 2025 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import requests

from tabularreportgenerator_consts import DEFAULT_TIMEOUT


def get_custom_list(connector, custom_list_name):
    phantom_base_url = connector.get_phantom_base_url()
    url = f"{phantom_base_url}rest/decided_list/{custom_list_name}/formatted_content?_output_format=csv&_fs=,&_rs=%0A"
    r = requests.get(url, verify=False, timeout=DEFAULT_TIMEOUT)  # nosemgrep
    r.raise_for_status()
    custom_list = r.content.decode("utf-8-sig")
    return custom_list
