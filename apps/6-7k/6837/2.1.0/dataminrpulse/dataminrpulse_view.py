# File: dataminrpulse_view.py
#
# Copyright (c) 2023-2026 Dataminr
#
# This unpublished material is proprietary to Dataminr.
# All rights reserved. The methods and
# techniques described herein are considered trade secrets
# and/or confidential. Reproduction or distribution, in whole
# or in part, is forbidden except by express written permission
# of Dataminr.
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

import re
from datetime import datetime


def _format_timestamp(timestamp_str):
    """
    Convert ISO timestamp to user-friendly format.

    Args:
        timestamp_str (str): ISO timestamp string like "2025-08-27T09:06:47.124Z"

    Returns:
        str: Formatted timestamp like "8:56 PM Sep 1, 2025" or original string if parsing fails
    """
    if not timestamp_str:
        return timestamp_str

    try:
        # Handle different ISO timestamp formats
        # Remove microseconds if present and handle Z timezone
        clean_timestamp = re.sub(r"\.\d+Z?$", "", timestamp_str.replace("Z", "+00:00"))

        # Parse the timestamp
        if "+" in clean_timestamp or clean_timestamp.endswith("Z"):
            # Handle timezone-aware timestamps
            dt = datetime.fromisoformat(clean_timestamp.replace("Z", "+00:00"))
        else:
            # Handle naive timestamps
            dt = datetime.fromisoformat(clean_timestamp)

        # Format to desired output: "8:56 PM Sep 1, 2025"
        return dt.strftime("%I:%M %p %b %d, %Y").lstrip("0")
    except (ValueError, TypeError):
        # Return original string if parsing fails
        return timestamp_str


