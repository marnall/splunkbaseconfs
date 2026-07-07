[comment]: # "Auto-generated SOAR connector documentation"
# QR Code

Publisher: Splunk Community  
Connector Version: 1.0.1  
Product Vendor: OpenCV  
Product Name: OpenCV  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 5.3.2.88192  

Extract Data from QR Codes

[comment]: # 'File: README.md'
[comment]: #
[comment]: # 'Copyright (c) Splunk, 2023'
[comment]: #
[comment]: # 'Licensed under the Apache License, Version 2.0 (the "License");'
[comment]: # 'you may not use this file except in compliance with the License.'
[comment]: # 'You may obtain a copy of the License at'
[comment]: #
[comment]: #     'http://www.apache.org/licenses/LICENSE-2.0'
[comment]: #
[comment]: # 'Unless required by applicable law or agreed to in writing, software distributed under'
[comment]: # 'the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,'
[comment]: # 'either express or implied. See the License for the specific language governing permissions'
[comment]: # 'and limitations under the License.'
[comment]: # ''

## QR Code

- This application allows you to extract the data from a QR Code that is in a PNG file. This uses the OpenCV-Python library found here: https://github.com/opencv/opencv-python

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[decode qr code](#action-decode-qr-code) - Decodes a PNG containing a QR code  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'decode qr code'
Decodes a PNG containing a QR code

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | Vault ID of the PNG file | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.vault_id | string |  `vault id`  |  
action_result.status | string |  |   success  failed 
action_result.data.\*.output | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  