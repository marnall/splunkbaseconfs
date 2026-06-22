# Copyright (c) 2025-2026 Splunk Inc.
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
import phantom.app as phantom
from django.http import HttpResponse
from django.template import loader

from cyberintalerts_connector import CyberintAlertsConnector
from cyberintalerts_consts import ALERTS_ENDPOINT


def get_enriched_alerts_view(request, **kwargs):
    """
    This view function will be called by Splunk SOAR to render the custom view.
    """
    connector = CyberintAlertsConnector()
    connector.handle_action = lambda x: x
    connector.initialize()

    action_result = connector.add_action_result(phantom.action_result.ActionResult(dict()))

    ret_val, response = connector._make_rest_call(ALERTS_ENDPOINT, action_result, method="post", json={})
    if phantom.is_fail(ret_val):
        return HttpResponse(f"Failed to get alerts: {action_result.get_message()}", status=500)

    alerts = response.get("alerts", [])
    ref_ids = [alert["ref_id"] for alert in alerts]

    ret_val, full_alerts = connector._get_full_alert_from_ref_id(ref_ids, action_result)
    if phantom.is_fail(ret_val):
        return HttpResponse(f"Failed to get full alerts: {action_result.get_message()}", status=500)

    ret_val, enriched_alerts = connector._enrich_alert_indicators(full_alerts, action_result)
    if phantom.is_fail(ret_val):
        return HttpResponse(f"Failed to enrich alerts: {action_result.get_message()}", status=500)

    template = loader.get_template("cyberintalerts_view.html")
    context = {
        "alerts": enriched_alerts,
    }
    return HttpResponse(template.render(context, request))


def update_alert_status_view(request, **kwargs):
    """
    This view function will be called by Splunk SOAR to update the status of an alert.
    """
    if request.method == "POST":
        connector = CyberintAlertsConnector()
        connector.handle_action = lambda x: x
        connector.initialize()

        param = {
            "alert_ref_ids": request.POST.get("alert_ref_id"),
            "status": request.POST.get("status"),
            "closure_reason": request.POST.get("closure_reason"),
        }

        action_result = connector.add_action_result(phantom.action_result.ActionResult(dict(param)))
        result = connector._handle_update_alert_status(param)

        if phantom.is_fail(result):
            return HttpResponse(
                f"Failed to update alert status: {action_result.get_message()}",
                status=500,
            )

        return HttpResponse("Alert status updated successfully.")
    return HttpResponse("Invalid request method.", status=405)


def submit_takedown_view(request, **kwargs):
    """
    This view function will be called by Splunk SOAR to submit a takedown request.
    """
    if request.method == "POST":
        connector = CyberintAlertsConnector()
        connector.handle_action = lambda x: x
        connector.initialize()

        param = {
            "url": request.POST.get("url"),
            "reason": request.POST.get("reason"),
            "brand": request.POST.get("brand"),
            "original_url": request.POST.get("original_url"),
            "alert_id": request.POST.get("alert_id"),
            "note": request.POST.get("note"),
        }

        action_result = connector.add_action_result(phantom.action_result.ActionResult(dict(param)))
        result = connector._handle_submit_takedown(param)

        if phantom.is_fail(result):
            return HttpResponse(f"Failed to submit takedown: {action_result.get_message()}", status=500)

        return HttpResponse("Takedown submitted successfully.")

    template = loader.get_template("submit_takedown_view.html")
    return HttpResponse(template.render({}, request))


def takedown_view(request, **kwargs):
    """
    This view function will be called by Splunk SOAR to display the list of takedowns.
    """
    connector = CyberintAlertsConnector()
    connector.handle_action = lambda x: x
    connector.initialize()

    # The customer_id should be passed as a query parameter to the view URL
    customer_id = request.GET.get("customer_id")
    if not customer_id:
        return HttpResponse("Error: customer_id query parameter is required.", status=400)

    param = {"Customer_ID": customer_id}
    action_result = connector.add_action_result(phantom.action_result.ActionResult(dict(param)))
    result = connector._handle_retrieve_takedowns(param)
    takedowns = []
    if phantom.is_success(result):
        takedowns = action_result.get_data()

    template = loader.get_template("takedown_view.html")
    context = {
        "takedowns": takedowns,
    }
    return HttpResponse(template.render(context, request))
