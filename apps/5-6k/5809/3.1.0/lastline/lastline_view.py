# File: lastline_view.py
#
# Copyright (c) 2015-2023 Splunk Inc.
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
def mask_string(url):
    return url.lower() \
           .replace('http', 'hXXp') \
           .replace('/', '[/]') \
           .replace(':[/][/]', '[://]') \
           .replace('.', '[.]') \
           .replace('?', '[?]') \
           .replace('=', '[=]') \
           .replace('&', '[&]')


def parse_report(report):
    # pre-process the report here if required

    ana_subjects = report.get('analysis_subjects')

    if not ana_subjects:
        return

    for subject in ana_subjects:
        file_name = None
        try:
            file_name = subject['overview']['process']['executable']['static_pe_information']['original_filename']
        except:
            pass

        if not file_name:
            try:
                file_name = subject['overview']['process']['executable']['abs_path']
                file_name = file_name.split('\\')[-1]
            except:
                pass

        if not file_name:
            try:
                file_name = subject['overview']['process']['executable']['filename']
                file_name = file_name.split('\\')[-1]
            except:
                pass

        if not file_name:
            file_name = "no_name"

        pid = None

        try:
            pid = subject['overview']['process']['process_id']
        except:
            pid = "Unknown"
            pass

        subject['process_display'] = "{0} (PID: {1})".format(file_name, pid)

    return report


def get_ctx_result(result):

    ctx_result = {'summary': result.get_summary(), 'param': result.get_param(), 'status': result.get_status()}

    if not ctx_result['status']:
        ctx_result['message'] = result.get_message()

    data = result.get_data()

    if not data:
        return ctx_result

    data = data[0]

    report = data.get('report')

    if not report:
        return ctx_result

    ctx_result['report'] = report
    parse_report(report)

    return ctx_result


def display_report(provides, all_app_runs, context):

    context['results'] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:

            ctx_result = get_ctx_result(result)
            if not ctx_result:
                continue
            results.append(ctx_result)
    # print context
    return 'lastline_display_report.html'


def display_artifacts(provides, all_app_runs, context):
    context['results'] = results = []
    for summary, action_results in all_app_runs:
        for result in action_results:
            for data in result.get_data():
                if 'url' in data:
                    data['masked_url'] = mask_string(data['url'])
                if 'file' in data:
                    data['masked_file'] = mask_string(data['source_file'])
                results.append({
                    'param': result.get_param(),
                    'data': data,
                    'summary': result.get_summary()
                })

    return 'lastline_display_artifacts.html'
