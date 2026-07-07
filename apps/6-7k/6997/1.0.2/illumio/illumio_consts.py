# File: illumio_consts.py
#
# Copyright (c) Illumio, 2023-2025
#
# This unpublished material is proprietary to Illumio.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Illumio.
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

PROTOCOL_LIST = ["tcp", "udp"]
ENFORCEMENT_MODE_LIST = ["idle", "visibility_only", "full", "selective"]
BOOLEAN_LIST = ["True", "False"]
PORT_MAX_VALUE = 65535
ILLUMIO_INVALID_PROTOCOL_MSG = "Please enter a valid value for 'protocol' parameter"
ILLUMIO_EXISTING_OBJECT_MSG = "already in use"
ILLUMIO_EXISTING_VIRTUAL_SERVICE_MSG = "Name must be unique"
ILLUMIO_INVALID_VIRTUAL_SERVICE_HREF = "Invalid URI"
DEFAULT_REQUEST_TIMEOUT = 30  # in seconds
