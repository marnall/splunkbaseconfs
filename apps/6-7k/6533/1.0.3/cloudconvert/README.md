# Cloud Convert

Publisher: Splunk \
Connector Version: 1.0.3 \
Product Vendor: CloudConvert \
Product Name: CloudConvert \
Minimum Product Version: 6.1.0

This app supports executing investigative and generic type of actions to convert the SOAR vault files to various formats

This app integrates with Cloud Convert to convert the files to specified format.

## Port Details

The app uses HTTP/HTTPS protocol for communicating with the Cloud Convert server. Below are the
default ports used by the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

## Steps to Configure the Cloud Convert Splunk SOAR app's asset

Follow these steps to configure the Cloud Convert Splunk SOAR app's asset:

- Log in to the Cloud Convert platform.

  - Once logged in, select **Dashboard** by clicking the user's profile logo.
  - In the API section, go to **Authorization** .
  - Click on **API Keys** and **Create new** .
  - Now, give any name to your key and give the below-mentioned scopes to it:
    - user.read: View your user data
    - user.write: Update your user data
    - task.read: View your task and job data
    - task.write: Update your task and job data
  - Click on the **Create** button.
  - Copy the generated API Key.
  - NOTE: The API key generated will be shown only once. So store it safely.

- Now, Log in to your Splunk SOAR instance.

  - Navigate to the **Home** dropdown and select **Apps** .
  - Search the Cloud Convert App from the search box.
  - Click on the **CONFIGURE NEW ASSET** button.
  - Navigate to the **Asset Info** tab and enter the Asset name and Asset description.
  - Navigate to the **Asset Settings** .
  - Paste the generated **API Key** from Cloud Convert UI to its respective configuration
    parameter.
  - Mention the number of minutes to poll to convert a file. Default is 1 minute.
  - Save the asset.
  - Now, test the connectivity of the Splunk SOAR server to the Cloud Convert instance by
    clicking the **TEST CONNECTIVITY** button.

## Explanation of the Asset Configuration Parameters

The asset configuration parameters affect 'test connectivity' and some other actions of the
application. The parameters related to test connectivity action are API Key and Number of minutes to
poll for the converted file.

- **API Key:** API Token for asset authorization.
- **Number of minutes to poll for converted file:** The number of minutes the user wants to take
  to convert any file. The default time is one minute.

## Explanation of the Cloud Convert Actions' Parameters

- ### Test Connectivity (Action Workflow Details)

  - This action will test the connectivity of the Splunk SOAR server to the Cloud Convert
    instance by making an initial API call using the provided asset configuration parameters.
  - The action validates the provided asset configuration parameters. Based on the API call
    response, the appropriate success and failure message will be displayed when the action gets
    executed.

- ### Get Valid Filetypes

  To retrieve information of valid input-output formats, the user can run this action.

  - **Action Parameter** : Input filetype

    This is a required parameter. The input filetype supports 200 filetypes. On selecting any
    one of the input format, the action generates a custom view listing valid output formats.

- ### Convert File

  This action lets a user convert file for a valid input-output format.

  - **Action Parameter: Vault ID**

    - This parameter is the unique id for any file and it is a required parameter. In case if
      file content of more than one file is the same but has a different filename then the
      vault ID will be the same for all those files.

  - **Action Parameter: Filetype**

    - This parameter is a required parameter and a dropdown box that lists all the output
      formats into which user wants their file to be converted.

  - **Action Parameter: Input filename**

    - This parameter is an optional parameter and the user needs to provide a name along with
      an extension of the file which has been uploaded to the vault. In the case of different
      vault IDs of files, a user does not need to provide this parameter. If the vault ID of
      more than one file is similar, then the user needs to provide the input filename of the
      file uploaded to the vault. In case the vault ID is similar and the user does not
      provide the input filename, then the output generated file could be any of the similar
      vault IDs.

### Configuration variables

This table lists the configuration variables required to operate Cloud Convert. These variables are specified when configuring a CloudConvert asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_key** | required | password | Cloud Convert API Key |
**timeout** | optional | numeric | Number of minutes to poll for converted file (Default: 1) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[convert file](#action-convert-file) - Convert one filetype to another \
[get valid filetypes](#action-get-valid-filetypes) - Get a list of valid output file formats

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'convert file'

Convert one filetype to another

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | Vault ID | string | `vault id` |
**filetype** | required | Type of the file in output | string | |
**input_filename** | optional | Name of the input file with extension | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.filetype | string | | pdf |
action_result.parameter.input_filename | string | | test.txt |
action_result.parameter.vault_id | string | `vault id` | e772e941546a76022f2ada981ef79faf1c86cf0f |
action_result.data.\*.converted_file | string | | Different language characters.tex |
action_result.data.\*.file_size | string | | 1024 |
action_result.data.\*.vault_id | string | `vault id` | 4a2bc4c1dcaebcb93e19105b11373e81745bf7a1 |
action_result.summary | string | | |
action_result.message | string | | File converted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get valid filetypes'

Get a list of valid output file formats

Type: **investigate** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filetype** | required | Type of the file | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.filetype | string | | pdf |
action_result.data.\*.input_format | string | | txt |
action_result.data.\*.output_format | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully fetched valid output formats |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
