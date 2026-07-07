##
## SPDX-FileCopyrightText: 2025 Splunk LLC
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##

[remedy_input://<name>]
account = <string> Name of the account that would be used to get data.
form_type =  <string> Form Type for which data will be collected.
form_name =  <string> Form Name for which data will be collected.
include_properties = <list> Properties of the form to be included (comma separated).'timefield' will be added by default.
exclude_properties = <list> Properties of the form to be excluded (comma separated).
timefield = <string> Time field of the form (Default is 'Last Modified Date').
reuse_checkpoint = <bool> Whether to use existing data input or not.
query_start_date = <string> The datetime after which to query and index records, in this format: "YYYY-MM-DD hh:mm:ss" (Default is one week ago).
qualification = <list> Provide qualification in key-value pairs as shown in example to fetch only selected data from the form eg. 'key1'="value1" AND 'key2'="value2" (By default no qualification will be applied).
