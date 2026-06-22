"""Parameterized Cypher query builders for Whisper enrichment.

Constructs Cypher queries for domain enrichment, IP enrichment, threat
intelligence, CNAME chain, and nameserver lookups. All queries use
parameterized inputs to prevent Cypher injection.

Result parsers have been extracted to whisper_enrichment_parsers.py.
"""

from __future__ import annotations

import re


def build_domain_resolve_query() -> str:
    """Build query to resolve a hostname to its IP addresses.

    This is the first stage of domain enrichment, limited to 1 hop
    to stay within the API depth limit.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return "MATCH (h:HOSTNAME {name: $hostname})-[:RESOLVES_TO]->(ip:IPV4) RETURN ip.name AS ip LIMIT 50"


def build_domain_query() -> str:
    """Build the domain infrastructure enrichment query.

    Uses the IP enrichment path (ANNOUNCED_BY) anchored on an IP address
    resolved from the hostname. The caller must first resolve the hostname
    to IPs using build_domain_resolve_query(), then call this query for
    each IP. This two-stage approach respects the 2-hop API depth limit.

    Returns inline threat properties from the IPV4 node to reduce the need
    for separate explain() calls.

    Returns:
        Cypher query string with $ip parameter (not $hostname).
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})-[:ANNOUNCED_BY]->(ap)-[:ROUTES]->(va:ASN) "
        "RETURN ip.name AS ip, ap.name AS prefix, va.name AS asn, "
        "ip.threatScore AS threat_score, ip.threatLevel AS threat_level, "
        "ip.isThreat AS is_threat, ip.isTor AS is_tor, ip.isC2 AS is_c2, "
        "ip.isMalware AS is_malware, ip.isPhishing AS is_phishing, ip.isSpam AS is_spam, "
        "ip.isBruteforce AS is_bruteforce, ip.isScanner AS is_scanner, "
        "ip.isBlacklist AS is_blacklist, ip.isProxy AS is_proxy, ip.isVpn AS is_vpn, "
        "ip.isAnonymizer AS is_anonymizer, ip.isWhitelist AS is_whitelist, "
        "ip.threatSources AS threat_sources_count, "
        "ip.threatFirstSeen AS threat_first_seen, ip.threatLastSeen AS threat_last_seen "
        "LIMIT 1"
    )


