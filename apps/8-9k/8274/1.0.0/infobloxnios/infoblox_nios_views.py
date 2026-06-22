# File: infoblox_nios_views.py
#
# Copyright 2025 Infoblox Inc.
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


def display_create_host_record(provides, all_app_runs, context):
    """
    Display Create Host Record Data

    This function renders a custom view for the Infoblox NIOS create host record action.
    It displays the created host record details in a horizontal table format.

    Args:
        provides (str): The name of the action that provides the data
        all_app_runs (list): List of all app runs
        context (dict): Context to render the template with

    Returns:
        str: The path to the HTML template to render
    """
    context["has_data"] = False

    # Basic host information
    context["reference_id"] = ""
    context["name"] = ""
    context["view"] = ""
    context["zone"] = ""
    context["network_view"] = ""

    # Status and configuration
    context["disable"] = False
    context["configure_for_dns"] = False
    context["comment"] = ""

    # Address information
    context["ipv4_addresses"] = []
    context["ipv4_count"] = 0
    context["ipv6_addresses"] = []
    context["ipv6_count"] = 0

    # Extended attributes
    context["extended_attributes"] = []
    context["extattrs_count"] = 0

    for _, action_results in all_app_runs:
        for result in action_results:
            # Get the raw data from the action result
            data = result.get_data()
            if not data:
                continue

            context["has_data"] = True

            # Get the first data item (host record)
            host_record = data[0]

            # Extract basic host information
            context["reference_id"] = host_record.get("_ref", "")
            context["name"] = host_record.get("name", "")
            context["view"] = host_record.get("view", "")
            context["zone"] = host_record.get("zone", "")
            context["network_view"] = host_record.get("network_view", "")

            # Status and configuration
            context["disable"] = host_record.get("disable", False)
            context["configure_for_dns"] = host_record.get("configure_for_dns", False)
            context["comment"] = host_record.get("comment", "")

            # Extract IPv4 addresses
            ipv4_addresses = host_record.get("ipv4addrs", [])
            context["ipv4_addresses"] = ipv4_addresses
            context["ipv4_count"] = len(ipv4_addresses)

            # Extract IPv6 addresses
            ipv6_addresses = host_record.get("ipv6addrs", [])
            context["ipv6_addresses"] = ipv6_addresses
            context["ipv6_count"] = len(ipv6_addresses)

            # Extract extended attributes
            extattrs = host_record.get("extattrs", {})
            extended_attributes = []
            for key, value_dict in extattrs.items():
                if isinstance(value_dict, dict) and "value" in value_dict:
                    extended_attributes.append({"name": key, "value": value_dict.get("value", "")})
            context["extended_attributes"] = extended_attributes
            context["extattrs_count"] = len(extended_attributes)

    return "views/infoblox_nios_create_host_record.html"


