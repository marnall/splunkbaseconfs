# File: sekoiaio_consts.py
#
# Copyright (c) 2023-2025 SEKOIA.IO
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

# Log messages
EMPTY_RESPONSE_ERROR_LOG = "Empty response and no information in the header"
JSON_RESPONSE_400_ERROR_LOG = "Invalid parameters. \
        Please recheck your parameters."
JSON_RESPONSE_401_ERROR_LOG = "Authentification failed. Please \
        pay attention to use an API KEY"
JSON_RESPONSE_403_ERROR_LOG = "Insufficient permissions. \
    please check if you have an INTHREAT_READ_OBJECTS permission"
DOCUMENTATION_LOG = "Please visit the API Key documentation \
        for more information: \
        https://docs.sekoia.io/getting_started/manage_api_keys/"
