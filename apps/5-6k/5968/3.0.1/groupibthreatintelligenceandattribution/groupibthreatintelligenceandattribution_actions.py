# Copyright (c) 2026 Splunk Inc.
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
"""Action handlers for Group-IB Threat Intelligence Connector."""

import phantom.app as phantom
from dateparser import parse
from phantom.action_result import ActionResult

from groupibthreatintelligenceandattribution_utils import get_first_value, get_joined_values


def handle_whois_ip(param, connector):
    """Handle WHOIS IP lookup action."""
    action_result = connector.add_action_result(ActionResult(dict(param)))

    ip = param.get("ip")
    if not ip:
        action_result.set_status(phantom.APP_ERROR, "IP parameter is required")
        return action_result.get_status()

    connector.save_progress(f"Querying WHOIS data for IP: {ip}")

    try:
        response = connector._gib_tia_connector.graph_ip_search(ip)
        whois_data = {}

        if response and isinstance(response, dict):
            item = response

            # Extract top-level fields
            external_id = item.get("id")
            ip_range_start = item.get("start")
            ip_range_end = item.get("end")
            provider = item.get("provider")
            top_level_created = item.get("createdAt")
            top_level_updated = item.get("updatedAt")

            # Extract from whoisSummary
            whois_summary = item.get("whoisSummary", {})
            asn = whois_summary.get("asn") if whois_summary else None
            country = whois_summary.get("country") if whois_summary else None
            isp = whois_summary.get("isp") if whois_summary else None
            netname = whois_summary.get("netname") if whois_summary else None

            # Process whoisHistory for detailed data
            status = None
            org_name = None
            address = None
            abuse_poc = None
            abuse_contact_email = None
            abuse_contact_phone = None
            created_at = top_level_created
            updated_at = top_level_updated

            whois_history = item.get("whoisHistory", [])
            if whois_history and isinstance(whois_history, list):
                oldest_date = None
                most_recent_date = None
                oldest_first_seen = None
                most_recent_entry = None
                most_recent_last_seen = None

                # Find oldest firstSeen and most recent lastSeen
                for history_entry in whois_history:
                    if not history_entry or not isinstance(history_entry, dict):
                        continue

                    first_seen = history_entry.get("first_seen")
                    if first_seen:
                        try:
                            parsed_date = parse(first_seen)
                            if parsed_date and (oldest_date is None or parsed_date < oldest_date):
                                oldest_date = parsed_date
                                oldest_first_seen = first_seen
                        except Exception:
                            if oldest_first_seen is None:
                                oldest_first_seen = first_seen

                    last_seen = history_entry.get("last_seen")
                    if last_seen:
                        try:
                            parsed_date = parse(last_seen)
                            if parsed_date and (most_recent_date is None or parsed_date > most_recent_date):
                                most_recent_date = parsed_date
                                most_recent_entry = history_entry
                                most_recent_last_seen = last_seen
                        except Exception:
                            if most_recent_entry is None:
                                most_recent_entry = history_entry
                                most_recent_last_seen = last_seen

                history_entry = most_recent_entry if most_recent_entry else whois_history[0]
                created_at = top_level_created or oldest_first_seen
                updated_at = top_level_updated or most_recent_last_seen

                if history_entry and isinstance(history_entry, dict):
                    data_array = history_entry.get("data", [])

                    # Find inetnum entry (most relevant for IP info)
                    inetnum_data = None
                    for data_item in data_array:
                        if data_item and isinstance(data_item, dict) and data_item.get("type") == "inetnum":
                            inetnum_data = data_item
                            break

                    data_item = inetnum_data or (data_array[0] if data_array else None)

                    if data_item and isinstance(data_item, dict):
                        parsed = data_item.get("parsed", [])
                        if parsed and isinstance(parsed, list):
                            for parsed_item in parsed:
                                if not parsed_item or not isinstance(parsed_item, dict):
                                    continue
                                field = parsed_item.get("field")
                                value = parsed_item.get("value", [])

                                if field == "org-name" and value:
                                    org_name = value[0] if isinstance(value, list) else value
                                elif field == "netname" and not netname and value:
                                    netname = value[0] if isinstance(value, list) else value
                                elif field == "status" and value:
                                    status = value[0] if isinstance(value, list) else value

                    # Extract address and abuse contact info
                    for data_item in data_array:
                        if not data_item or not isinstance(data_item, dict):
                            continue
                        parsed = data_item.get("parsed", [])
                        if not parsed:
                            continue

                        for parsed_item in parsed:
                            if not parsed_item or not isinstance(parsed_item, dict):
                                continue
                            field = parsed_item.get("field")
                            value = parsed_item.get("value", [])

                            if field == "address" and value:
                                address = ", ".join([str(addr) for addr in value if addr])
                            elif field == "abuse-c" and value and not abuse_poc:
                                abuse_poc = value[0] if isinstance(value, list) else value
                            elif field == "parsed_emails" and value and not abuse_contact_email:
                                abuse_contact_email = value[0] if isinstance(value, list) else value
                            elif field == "phone" and value and not abuse_contact_phone:
                                abuse_contact_phone = value[0] if isinstance(value, list) else value

                        if address and abuse_poc and abuse_contact_email and abuse_contact_phone:
                            break

            # Build response in order
            if external_id:
                whois_data["externalId"] = external_id
            if ip_range_start:
                whois_data["ipRangeStart"] = ip_range_start
            if ip_range_end:
                whois_data["ipRangeEnd"] = ip_range_end
            if created_at:
                whois_data["firstSeen"] = created_at
            if updated_at:
                whois_data["lastSeen"] = updated_at
            if asn:
                whois_data["asn"] = asn
            if status:
                whois_data["status"] = status
            if netname:
                whois_data["netname"] = netname
            if country:
                whois_data["country"] = country
            if address:
                whois_data["address"] = address
            if abuse_poc:
                whois_data["abuse-c"] = abuse_poc
            if abuse_contact_email:
                whois_data["e-mail"] = abuse_contact_email
            if abuse_contact_phone:
                whois_data["phone"] = abuse_contact_phone
            if provider:
                whois_data["provider"] = provider
            if isp:
                whois_data["isp"] = isp
            if org_name:
                whois_data["orgName"] = org_name

        if whois_data:
            action_result.add_data(whois_data)
            action_result.update_summary({"total_objects": 1, "total_objects_successful": 1})
            action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved WHOIS data for IP: {ip}")
        else:
            action_result.set_status(phantom.APP_SUCCESS, f"No WHOIS data found for IP: {ip}")

    except Exception as e:
        error_message = connector._get_error_message_from_exception(e)
        connector.debug_print(f"Error querying WHOIS data: {error_message}")
        action_result.set_status(phantom.APP_ERROR, f"Error querying WHOIS data: {error_message}")

    return action_result.get_status()