def display_search_rpz_rule(provides, all_app_runs, context):
    """
    Display Search RPZ Rule Data

    This function renders a custom view for the Infoblox NIOS search RPZ rule action.
    It dynamically handles both default fields and additional fields specified by the user.

    Args:
        provides (str): The name of the action that provides the data
        all_app_runs (list): List of all app runs
        context (dict): Context to render the template with

    Returns:
        str: The path to the HTML template to render
    """
    context["results"] = []
    context["has_data"] = False
    context["rule_name"] = ""
    context["object_type"] = ""
    context["total_rules"] = 0
    context["output_fields"] = ""

    for _, action_results in all_app_runs:
        for result in action_results:
            # Get the raw data from the action result
            data = result.get_data()
            if not data:
                continue

            context["has_data"] = True
            context["total_rules"] = len(data)

            # Get the search parameters
            params = result.get_param()
            context["rule_name"] = params.get("rule_name", "")
            context["object_type"] = params.get("object_type", "record:rpz:cname")

            # Get output fields if specified
            output_fields_param = params.get("output_fields", "")
            context["output_fields"] = output_fields_param

            # Collect all unique fields across all rules
            all_fields = set()
            for rule in data:
                all_fields.update(rule.keys())

            # Always include default fields first
            default_fields = [
                "priority",
                "target_name",
                "ipv6addr",
                "mail_exchanger",
                "preference",
                "order",
                "regexp",
                "replacement",
                "services",
                "ptrdname",
                "port",
                "target",
                "weight",
                "text",
                "ref",
                "name",
                "view",
                "canonical",
                "ipv4addr",
            ]

            display_fields = []

            # Add default fields that exist in the data
            for field in default_fields:
                if field in all_fields:
                    display_fields.append(field)
                    all_fields.discard(field)

            # Add any additional fields from output_fields parameter
            if output_fields_param:
                requested_fields = [f.strip() for f in output_fields_param.split(",")]
                # Limit to first 3 requested fields only
                requested_fields = requested_fields[:3]
                for field in requested_fields:
                    if field in all_fields and field not in display_fields:
                        display_fields.append(field)
                        all_fields.discard(field)

            # Pre-process the data for the template
            processed_data = []
            for rule in data:
                processed_rule = []

                # Process each field in the rule
                for field in display_fields:
                    value = rule.get(field)
                    field_info = {"field_name": field, "raw_value": value, "display_value": "", "field_type": "text"}

                    # Set display value and type based on value type
                    if isinstance(value, bool):
                        field_info["display_value"] = "True" if value else "False"
                        field_info["field_type"] = "boolean"
                        field_info["is_true"] = value
                    elif value == "":
                        field_info["display_value"] = ""
                        field_info["field_type"] = "empty"
                    elif value is None:
                        field_info["display_value"] = "-"
                        field_info["field_type"] = "empty"
                    elif isinstance(value, dict):
                        field_info["field_type"] = "object"
                        # For objects, try to show a meaningful summary
                        if field == "extattrs" and value:
                            # For extattrs, show key-value pairs
                            items = []
                            for key, val in value.items():
                                # Handle nested objects in extattrs
                                if isinstance(val, dict) and "value" in val:
                                    # Infoblox extattrs often have structure like {"value": "actual_value"}
                                    items.append(f"{key}: {val['value']}")
                                else:
                                    # Simple key-value or other structure
                                    val_str = str(val)[:20]
                                    if len(str(val)) > 20:
                                        val_str += "..."
                                    items.append(f"{key}: {val_str}")

                            if len(items) <= 2:
                                field_info["display_value"] = f"Attrs: {'; '.join(items)}"
                            else:
                                field_info["display_value"] = f"Attrs: {'; '.join(items[:2])}... (+{len(items) - 2})"
                        elif len(value) == 0:
                            field_info["display_value"] = "-"
                        elif len(value) == 1:
                            key, val = next(iter(value.items()))
                            field_info["display_value"] = f"{key}: {str(val)[:30]}{'...' if len(str(val)) > 30 else ''}"
                        else:
                            field_info["display_value"] = f"Object ({len(value)} keys)"
                        try:
                            field_info["json_value"] = json.dumps(value)
                        except:
                            field_info["json_value"] = str(value)
                    elif isinstance(value, list):
                        field_info["field_type"] = "array"
                        # For arrays, show count and type of first element if available
                        if len(value) == 0:
                            field_info["display_value"] = "Empty Array"
                        elif len(value) == 1:
                            first_item = value[0]
                            if isinstance(first_item, dict):
                                field_info["display_value"] = f"Array [1 object]"
                            else:
                                field_info["display_value"] = f"Array [1]: {str(first_item)[:20]}{'...' if len(str(first_item)) > 20 else ''}"
                        else:
                            first_item = value[0]
                            if isinstance(first_item, dict):
                                field_info["display_value"] = f"Array [{len(value)} objects]"
                            else:
                                field_info["display_value"] = (
                                    f"Array [{len(value)}]: {str(first_item)[:15]}{'...' if len(str(first_item)) > 15 else ''}"
                                )
                        try:
                            field_info["json_value"] = json.dumps(value)
                        except:
                            field_info["json_value"] = str(value)
                    else:
                        field_info["display_value"] = str(value)
                        field_info["field_type"] = "text"

                    processed_rule.append(field_info)

                processed_data.append(processed_rule)

            context["display_fields"] = display_fields
            context["results"] = processed_data

    return "views/infoblox_nios_search_rpz_rule.html"
