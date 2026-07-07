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
"""Artifact parser for Group-IB Threat Intelligence Connector."""

from groupibthreatintelligenceandattribution_consts import *
from groupibthreatintelligenceandattribution_utils import (
    create_artifact,
    determine_hash_type,
    extract_cnc_fields,
    extract_ipv4_fields,
    extract_names_from_array,
    get_items_from_chunk,
    get_nested_value,
    join_list_values,
    mask_password,
    normalize_to_list,
    safe_get_list,
)


def _process_suspicious_ip_collection(items, artifacts_list, collection_name, debug_print=None):
    """Process suspicious_ip/* collections with common logic."""
    array_field = SUSPICIOUS_IP_ARRAY_FIELDS.get(collection_name)

    # Map collection to the human-readable field name for array fields
    array_field_names = {
        "suspicious_ip/scanner": "Categories",
        "suspicious_ip/tor_node": "Source",
        "suspicious_ip/open_proxy": "Sources",
        "suspicious_ip/socks_proxy": "Source",
        "suspicious_ip/vpn": "Sources",
    }

    for i, item in enumerate(items):
        if not item or i >= len(artifacts_list) or not artifacts_list[i]:
            continue

        base_artifact = artifacts_list[i][0] if artifacts_list[i] else None
        if not base_artifact:
            continue

        base_cef = base_artifact.get("cef", {})
        if not base_cef:
            base_cef = {}
            base_artifact["cef"] = base_cef

        # Handle array field (sources, categories, etc.)
        if array_field:
            array_data = safe_get_list(item, array_field)
            if array_data:
                joined_values = join_list_values(array_data)
                if joined_values:
                    # Use human-readable field name
                    field_name = array_field_names.get(collection_name, array_field.title())
                    base_cef[field_name] = joined_values

        # Extract IP with fallback to id
        if not base_cef.get("destinationAddress"):
            ip = get_nested_value(item, "ipv4.ip")
            if ip:
                base_cef["destinationAddress"] = ip
            else:
                item_id = item.get("id")
                if item_id:
                    base_cef["destinationAddress"] = item_id

        base_artifact["cef"] = base_cef