def build_ip_query() -> str:
    """Build the IP infrastructure enrichment query.

    Uses the virtual ANNOUNCED_BY path to reach the ASN, then re-anchors
    on the physical ASN node via WITH to access HAS_NAME and HAS_COUNTRY
    edges (virtual ASN nodes from ANNOUNCED_PREFIX lack these edges).

    Returns inline threat properties from the IPV4 and ASN nodes to reduce
    the need for separate explain() calls.

    Returns:
        Cypher query string with $ip parameter.
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})-[:ANNOUNCED_BY]->(ap)-[:ROUTES]->(va:ASN) "
        "WITH ip, ap, va.name AS asn "
        "MATCH (a:ASN {name: asn})-[:HAS_NAME]->(n:ASN_NAME) "
        "MATCH (a)-[:HAS_COUNTRY]->(co:COUNTRY) "
        "OPTIONAL MATCH (ip)<-[:RESOLVES_TO]-(h:HOSTNAME) "
        "RETURN ip.name AS ip, ap.name AS prefix, a.name AS asn, n.name AS asn_name, "
        "co.name AS country, count(DISTINCT h) AS reverse_dns_count, count(DISTINCT h) AS cohost_count, "
        "ip.threatScore AS threat_score, ip.threatLevel AS threat_level, "
        "ip.isThreat AS is_threat, ip.isTor AS is_tor, ip.isC2 AS is_c2, "
        "ip.isMalware AS is_malware, ip.isPhishing AS is_phishing, ip.isSpam AS is_spam, "
        "ip.isBruteforce AS is_bruteforce, ip.isScanner AS is_scanner, "
        "ip.isBlacklist AS is_blacklist, ip.isProxy AS is_proxy, ip.isVpn AS is_vpn, "
        "ip.isAnonymizer AS is_anonymizer, ip.isWhitelist AS is_whitelist, "
        "ip.threatSources AS threat_sources_count, "
        "ip.threatFirstSeen AS threat_first_seen, ip.threatLastSeen AS threat_last_seen, "
        "a.overallThreatLevel AS asn_threat_level, "
        "a.threatScore AS asn_threat_score, a.maxThreatScore AS asn_max_threat_score, "
        "a.avgThreatScore AS asn_avg_threat_score, "
        "a.hasThreateningPrefixes AS asn_has_threatening_prefixes "
        "LIMIT 50"
    )


def build_cohost_count_query() -> str:
    """Build query to count hostnames co-hosted on the same IP.

    Returns the number of HOSTNAME nodes that resolve to the given IP
    address. Used for both IP and domain enrichment to populate
    ``cohost_count``, which feeds into co-hosting risk factors.

    Returns:
        Cypher query string with $ip parameter.
    """
    return "MATCH (ip:IPV4 {name: $ip})<-[:RESOLVES_TO]-(h:HOSTNAME) RETURN count(DISTINCT h) AS cohost_count LIMIT 1"


def build_asn_info_query() -> str:
    """Build query to get ASN name and country in a single call.

    Anchors on the physical ASN node to access HAS_NAME and HAS_COUNTRY edges.
    Uses OPTIONAL MATCH for country since not all ASNs have country data.

    Returns:
        Cypher query string with $asn parameter.
    """
    return (
        "MATCH (a:ASN {name: $asn})-[:HAS_NAME]->(n:ASN_NAME) "
        "OPTIONAL MATCH (a)-[:HAS_COUNTRY]->(co:COUNTRY) "
        "RETURN n.name AS asn_name, co.name AS country, "
        "a.overallThreatLevel AS asn_threat_level, "
        "a.threatScore AS asn_threat_score, a.maxThreatScore AS asn_max_threat_score, "
        "a.avgThreatScore AS asn_avg_threat_score, "
        "a.hasThreateningPrefixes AS asn_has_threatening_prefixes "
        "LIMIT 1"
    )


def build_cname_query() -> str:
    """Build the CNAME chain enrichment query.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH path = (h:HOSTNAME {name: $hostname})-[:ALIAS_OF*1..5]->(target:HOSTNAME) "
        "RETURN [n IN nodes(path) | n.name] AS cname_chain "
        "LIMIT 10"
    )


def build_nameserver_query(
    parameter_name: str = "hostname",
    return_alias: str = "nameserver",
    limit: int = 50,
) -> str:
    """Build a nameserver lookup query for a given hostname or domain.

    Both the enrichment pipeline (using ``$hostname``) and the baseline
    collection pipeline (using ``$domain``) query the same
    ``NAMESERVER_FOR`` relationship.  This shared builder lets each
    caller specify its own parameter name and return alias so a single
    implementation serves both use-cases.

    Args:
        parameter_name: Cypher parameter placeholder name (without ``$``).
            Defaults to ``"hostname"`` for enrichment; baseline passes
            ``"domain"``.
        return_alias: Column alias for the returned nameserver value.
            Defaults to ``"nameserver"`` for enrichment; baseline passes
            ``"value"``.
        limit: Maximum number of nameservers to return.

    Returns:
        Parameterized Cypher query string.

    Raises:
        ValueError: If ``parameter_name`` or ``return_alias`` contain
            non-alphanumeric characters (defense-in-depth against
            Cypher injection).
    """

    if not re.fullmatch(r"[a-zA-Z_]\w*", parameter_name):
        raise ValueError(f"Invalid parameter_name: {parameter_name!r}")
    if not re.fullmatch(r"[a-zA-Z_]\w*", return_alias):
        raise ValueError(f"Invalid return_alias: {return_alias!r}")

    return (
        f"MATCH (h:HOSTNAME {{name: ${parameter_name}}})"
        f"<-[:NAMESERVER_FOR]-(ns:HOSTNAME) "
        f"RETURN ns.name AS {return_alias} LIMIT {limit}"
    )


