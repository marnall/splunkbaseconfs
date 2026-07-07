# File: google_threat_intelligence_views.py
#
# Copyright 2025-2026 Google LLC
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


def display_curated_threat_intelligence(provides, all_app_runs, context):
    """
    Display Curated Threat Intelligence

    This function renders a view that displays a curated view of threat intelligence
    related to an entity. The view is a table with links to other VT UI pages.

    Args:
        provides (phantom.app_action_result.ActionResult): Action result from the app
        all_app_runs (list): List of all app runs
        context (dict): Context to render the template with

    Returns:
        str: The rendered HTML template
    """
    context["relationships"] = {"campaigns": [], "malware_families": [], "related_threat_actors": [], "reports": []}
    for _, action_results in all_app_runs:
        for result in action_results:
            raw = result.get_data()
            # Some actions return a list of items, sometimes a single dict
            if isinstance(raw, list):
                # If it's a list of responses, pick the first one (or loop them)
                payload = raw[0] if raw else {}
            elif isinstance(raw, dict):
                payload = raw
            else:
                payload = {}

            # Safely pull out the "data" dict
            data = payload.get("data", {})
            context["entity"] = data.get("id")
            context["entity_type"] = data.get("type")

            def parse_relationship(relationship_name, want_desc=False):
                """
                Helper to extract relationships

                Args:
                    relationship_name (str): Name of the relationship
                    want_desc (bool): Flag to include description

                Returns:
                    list: List of relationships
                """
                items = []
                rel_list = data.get("relationships", {}).get(relationship_name, {}).get("data", [])
                for entry in rel_list:
                    item = {"id": entry.get("id")}
                    attrs = entry.get("attributes", {}) or {}

                    def extract_comma_separated(items, key):
                        return ",".join([item[key] for item in items if item.get(key)])

                    source_regions = extract_comma_separated(attrs.get("source_regions_hierarchy", []), "country_iso2")
                    targeted_regions = extract_comma_separated(attrs.get("targeted_regions_hierarchy", []), "country_iso2")
                    targeted_industries = extract_comma_separated(attrs.get("targeted_industries_tree", []), "industry_group")

                    item.update(
                        {
                            "name": attrs.get("name"),
                            "origin": attrs.get("origin"),
                            "source_regions": source_regions,
                            "targeted_regions": targeted_regions,
                            "targeted_industries": targeted_industries,
                        }
                    )

                    if want_desc and attrs.get("description"):
                        item["description"] = attrs.get("description")
                    items.append(item)
                return items

            context["relationships"]["campaigns"] = parse_relationship("campaigns", want_desc=True)
            context["relationships"]["malware_families"] = parse_relationship("malware_families", want_desc=True)
            context["relationships"]["related_threat_actors"] = parse_relationship("related_threat_actors", want_desc=True)
            context["relationships"]["reports"] = parse_relationship("reports")

    #  Render the template with the above context
    return "views/google_threat_intelligence_curated_threat_intelligence.html"