def _enrich_entity_country_names(alert_data):
    """
    Maps a country code to its full name.

    Args:
        country_code (str): ISO 3166-1 alpha-2 country code

    Returns:
        str: Full country name or the original code if not found
    """
    country_map = {
        "AF": "Afghanistan",
        "AX": "Aland Islands",
        "AL": "Albania",
        "DZ": "Algeria",
        "AS": "American Samoa",
        "AD": "Andorra",
        "AO": "Angola",
        "AI": "Anguilla",
        "AQ": "Antarctica",
        "AG": "Antigua and Barbuda",
        "AR": "Argentina",
        "AM": "Armenia",
        "AW": "Aruba",
        "AU": "Australia",
        "AT": "Austria",
        "AZ": "Azerbaijan",
        "BS": "Bahamas",
        "BH": "Bahrain",
        "BD": "Bangladesh",
        "BB": "Barbados",
        "BY": "Belarus",
        "BE": "Belgium",
        "BZ": "Belize",
        "BJ": "Benin",
        "BM": "Bermuda",
        "BT": "Bhutan",
        "BO": "Bolivia",
        "BQ": "Bonaire, Sint Eustatius and Saba",
        "BA": "Bosnia and Herzegovina",
        "BW": "Botswana",
        "BV": "Bouvet Island",
        "BR": "Brazil",
        "IO": "British Indian Ocean Territory",
        "BN": "Brunei Darussalam",
        "BG": "Bulgaria",
        "BF": "Burkina Faso",
        "BI": "Burundi",
        "CV": "Cabo Verde",
        "KH": "Cambodia",
        "CM": "Cameroon",
        "CA": "Canada",
        "KY": "Cayman Islands",
        "CF": "Central African Republic",
        "TD": "Chad",
        "CL": "Chile",
        "CN": "China",
        "CX": "Christmas Island",
        "CC": "Cocos (Keeling) Islands",
        "CO": "Colombia",
        "KM": "Comoros",
        "CG": "Congo",
        "CD": "Congo (Democratic Republic)",
        "CK": "Cook Islands",
        "CR": "Costa Rica",
        "CI": "Côte d'Ivoire",
        "HR": "Croatia",
        "CU": "Cuba",
        "CW": "Curaçao",
        "CY": "Cyprus",
        "CZ": "Czechia",
        "DK": "Denmark",
        "DJ": "Djibouti",
        "DM": "Dominica",
        "DO": "Dominican Republic",
        "EC": "Ecuador",
        "EG": "Egypt",
        "SV": "El Salvador",
        "GQ": "Equatorial Guinea",
        "ER": "Eritrea",
        "EE": "Estonia",
        "SZ": "Eswatini",
        "ET": "Ethiopia",
        "FK": "Falkland Islands",
        "FO": "Faroe Islands",
        "FJ": "Fiji",
        "FI": "Finland",
        "FR": "France",
        "GF": "French Guiana",
        "PF": "French Polynesia",
        "TF": "French Southern Territories",
        "GA": "Gabon",
        "GM": "Gambia",
        "GE": "Georgia",
        "DE": "Germany",
        "GH": "Ghana",
        "GI": "Gibraltar",
        "GR": "Greece",
        "GL": "Greenland",
        "GD": "Grenada",
        "GP": "Guadeloupe",
        "GU": "Guam",
        "GT": "Guatemala",
        "GG": "Guernsey",
        "GN": "Guinea",
        "GW": "Guinea-Bissau",
        "GY": "Guyana",
        "HT": "Haiti",
        "HM": "Heard Island and McDonald Islands",
        "VA": "Holy See",
        "HN": "Honduras",
        "HK": "Hong Kong",
        "HU": "Hungary",
        "IS": "Iceland",
        "IN": "India",
        "ID": "Indonesia",
        "IR": "Iran",
        "IQ": "Iraq",
        "IE": "Ireland",
        "IM": "Isle of Man",
        "IL": "Israel",
        "IT": "Italy",
        "JM": "Jamaica",
        "JP": "Japan",
        "JE": "Jersey",
        "JO": "Jordan",
        "KZ": "Kazakhstan",
        "KE": "Kenya",
        "KI": "Kiribati",
        "KP": "North Korea",
        "KR": "South Korea",
        "KW": "Kuwait",
        "KG": "Kyrgyzstan",
        "LA": "Laos",
        "LV": "Latvia",
        "LB": "Lebanon",
        "LS": "Lesotho",
        "LR": "Liberia",
        "LY": "Libya",
        "LI": "Liechtenstein",
        "LT": "Lithuania",
        "LU": "Luxembourg",
        "MO": "Macao",
        "MG": "Madagascar",
        "MW": "Malawi",
        "MY": "Malaysia",
        "MV": "Maldives",
        "ML": "Mali",
        "MT": "Malta",
        "MH": "Marshall Islands",
        "MQ": "Martinique",
        "MR": "Mauritania",
        "MU": "Mauritius",
        "YT": "Mayotte",
        "MX": "Mexico",
        "FM": "Micronesia",
        "MD": "Moldova",
        "MC": "Monaco",
        "MN": "Mongolia",
        "ME": "Montenegro",
        "MS": "Montserrat",
        "MA": "Morocco",
        "MZ": "Mozambique",
        "MM": "Myanmar",
        "NA": "Namibia",
        "NR": "Nauru",
        "NP": "Nepal",
        "NL": "Netherlands",
        "NC": "New Caledonia",
        "NZ": "New Zealand",
        "NI": "Nicaragua",
        "NE": "Niger",
        "NG": "Nigeria",
        "NU": "Niue",
        "NF": "Norfolk Island",
        "MK": "North Macedonia",
        "MP": "Northern Mariana Islands",
        "NO": "Norway",
        "OM": "Oman",
        "PK": "Pakistan",
        "PW": "Palau",
        "PS": "Palestine",
        "PA": "Panama",
        "PG": "Papua New Guinea",
        "PY": "Paraguay",
        "PE": "Peru",
        "PH": "Philippines",
        "PN": "Pitcairn",
        "PL": "Poland",
        "PT": "Portugal",
        "PR": "Puerto Rico",
        "QA": "Qatar",
        "RE": "Réunion",
        "RO": "Romania",
        "RU": "Russia",
        "RW": "Rwanda",
        "BL": "Saint Barthélemy",
        "SH": "Saint Helena",
        "KN": "Saint Kitts and Nevis",
        "LC": "Saint Lucia",
        "MF": "Saint Martin",
        "PM": "Saint Pierre and Miquelon",
        "VC": "Saint Vincent and the Grenadines",
        "WS": "Samoa",
        "SM": "San Marino",
        "ST": "Sao Tome and Principe",
        "SA": "Saudi Arabia",
        "SN": "Senegal",
        "RS": "Serbia",
        "SC": "Seychelles",
        "SL": "Sierra Leone",
        "SG": "Singapore",
        "SX": "Sint Maarten",
        "SK": "Slovakia",
        "SI": "Slovenia",
        "SB": "Solomon Islands",
        "SO": "Somalia",
        "ZA": "South Africa",
        "GS": "South Georgia and the South Sandwich Islands",
        "SS": "South Sudan",
        "ES": "Spain",
        "LK": "Sri Lanka",
        "SD": "Sudan",
        "SR": "Suriname",
        "SJ": "Svalbard and Jan Mayen",
        "SE": "Sweden",
        "CH": "Switzerland",
        "SY": "Syria",
        "TW": "Taiwan",
        "TJ": "Tajikistan",
        "TZ": "Tanzania",
        "TH": "Thailand",
        "TL": "Timor-Leste",
        "TG": "Togo",
        "TK": "Tokelau",
        "TO": "Tonga",
        "TT": "Trinidad and Tobago",
        "TN": "Tunisia",
        "TR": "Turkey",
        "TM": "Turkmenistan",
        "TC": "Turks and Caicos Islands",
        "TV": "Tuvalu",
        "UG": "Uganda",
        "UA": "Ukraine",
        "AE": "United Arab Emirates",
        "GB": "United Kingdom",
        "UK": "United Kingdom",  # Non-standard but commonly used
        "US": "United States",
        "UM": "United States Minor Outlying Islands",
        "UY": "Uruguay",
        "UZ": "Uzbekistan",
        "VU": "Vanuatu",
        "VE": "Venezuela",
        "VN": "Vietnam",
        "VG": "Virgin Islands (British)",
        "VI": "Virgin Islands (U.S.)",
        "WF": "Wallis and Futuna",
        "EH": "Western Sahara",
        "YE": "Yemen",
        "ZM": "Zambia",
        "ZW": "Zimbabwe",
    }

    # Process intelAgents and their discoveredEntities if they exist
    if alert_data and "intelAgents" in alert_data:
        for agent in alert_data["intelAgents"]:
            if "discoveredEntities" in agent:
                for entity in agent["discoveredEntities"]:
                    if entity.get("countryOfOrigin"):
                        country_code = entity["countryOfOrigin"]
                        entity["countryName"] = country_map.get(country_code, country_code)

    return alert_data