def build_whois_query() -> str:
    """Build query to get WHOIS data for a hostname.

    Retrieves registrar, registrant organization, contact email, and phone
    using OPTIONAL MATCH since WHOIS data is sparse.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname}) "
        "OPTIONAL MATCH (h)-[:HAS_REGISTRAR]->(r:REGISTRAR) "
        "OPTIONAL MATCH (h)-[:REGISTERED_BY]->(org:ORGANIZATION) "
        "OPTIONAL MATCH (h)-[:HAS_EMAIL]->(email:EMAIL) "
        "OPTIONAL MATCH (h)-[:HAS_PHONE]->(phone:PHONE) "
        "RETURN r.name AS registrar, org.name AS registrant_org, "
        "email.name AS registrant_email, phone.name AS registrant_phone, "
        "h.registrationDate AS registration_date, "
        "h.expirationDate AS expiration_date "
        "LIMIT 1"
    )


def build_whois_prev_registrar_query() -> str:
    """Build query to get previous registrar for a hostname.

    Uses the PREV_REGISTRAR relationship (618M edges) to detect
    registrar changes which can signal domain hijacking.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname})-[:PREV_REGISTRAR]->(pr:REGISTRAR) "
        "RETURN pr.name AS prev_registrar "
        "LIMIT 1"
    )


def build_whois_shared_contact_query() -> str:
    """Build query to find domains sharing the same registrant email.

    Uses the EMAIL node as a pivot to find related domains.
    Always uses LIMIT to prevent scanning the full graph.

    Returns:
        Cypher query string with $email parameter.
    """
    return "MATCH (email:EMAIL {name: $email})<-[:HAS_EMAIL]-(h:HOSTNAME) RETURN h.name AS domain LIMIT 50"


def build_whois_shared_org_query() -> str:
    """Build query to find domains sharing the same registrant organization.

    Returns:
        Cypher query string with $org parameter.
    """
    return "MATCH (org:ORGANIZATION {name: $org})<-[:REGISTERED_BY]-(h:HOSTNAME) RETURN h.name AS domain LIMIT 50"


def build_whois_shared_phone_query() -> str:
    """Build query to find domains sharing the same registrant phone.

    Returns:
        Cypher query string with $phone parameter.
    """
    return "MATCH (phone:PHONE {name: $phone})<-[:HAS_PHONE]-(h:HOSTNAME) RETURN h.name AS domain LIMIT 50"


def build_geoip_query() -> str:
    """Build query to get city-level GeoIP data for an IP address.

    Uses IPV4->LOCATED_IN->CITY (1 hop). CITY nodes contain country
    in the name (e.g. "Mountain View, US") plus latitude/longitude.

    Returns:
        Cypher query string with $ip parameter.
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})-[:LOCATED_IN]->(city:CITY) "
        "RETURN city.name AS city, "
        "city.latitude AS latitude, city.longitude AS longitude "
        "LIMIT 1"
    )


def build_web_links_query() -> str:
    """Build query to get domains linked to/from a hostname.

    Uses LINKS_TO edges (10.8B total) with strict LIMIT.
    Anchored on the queried hostname to avoid scanning.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname})-[:LINKS_TO]->(target:HOSTNAME) "
        "RETURN target.name AS linked_domain, 'outbound' AS direction "
        "LIMIT 25"
    )


def build_web_inbound_links_query() -> str:
    """Build query to get domains that link to a hostname.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (source:HOSTNAME)-[:LINKS_TO]->(h:HOSTNAME {name: $hostname}) "
        "RETURN source.name AS linked_domain, 'inbound' AS direction "
        "LIMIT 25"
    )


def build_web_link_counts_query() -> str:
    """Build query to get accurate outbound and inbound link counts.

    Separate from the domain-list queries so counts are not truncated
    by the LIMIT applied to those queries.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname}) "
        "OPTIONAL MATCH (h)-[:LINKS_TO]->(out:HOSTNAME) "
        "OPTIONAL MATCH (inb:HOSTNAME)-[:LINKS_TO]->(h) "
        "RETURN count(DISTINCT out) AS outbound_count, "
        "count(DISTINCT inb) AS inbound_count"
    )