def parse_artifacts(chunk, collection_info, collection_name, debug_print=None, filters=None):
    """Parse artifacts from chunk data based on collection type."""
    if debug_print is None:

        def debug_print(msg):
            pass

    artifact_keys_list = collection_info.get("artifacts", [])
    artifacts_list = chunk.bulk_parse_portion([{**BASE_MAPPING_ARTIFACT, **a} for a in artifact_keys_list])

    # Ensure artifacts_list is always a list (bulk_parse_portion may return None)
    if artifacts_list is None:
        artifacts_list = []

    if collection_name == "ioc/common":
        items = get_items_from_chunk(chunk)

        while len(artifacts_list) < len(items):
            artifacts_list.append([])

        for i, item in enumerate(items):
            if not item:
                continue

            base_start_time = item.get("dateFirstSeen") or None
            base_end_time = item.get("dateLastSeen") or None

            base_cef = {**BASE_CEF_LIST}
            if item.get("id"):
                base_cef["*id"] = item.get("id")

            # Extract malware and threat names using utility
            malware_str = extract_names_from_array(item.get("malwareList", []))
            if malware_str:
                base_cef["malwareName"] = malware_str

            threat_str = extract_names_from_array(item.get("threatList", []))
            if threat_str:
                base_cef["threatName"] = threat_str

            ioc_type = item.get("type", "network")
            artifact_type = "*file" if ioc_type == "file" else "*network"

            # Normalize IOC lists using utility
            ip_list = normalize_to_list(item.get("ip"))
            url_list = normalize_to_list(item.get("url"))
            domain_list = normalize_to_list(item.get("domain"))
            hash_list = normalize_to_list(item.get("hash"))

            has_threat_or_malware = bool(base_cef.get("threatName") or base_cef.get("malwareName"))
            non_hash_severity = "high" if has_threat_or_malware else "medium"

            new_artifacts = []

            # Create IP artifacts
            for ip in filter(None, ip_list):
                ip_cef = {**base_cef, "destinationAddress": ip}
                new_artifacts.append(
                    create_artifact(
                        f"IP: {ip}",
                        ip_cef,
                        artifact_type,
                        "gib_indicator",
                        base_start_time,
                        base_end_time,
                        non_hash_severity,
                        first_seen=base_start_time,
                    )
                )

            # Create URL artifacts
            for url in filter(None, url_list):
                url_cef = {**base_cef, "requestUrl": url}
                new_artifacts.append(
                    create_artifact(
                        f"URL: {url}",
                        url_cef,
                        artifact_type,
                        "gib_indicator",
                        base_start_time,
                        base_end_time,
                        non_hash_severity,
                        first_seen=base_start_time,
                        last_fetch=item.get("seqUpdate"),
                    )
                )

            # Create Domain artifacts
            for domain in filter(None, domain_list):
                domain_cef = {**base_cef, "destinationDnsDomain": domain}
                new_artifacts.append(
                    create_artifact(
                        f"Domain: {domain}",
                        domain_cef,
                        artifact_type,
                        "gib_indicator",
                        base_start_time,
                        base_end_time,
                        non_hash_severity,
                        first_seen=base_start_time,
                        last_fetch=item.get("seqUpdate"),
                    )
                )

            # Create Hash artifacts
            for hash_value in filter(None, hash_list):
                hash_cef = base_cef.copy()
                cef_field, hash_type = determine_hash_type(hash_value)
                if cef_field:
                    hash_cef[cef_field] = hash_value
                new_artifacts.append(
                    create_artifact(
                        f"Hash ({hash_type}): {hash_value} ",
                        hash_cef,
                        "*file",
                        "gib_indicator",
                        base_start_time,
                        severity="high",
                        first_seen=base_start_time,
                        last_seen=base_end_time,
                        last_fetch=item.get("seqUpdate"),
                    )
                )

            artifacts_list[i] = new_artifacts

    elif collection_name == "compromised/account_group":
        items = get_items_from_chunk(chunk)

        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list) or not artifacts_list[i]:
                continue

            events = safe_get_list(item, "events")

            # Get main "*Compromised account" artifact
            compromised_account_artifact = None
            base_start_time = None
            base_end_time = None

            if artifacts_list[i]:
                first_artifact = artifacts_list[i][0]
                if first_artifact and first_artifact.get("name") == "*Compromised account":
                    compromised_account_artifact = first_artifact
                else:
                    for artifact in artifacts_list[i]:
                        if artifact and artifact.get("name") == "*Compromised account":
                            compromised_account_artifact = artifact
                            break
                    if not compromised_account_artifact and first_artifact:
                        compromised_account_artifact = first_artifact

                if compromised_account_artifact:
                    base_start_time = compromised_account_artifact.get("start_time")
                    base_end_time = compromised_account_artifact.get("end_time")

            # Check for CNC data in events
            cnc_data = None
            for event in events:
                if event and isinstance(event, dict):
                    event_cnc = event.get("cnc")
                    if event_cnc and isinstance(event_cnc, dict):
                        if event_cnc.get("domain") or event_cnc.get("url") or get_nested_value(event_cnc, "ipv4.ip"):
                            cnc_data = event_cnc
                            break

            # Add CNC fields to main artifact
            if cnc_data and compromised_account_artifact:
                compromised_cef = compromised_account_artifact.get("cef") or {**BASE_CEF_LIST}
                if cnc_data.get("domain"):
                    compromised_cef["sourceHostName"] = cnc_data.get("domain")
                if cnc_data.get("url"):
                    compromised_cef["requestUrl"] = cnc_data.get("url")
                cnc_ipv4 = cnc_data.get("ipv4")
                if cnc_ipv4 and isinstance(cnc_ipv4, dict):
                    if cnc_ipv4.get("ip"):
                        compromised_cef["sourceAddress"] = cnc_ipv4.get("ip")
                    extract_ipv4_fields(cnc_ipv4, compromised_cef)
                compromised_account_artifact["cef"] = compromised_cef

            # Set label based on CNC data presence
            # Note: Password masking is handled by universal handler at end of parse_artifacts
            if compromised_account_artifact:
                compromised_account_artifact["label"] = "gib_indicator" if cnc_data else "gib_info"

            # Process latest event
            event_artifacts = []
            if events:
                latest_event = events[-1]
                if latest_event and isinstance(latest_event, dict):
                    client_ipv4 = get_nested_value(latest_event, "client.ipv4") or {}
                    source_data = latest_event.get("source") or {}
                    malware_data = latest_event.get("malware") or {}
                    threat_actor_data = latest_event.get("threatActor") or {}

                    # Create Source&Details artifact
                    source_details_cef = {**BASE_CEF_LIST}
                    if item.get("id"):
                        source_details_cef["externalId"] = item.get("id")

                    if client_ipv4.get("ip"):
                        source_details_cef["Victim's IP"] = client_ipv4.get("ip")
                    extract_ipv4_fields(client_ipv4, source_details_cef)

                    if latest_event.get("dateCompromised"):
                        source_details_cef["Compromised"] = latest_event.get("dateCompromised")
                    if source_data.get("id"):
                        source_details_cef["Source link"] = source_data.get("id")
                    if source_data.get("type"):
                        source_details_cef["Source type"] = source_data.get("type")
                    if source_data.get("idType"):
                        source_details_cef["Source"] = source_data.get("idType")
                    if malware_data.get("name"):
                        source_details_cef["Malware"] = malware_data.get("name")
                    if threat_actor_data.get("name"):
                        source_details_cef["Threat Actor"] = threat_actor_data.get("name")

                    # Add applied filters
                    if filters:
                        applied = [k for k in ["combolist", "unique", "probable_corporate_access"] if filters.get(k)]
                        if applied:
                            source_details_cef["Applied data filter"] = ", ".join(applied)

                    event_artifacts.append(
                        create_artifact("Source&Details", source_details_cef, start_time=base_start_time, end_time=base_end_time)
                    )

                    # Create Host information artifact if indexed data exists
                    indexed_data = get_nested_value(latest_event, "additionalData.indexed") or {}
                    if indexed_data and any(indexed_data.get(f) for f in HOST_INFO_FIELD_MAPPING.keys()):
                        host_info_cef = {**BASE_CEF_LIST}
                        if item.get("id"):
                            host_info_cef["externalId"] = item.get("id")

                        for src_field, dest_field in HOST_INFO_FIELD_MAPPING.items():
                            value = indexed_data.get(src_field)
                            if value:
                                host_info_cef[dest_field] = value

                        event_artifacts.append(
                            create_artifact("Host information structured", host_info_cef, start_time=base_start_time, end_time=base_end_time)
                        )

            # Build final artifacts list
            final_artifacts = []
            if compromised_account_artifact:
                final_artifacts.append(compromised_account_artifact)
            else:
                debug_print(f"Warning: '*Compromised account' artifact not found for item {item.get('id', 'unknown')}")
                if artifacts_list[i]:
                    final_artifacts.append(artifacts_list[i][0])

            final_artifacts.extend(event_artifacts)
            artifacts_list[i] = final_artifacts

    elif collection_name == "compromised/bank_card_group":
        items = get_items_from_chunk(chunk)
        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list):
                continue
            if artifacts_list[i] is None:
                artifacts_list[i] = []
            additional_artifacts = []

            # Extract names from arrays using utility
            malware_str = extract_names_from_array(item.get("malware", []))
            ta_str = extract_names_from_array(item.get("threatActor", []))
            source_types = [s.get("type") for s in item.get("source", []) if s and s.get("type")]
            source_str = ", ".join(set(source_types)) if source_types else None

            # Update main artifact with array data
            if artifacts_list[i] and len(artifacts_list[i]) > 0:
                main_artifact = artifacts_list[i][0]
                if main_artifact:
                    main_cef = main_artifact.get("cef", {})
                    if malware_str:
                        main_cef["Malware"] = malware_str
                    if ta_str:
                        main_cef["Threat Actor"] = ta_str
                    if source_str:
                        main_cef["Source Type"] = source_str

            # Process events array
            for event in item.get("events", []):
                if not event:
                    continue

                event_card = event.get("cardInfo") or {}
                event_owner = event.get("owner") or {}
                event_malware = event.get("malware") or {}
                event_ta = event.get("threatActor") or {}
                event_source = event.get("source") or {}

                cef = {
                    **BASE_CEF_LIST,
                    "externalId": event.get("id"),
                    "CVV": event_card.get("cvv"),
                    "Valid Thru": event_card.get("validThru"),
                    "Date Compromised": event.get("dateCompromised"),
                    "Date Detected": event.get("dateDetected"),
                    "Is Dump": event.get("isDump"),
                    "Is Expired": event.get("isExpired"),
                    "Owner Country": event_owner.get("countryCode"),
                    "Malware": event_malware.get("name"),
                    "Threat Actor": event_ta.get("name"),
                    "Threat Actor Is APT": event_ta.get("isAPT"),
                    "Source Type": event_source.get("type"),
                    "Source ID": event_source.get("id"),
                }

                # Add CNC fields using utility
                extract_cnc_fields(event.get("cnc"), cef)

                additional_artifacts.append(create_artifact("*Card event", cef))

            artifacts_list[i].extend(additional_artifacts)

    elif collection_name in SUSPICIOUS_IP_COLLECTIONS:
        items = get_items_from_chunk(chunk)
        _process_suspicious_ip_collection(items, artifacts_list, collection_name, debug_print)

    elif collection_name == "osi/public_leak":
        items = get_items_from_chunk(chunk)
        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list):
                continue
            if artifacts_list[i] is None:
                artifacts_list[i] = []
            additional_artifacts = []
            for link in filter(None, item.get("linkList", [])):
                cef = {
                    **BASE_CEF_LIST,
                    "Author": link.get("author"),
                    "Source": link.get("source"),
                    "Date Detected": link.get("dateDetected"),
                    "Date Published": link.get("datePublished"),
                    "fileHash": link.get("hash"),
                    "Link": link.get("link"),
                }
                additional_artifacts.append(create_artifact("*Link details", cef))
            artifacts_list[i].extend(additional_artifacts)

    elif collection_name == "osi/git_repository":
        items = get_items_from_chunk(chunk)
        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list):
                continue
            if artifacts_list[i] is None:
                artifacts_list[i] = []
            additional_artifacts = []

            # Process contributors
            for contributor in filter(None, item.get("contributors", [])):
                cef = {
                    **BASE_CEF_LIST,
                    "Author Email": contributor.get("authorEmail"),
                    "Author Name": contributor.get("authorName"),
                }
                additional_artifacts.append(create_artifact("*Contributor", cef))

            # Process files
            for file_info in filter(None, item.get("files", [])):
                file_eval = file_info.get("evaluation") or {}
                matches_type = file_info.get("matchesType", [])

                cef = {
                    **BASE_CEF_LIST,
                    "externalId": file_info.get("id"),
                    "File Name": file_info.get("name"),
                    "File URL": file_info.get("url"),
                    "Date Created": file_info.get("dateCreated"),
                    "Date Detected": file_info.get("dateDetected"),
                    "Matches Type": ", ".join(matches_type) if matches_type else None,
                    "Severity": file_eval.get("severity"),
                    "Credibility": file_eval.get("credibility"),
                    "Reliability": file_eval.get("reliability"),
                }
                additional_artifacts.append(create_artifact("*File leak", cef))

                # Process revisions for each file
                for revision in filter(None, file_info.get("revisions", [])):
                    info = revision.get("info") or {}
                    rev_cef = {
                        **BASE_CEF_LIST,
                        "Author Email": info.get("authorEmail"),
                        "Author Name": info.get("authorName"),
                        "Revision Hash": revision.get("hash"),
                        "Timestamp": info.get("timestamp"),
                    }
                    additional_artifacts.append(create_artifact("*Revision details", rev_cef))

            artifacts_list[i].extend(additional_artifacts)

    elif collection_name == "malware/config":
        items = get_items_from_chunk(chunk)
        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list):
                continue
            if artifacts_list[i] is None:
                artifacts_list[i] = []
            additional_artifacts = []

            # Process file array
            for file_info in filter(None, item.get("file", [])):
                cef = {
                    **BASE_CEF_LIST,
                    "File Name": file_info.get("name"),
                    "fileHashMd5": file_info.get("md5"),
                    "fileHashSha1": file_info.get("sha1"),
                    "fileHashSha256": file_info.get("sha256"),
                    "Timestamp": file_info.get("timestamp"),
                }
                additional_artifacts.append(create_artifact("*File details", cef, "*file", "gib_indicator"))

            # Process IP list
            for ip in filter(None, item.get("ipList", [])):
                cef = {**BASE_CEF_LIST, "destinationAddress": ip}
                additional_artifacts.append(create_artifact(f"IP: {ip}", cef, "*network", "gib_indicator"))

            # Process domain list
            for domain in filter(None, item.get("domainList", [])):
                cef = {**BASE_CEF_LIST, "destinationDnsDomain": domain}
                additional_artifacts.append(create_artifact(f"Domain: {domain}", cef, "*network", "gib_indicator"))

            artifacts_list[i].extend(additional_artifacts)

    elif collection_name == "attacks/phishing_group":
        items = get_items_from_chunk(chunk)
        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list):
                continue
            if artifacts_list[i] is None:
                artifacts_list[i] = []
            additional_artifacts = []

            # Process objective and source arrays
            objective_str = join_list_values(item.get("objective", []))
            source_str = join_list_values(item.get("source", []))

            # Add to main artifact if present
            if artifacts_list[i] and len(artifacts_list[i]) > 0:
                main_artifact = artifacts_list[i][0]
                if main_artifact:
                    main_cef = main_artifact.get("cef", {})
                    if objective_str:
                        main_cef["Objective"] = objective_str
                    if source_str:
                        main_cef["Sources"] = source_str

            # Process IP array
            for ip_info in filter(None, item.get("ip", [])):
                ip_addr = ip_info.get("ip") if isinstance(ip_info, dict) else ip_info
                cef = {**BASE_CEF_LIST, "destinationAddress": ip_addr}
                if isinstance(ip_info, dict):
                    extract_ipv4_fields(ip_info, cef)
                additional_artifacts.append(create_artifact(f"IP: {ip_addr}", cef, "*network", "gib_indicator"))

            # Process phishing array (individual phishing URLs)
            for phishing in filter(None, item.get("phishing", [])):
                phishing_ip = phishing.get("ip") or {}
                phishing_date = phishing.get("date") or {}

                cef = {
                    **BASE_CEF_LIST,
                    "externalId": phishing.get("id"),
                    "requestUrl": phishing.get("url"),
                    "Status": phishing.get("status"),
                    "Title": phishing.get("title"),
                    "Date Detected": phishing_date.get("detected"),
                    "Date Blocked": phishing_date.get("blocked"),
                }
                extract_ipv4_fields(phishing_ip, cef)

                phishing_objectives = phishing.get("objective", [])
                if phishing_objectives:
                    cef["Objective"] = ", ".join(phishing_objectives)

                additional_artifacts.append(create_artifact("*Phishing URL", cef, "*network", "gib_indicator"))

            artifacts_list[i].extend(additional_artifacts)

    elif collection_name == "attacks/phishing_kit":
        items = get_items_from_chunk(chunk)
        for i, item in enumerate(items):
            if not item or i >= len(artifacts_list):
                continue

            # Ensure artifacts_list[i] is a list (not None)
            if artifacts_list[i] is None:
                artifacts_list[i] = []

            additional_artifacts = []

            # Process arrays and join values
            source_str = join_list_values(item.get("source", []))
            target_brand_str = join_list_values(item.get("targetBrand", []))
            emails_str = join_list_values(item.get("emails", []))

            # Update Additional info artifact with array data
            if artifacts_list[i] and len(artifacts_list[i]) > 1:
                additional_info = artifacts_list[i][1]
                if additional_info and additional_info.get("name") == "*Additional info":
                    add_cef = additional_info.get("cef", {})
                    if source_str:
                        add_cef["Source"] = source_str
                    if target_brand_str:
                        add_cef["Target Brand"] = target_brand_str
                    if emails_str:
                        add_cef["Emails"] = emails_str

            # Process downloadedFrom array
            # Use "or []" because item.get() returns None if key exists with None value
            for download in filter(None, item.get("downloadedFrom") or []):
                cef = {
                    **BASE_CEF_LIST,
                    "requestUrl": download.get("url"),
                    "sourceHostName": download.get("domain"),
                    "Phishing URL": download.get("phishingUrl"),
                    "File Name": download.get("fileName"),
                    "Date": download.get("date"),
                }
                additional_artifacts.append(create_artifact("*Download source", cef, "*network", "gib_indicator"))

            # Process variables array (limit values to prevent oversized data)
            # Use "or []" because item.get("variables", []) returns None if key exists with None value
            for var in filter(None, item.get("variables") or []):
                values = var.get("values", [])
                # Ensure values are strings and limit total length to prevent issues
                if values and isinstance(values, list):
                    str_values = [str(v)[:500] for v in values if v]  # Truncate long values
                    values_str = "; ".join(str_values[:20]) if str_values else None  # Limit to 20 items
                    if len(str_values) > 20:
                        values_str += f"; ... (+{len(str_values) - 20} more)"
                else:
                    values_str = None
                cef = {
                    **BASE_CEF_LIST,
                    "Variable Type": var.get("type"),
                    "File Path": var.get("filePath"),
                    "Values": values_str,
                }
                additional_artifacts.append(create_artifact("*Variable", cef))

            artifacts_list[i].extend(additional_artifacts)

    # Universal post-processing - applies to ALL collections
    for item_artifacts in artifacts_list:
        if not item_artifacts:
            continue
        for artifact in item_artifacts:
            if artifact and artifact.get("cef"):
                cef = artifact["cef"]

                # Normalize array values to strings (e.g., email: ["a@b.com"] -> "a@b.com")
                for key, value in list(cef.items()):
                    if isinstance(value, list):
                        if len(value) == 1:
                            cef[key] = value[0]
                        elif len(value) > 1:
                            cef[key] = ", ".join(str(v) for v in value if v)
                        else:
                            cef[key] = None

                # Mask any "Password" field
                if "Password" in cef:
                    raw_password = cef.pop("Password", None)
                    masked = mask_password(raw_password)
                    if masked:
                        cef["Password (masked)"] = masked

    return artifacts_list
