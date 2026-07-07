# --
# File: cyphort_view.py
# Copyright (c) 2014-2021 Splunk Inc.
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


def get_ctx_result(result):

    ctx_result = {}
    param = result.get_param()

    ctx_result['task_id'] = param.get('id')
    ctx_result['vault_id'] = param.get('vault_id')
    ctx_result['vault_file_name'] = param.get('file_name')

    data = result.get_data()

    if (not data):
        return ctx_result

    data = data[0]

    if (not data):
        return ctx_result

    ctx_result['analysis_details'] = data.get('analysis_details', {}).get('analysis_details')
    ctx_result['analysis_array'] = data.get('analysis_details', {}).get('analysis_array')
    ctx_result['behavior_details'] = data.get('behavior_details')

    message = result.get_message()

    if (message) and ('max polling attempts' in message):
        ctx_result['message'] = message

    return ctx_result


def display_report(provides, all_app_runs, context):

    context['results'] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if (not ctx_result):
                continue
            results.append(ctx_result)
    # print context
    return 'cyphort_display_report.html'