def _enrich_alert_timestamps(alert_data):
    """
    Format timestamps in alert data to user-friendly format.

    Args:
        alert_data (dict): Alert data containing timestamps

    Returns:
        dict: Alert data with formatted timestamps
    """
    # Format main alert timestamp
    if alert_data.get("alertTimestamp"):
        alert_data["alertTimestamp"] = _format_timestamp(alert_data["alertTimestamp"])

    return alert_data


def _enrich_vulnerability_cvss_scores(alert_data):
    """
    Enrich vulnerability metadata with CVSS scores from discoveredEntities when missing.

    Args:
        alert_data (dict): Alert data containing metadata and intelAgents

    Returns:
        dict: Alert data with enriched vulnerability CVSS scores
    """
    # Check if we have the necessary data structures
    if not alert_data.get("metadata", []):
        return alert_data
    if not alert_data.get("metadata", {})[0].get("cyber", {}).get("vulnerabilities"):
        return alert_data

    vulnerabilities = alert_data["metadata"][0]["cyber"]["vulnerabilities"]
    discovered_entities = []

    # Extract all discovered entities from intel agents
    if alert_data.get("intelAgents"):
        for agent in alert_data["intelAgents"]:
            if agent.get("discoveredEntities"):
                discovered_entities.extend(agent["discoveredEntities"])

    # Create a lookup dictionary for discovered entities by name
    entity_lookup = {}
    for entity in discovered_entities:
        if entity.get("name") and entity.get("cvss"):
            entity_lookup[entity["name"]] = entity["cvss"]

    # Enrich vulnerabilities with CVSS scores from discovered entities
    for vuln in vulnerabilities:
        # If CVSS score is missing or empty in metadata
        if not vuln.get("cvss"):
            vuln_id = vuln.get("id")
            if vuln_id and vuln_id in entity_lookup:
                # Use CVSS score from discovered entities
                vuln["cvss"] = entity_lookup[vuln_id]
                vuln["cvss_source"] = "discoveredEntities"  # Track the source
            else:
                # Ensure we have a fallback value
                vuln["cvss"] = None
                vuln["cvss_source"] = "none"
        else:
            vuln["cvss_source"] = "metadata"

    return alert_data


