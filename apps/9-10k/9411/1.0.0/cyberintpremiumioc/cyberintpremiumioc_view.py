# File: cyberintpremiumioc_view.py
#
# Copyright (c) 2025-2026 Splunk Inc.
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
import json


def _enrichment_view(all_app_runs, context, template, param_key):
    """
    Render the results of an already-run enrichment action.

    Custom views do not run actions; SOAR passes the results of the action that
    has already executed via ``all_app_runs``. Each app run is a
    ``(summary, action_results)`` tuple, and every ``ActionResult`` exposes the
    action parameters (``get_param``) and the data the connector attached
    (``get_data``). We flatten those into ``context["results"]`` for the template.
    """
    context["results"] = results = []
    for _summary, action_results in all_app_runs:
        for result in action_results:
            param = result.get_param()
            data = result.get_data()
            enrichment = data[0] if data else {}
            results.append(
                {
                    "indicator_value": param.get(param_key, ""),
                    "data": enrichment,
                    "data_json": json.dumps(enrichment, indent=2, sort_keys=True) if enrichment else "",
                }
            )
    return template


def enrich_sha256_view(provides, all_app_runs, context):
    return _enrichment_view(all_app_runs, context, "enrich_sha256_view.html", "Hash")


def enrich_ipv4_view(provides, all_app_runs, context):
    return _enrichment_view(all_app_runs, context, "enrich_ipv4_view.html", "IP")


def enrich_url_view(provides, all_app_runs, context):
    return _enrichment_view(all_app_runs, context, "enrich_url_view.html", "URL")


def enrich_domain_view(provides, all_app_runs, context):
    return _enrichment_view(all_app_runs, context, "enrich_domain_view.html", "Domain")
