# File: awsdynamodb_consts.py
#
# Copyright (c) 2023-2025 Splunk Inc.
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

AWS_DYNAMODB_VALIDATE_INTEGER_MESSAGE = "Please provide a valid integer value in the {key} parameter"
ERROR_MESSAGE_UNAVAILABLE = "Error message unavailable. Please check the asset configuration and|or action parameters"
AWS_DYNAMODB_JSON_REGION = "region"
AWS_DYNAMODB_JSON_ACCESS_KEY = "access_key"
AWS_DYNAMODB_JSON_SECRET_KEY = "secret_key"  # pragma: allowlist secret`
AWS_DYNAMODB_REGIONS = {
    "US East (Ohio)": "us-east-2",
    "US East (N. Virginia)": "us-east-1",
    "US West (N. California)": "us-west-1",
    "US West (Oregon)": "us-west-2",
    "Africa (Cape Town)": "af-south-1",
    "Asia Pacific (Hong Kong)": "ap-east-1",
    "Asia Pacific (Hyderabad)": "ap-south-2",
    "Asia Pacific (Jakarta)": "ap-southeast-3",
    "Asia Pacific (Melbourne)": "ap-southeast-4",
    "Asia Pacific (Mumbai)": "ap-south-1",
    "Asia Pacific (Osaka)": "ap-northeast-3",
    "Asia Pacific (Seoul)": "ap-northeast-2",
    "Asia Pacific (Singapore)": "ap-southeast-1",
    "Asia Pacific (Sydney)": "ap-southeast-2",
    "Asia Pacific (Tokyo)": "ap-northeast-1",
    "Canada (Central)": "ca-central-1",
    "Europe (Frankfurt)": "eu-central-1",
    "Europe (Ireland)": "eu-west-1",
    "Europe (London)": "eu-west-2",
    "Europe (Milan)": "eu-south-1",
    "Europe (Paris)": "eu-west-3",
    "Europe (Spain)": "eu-south-2",
    "Europe (Stockholm)": "eu-north-1",
    "Europe (Zurich)": "eu-central-2",
    "Middle East (Bahrain)": "me-south-1",
    "Middle East (UAE)": "me-central-1",
    "South America (São Paulo)": "sa-east-1",
    "AWS GovCloud (US-East)": "us-gov-east-1",
    "AWS GovCloud (US-West)": "us-gov-west-1",
}
AWS_DYNAMODB_DATATYPES = {"string": "S", "number": "N", "binary": "B"}
AWS_DYNAMODB_KEYTYPE = {"sort": "RANGE", "partition": "HASH"}
CONSUMED_CAPACITY_TYPES = ["INDEXES", "TOTAL", "NONE", ""]
SELECT_VALUES = ["COUNT", "ALL_ATTRIBUTES", "ALL_PROJECTED_ATTRIBUTES", "SPECIFIC_ATTRIBUTES", ""]
STREAM_VIEW_TYPES = ["NEW_IMAGE", "OLD_IMAGE", "NEW_AND_OLD_IMAGES", "KEYS_ONLY", ""]
AWS_DYNAMODB_READ_CAPACITY_UNITS = 5
AWS_DYNAMODB_WRITE_CAPACITY_UNITS = 5
EC2_ROLE_CREDENTIALS_FAILURE_MESSAGE = "Failed to get EC2 role credentials"
AWS_DYNAMODB_BAD_ASSET_CONFIG_MESSAGE = "Please provide access keys or select assume role check box in asset configuration"
AWS_DATE_TIME_CONVERSION = "Converting datetime object to string"
AWS_BOTO_CALL = "Making boto call to DynamoDB"