def handle_whois_domain(param, connector):
    """Handle WHOIS domain lookup action."""
    action_result = connector.add_action_result(ActionResult(dict(param)))
    domain = param.get("domain")

    if not domain:
        action_result.set_status(phantom.APP_ERROR, "Domain parameter is required")
        return action_result.get_status()

    connector.save_progress(f"Querying WHOIS data for domain: {domain}")

    try:
        response = connector._gib_tia_connector.graph_domain_search(domain)

        if not response or not isinstance(response, dict):
            return action_result.set_status(phantom.APP_ERROR, f"Invalid API response for domain: {domain}")

        top_level_created = response.get("created_at")
        whois_list = response.get("whois", [])

        if not whois_list:
            return action_result.set_status(phantom.APP_SUCCESS, f"No WHOIS data found for domain: {domain}")

        # Find level 2 entry (most detailed), or use last entry
        whois_entry = None
        for entry in whois_list:
            if entry.get("level", 0) == 2:
                whois_entry = entry
                break
        if whois_entry is None:
            whois_entry = whois_list[-1] if whois_list else {}

        # Get data from values dict or parsed array
        values_data = whois_entry.get("values", {})
        parsed_array = whois_entry.get("parsed", [])

        parsed_dict = {}
        if parsed_array and isinstance(parsed_array, list):
            for item in parsed_array:
                if item and isinstance(item, dict):
                    field_name = item.get("field", "")
                    field_value = item.get("value", [])
                    if field_name:
                        parsed_dict[field_name.lower()] = field_value

        data_source = values_data if values_data and any(values_data.values()) else parsed_dict
        creation_date = get_first_value(data_source, "creationDate") or top_level_created

        domain_data = {
            "creationDate": creation_date,
            "updatedDate": get_first_value(data_source, "updatedDate"),
            "expirationDate": get_first_value(data_source, "expirationDate"),
            "registrar": get_first_value(data_source, "registrar"),
            "whoisServer": get_first_value(data_source, "whoisServer"),
            "registrantName": get_first_value(data_source, "name"),
            "registrantOrg": get_first_value(data_source, "org"),
            "registrantCountry": get_first_value(data_source, "country"),
            "registrantState": get_first_value(data_source, "state"),
            "registrantCity": get_first_value(data_source, "city"),
            "registrantAddress": get_joined_values(data_source, "address"),
            "registrantZipcode": get_first_value(data_source, "zipcode"),
            "registrantPhone": get_joined_values(data_source, "phone"),
            "domainStatus": get_joined_values(data_source, "status"),
            "nameServers": get_joined_values(data_source, "nameServers"),
        }

        has_data = any(
            [
                domain_data.get("creationDate"),
                domain_data.get("registrar"),
                domain_data.get("expirationDate"),
                domain_data.get("domainStatus"),
                domain_data.get("nameServers"),
            ]
        )

        if has_data:
            action_result.add_data(domain_data)
            action_result.update_summary(
                {"Domain": domain, "Registrar": domain_data.get("registrar"), "Creation Date": domain_data.get("creationDate")}
            )
            action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved WHOIS data for domain: {domain}")
        else:
            action_result.set_status(phantom.APP_SUCCESS, f"WHOIS data found but key fields empty for domain: {domain}")

    except Exception as e:
        error_message = connector._get_error_message_from_exception(e)
        connector.debug_print(f"Error querying WHOIS data for domain: {domain}", e)
        action_result.set_status(phantom.APP_ERROR, f"Error querying WHOIS data: {error_message}")

    return action_result.get_status()