def _get_alerts_result(provides, result):
    ctx_result = {}
    param = result.get_param()
    data = result.get_data()
    status = result.get_status()
    summary = result.get_summary()

    ctx_result["status"] = status
    ctx_result["param"] = param
    ctx_result["summary"] = summary
    if data:
        if provides == "get alert details":
            # Enrich each alert with CVSS score fallback logic
            enriched_data = []
            for alert_data in data:
                enrich_alert_cvss = _enrich_vulnerability_cvss_scores(alert_data)
                enrich_alert_country = _enrich_entity_country_names(enrich_alert_cvss)
                enrich_alert_timestamp = _enrich_alert_timestamps(enrich_alert_country)
                enriched_data.append(enrich_alert_timestamp)
            ctx_result["data"] = enriched_data
        else:
            ctx_result["data"] = data

    return ctx_result


def _get_api_version_from_results(all_app_runs):
    """Extract API version from action results or summary."""
    for summary, action_results in all_app_runs:
        for result in action_results:
            # Try to get API version from summary first
            result_summary = result.get_summary()
            if result_summary and "api_version_used" in result_summary:
                return result_summary["api_version_used"]

            # Try to get API version from data
            data = result.get_data()
            if data:
                for data_item in data:
                    if isinstance(data_item, dict) and "api_version" in data_item:
                        return data_item["api_version"]

    # Default to v3 if not found
    return "v3"


def _get_template_for_action(action_name, api_version):
    """Get the appropriate HTML template based on action and API version."""
    template_mapping = {
        "get alerts": {"v3": "dataminrpulse_get_alerts.html", "v4": "dataminrpulse_get_alerts_v4.html"},
        "get lists": {"v3": "dataminrpulse_get_lists.html", "v4": "dataminrpulse_get_lists_v4.html"},
        "get alert details": {"v3": "dataminrpulse_get_alert_details_v4.html", "v4": "dataminrpulse_get_alert_details_v4.html"},
    }

    # Get template for the specific version, fallback to v3 if not found
    action_templates = template_mapping.get(action_name, {})
    return action_templates.get(api_version, action_templates.get("v3"))


def display_alerts(provides, all_app_runs, context):
    context["results"] = results = []

    for summary, action_results in all_app_runs:
        for result in action_results:
            get_alerts_result = _get_alerts_result(provides, result)
            if not get_alerts_result:
                continue
            results.append(get_alerts_result)

    # Get API version from results
    api_version = _get_api_version_from_results(all_app_runs)

    # Add API version to context for use in templates
    context["api_version"] = api_version

    # Return appropriate template based on action and API version
    return _get_template_for_action(provides, api_version)