def build_hostname_threat_query() -> str:
    """Build query to get threat properties directly from a HOSTNAME node.

    HOSTNAME nodes have their own threat properties (threatScore, threatLevel,
    is* booleans) which are independent of IPV4 threat properties.

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname}) "
        "RETURN h.threatScore AS threat_score, h.threatLevel AS threat_level, "
        "h.isThreat AS is_threat, h.isTor AS is_tor, h.isC2 AS is_c2, "
        "h.isMalware AS is_malware, h.isPhishing AS is_phishing, h.isSpam AS is_spam, "
        "h.isBruteforce AS is_bruteforce, h.isScanner AS is_scanner, "
        "h.isBlacklist AS is_blacklist, h.isProxy AS is_proxy, h.isVpn AS is_vpn, "
        "h.isAnonymizer AS is_anonymizer, h.isWhitelist AS is_whitelist, "
        "h.threatSources AS threat_sources_count "
        "LIMIT 1"
    )


def build_prefix_threat_query() -> str:
    """Build query to get threat properties from ANNOUNCED_PREFIX and REGISTERED_PREFIX.

    Both prefix types have threatScore, threatLevel, and isThreat properties
    that provide network-level threat assessment.

    Returns:
        Cypher query string with $ip parameter.
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})-[:ANNOUNCED_BY]->(ap:ANNOUNCED_PREFIX) "
        "OPTIONAL MATCH (ip)-[:BELONGS_TO]->(rp:REGISTERED_PREFIX) "
        "RETURN ap.name AS announced_prefix, ap.threatScore AS ap_threat_score, "
        "ap.threatLevel AS ap_threat_level, ap.isThreat AS ap_is_threat, "
        "rp.name AS registered_prefix, rp.threatScore AS rp_threat_score, "
        "rp.threatLevel AS rp_threat_level, rp.isThreat AS rp_is_threat "
        "LIMIT 1"
    )


def build_bgp_hijack_query() -> str:
    """Build query to detect BGP hijack by comparing ANNOUNCED vs REGISTERED prefix ownership.

    Compares the ASN that announces a prefix (via BGP) with the ASN that
    owns the registered prefix (via RIR allocation). A mismatch can indicate
    route hijacking.

    Returns:
        Cypher query string with $ip parameter.
    """
    return (
        "MATCH (ip:IPV4 {name: $ip})-[:ANNOUNCED_BY]->(ap:ANNOUNCED_PREFIX)-[:ROUTES]->(ann_asn:ASN) "
        "MATCH (ip)-[:BELONGS_TO]->(rp:REGISTERED_PREFIX)-[:ROUTES]->(reg_asn:ASN) "
        "WHERE ann_asn.name <> reg_asn.name "
        "RETURN ap.name AS announced_prefix, ann_asn.name AS announcing_asn, "
        "rp.name AS registered_prefix, reg_asn.name AS registered_asn "
        "LIMIT 1"
    )


def build_org_pivot_query() -> str:
    """Build query to get organization information for a hostname.

    Uses HOSTNAME->REGISTERED_BY->ORGANIZATION path (916M edges).

    Returns:
        Cypher query string with $hostname parameter.
    """
    return (
        "MATCH (h:HOSTNAME {name: $hostname})-[:REGISTERED_BY]->(org:ORGANIZATION) "
        "RETURN org.name AS organization "
        "LIMIT 1"
    )


def build_impossible_travel_resolve_query() -> str:
    """Build query to resolve a hostname to its IPs (stage 1 of impossible travel).

    Stage 1: Get all IPs for a hostname. Stage 2 uses build_geoip_query()
    on each IP. Split into 2 stages to stay within API depth limits
    (each stage is 1–2 hops instead of 3 combined).

    Returns:
        Cypher query string with $hostname parameter.
    """
    return "MATCH (h:HOSTNAME {name: $hostname})-[:RESOLVES_TO]->(ip:IPV4) RETURN ip.name AS ip LIMIT 20"


def build_feed_query() -> str:
    """Build the threat intelligence feed query.

    Traverses LISTED_IN to FEED_SOURCE, then BELONGS_TO to CATEGORY to
    get feed category data. FEED_SOURCE nodes only have a ``name`` property;
    category information lives on the related CATEGORY node.

    Returns:
        Cypher query string with $indicator parameter.
    """
    return (
        "MATCH (n {name: $indicator})-[:LISTED_IN]->(f:FEED_SOURCE) "
        "OPTIONAL MATCH (f)-[:BELONGS_TO]->(c:CATEGORY) "
        "RETURN f.name AS feed_name, c.name AS category "
        "LIMIT 100"
    )