def handle_ip_scoring(param, connector):
    """Handle IP scoring action."""
    action_result = connector.add_action_result(ActionResult(dict(param)))

    ip = param.get("ip")
    if not ip:
        action_result.set_status(phantom.APP_ERROR, "IP parameter is required")
        return action_result.get_status()

    connector.save_progress(f"Querying IP score for: {ip}")

    try:
        response = connector._gib_tia_connector.scoring(ip)

        if not response or not isinstance(response, dict):
            action_result.set_status(phantom.APP_ERROR, f"Invalid API response for IP: {ip}")
            return action_result.get_status()

        items = response.get("items", {})

        if not items:
            action_result.set_status(phantom.APP_SUCCESS, f"No scoring data found for IP: {ip}")
            return action_result.get_status()

        # Get the scoring data for the requested IP
        ip_data = items.get(ip, {})

        if not ip_data:
            # Try to get first item if exact IP key not found
            first_key = next(iter(items), None)
            if first_key:
                ip_data = items[first_key]

        if ip_data:
            scoring_result = {"ip": ip_data.get("ip", ip), "score": ip_data.get("riskScore", 0)}
            action_result.add_data(scoring_result)
            action_result.set_status(phantom.APP_SUCCESS, f"Successfully retrieved score for IP: {ip}")
        else:
            action_result.set_status(phantom.APP_SUCCESS, f"No scoring data found for IP: {ip}")

    except Exception as e:
        error_message = connector._get_error_message_from_exception(e)
        connector.debug_print(f"Error querying IP score: {error_message}")
        action_result.set_status(phantom.APP_ERROR, f"Error querying IP score: {error_message}")

    return action_result.get_status()
