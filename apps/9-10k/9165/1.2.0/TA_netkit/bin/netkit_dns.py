try:
    import import_declare_test
except ImportError:
    pass

import ipaddress
import json
import re
import time

import dns.exception
import dns.flags
import dns.message
import dns.query
import dns.rdatatype
import dns.resolver
import netkit_config
import netkit_logging
from netkit_targets import parse_names, run_parallel

_SOURCETYPE = "netkit:dns"
_DEFAULT_RECORD_TYPES = "A,AAAA"
_DEFAULT_TIMEOUT_MS = 5000
_ANSWERS_MAX_BYTES = 8192
_EDNS_PAYLOAD = 1232
_DNS_PORT = 53
_DEFAULT_TIMEOUT_S = 5.0
_NO_NAMESERVER = "no_nameserver"
_RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "CAA")
_PROTOCOLS = ("auto", "udp", "tcp")
_TIMEOUT_MS_RANGE = (1, 60000)
_INTERVAL_RANGE_S = (10, 86400)
_DOMAIN_GROUP_CONF = "ta_netkit_domain_group"
_RESOLVER_CONF = "ta_netkit_dns_resolver"
_SETTINGS_CONF = "ta_netkit_settings"
_SETTINGS_STANZA = "settings"
_STORED_NAME_RE = re.compile(r"^[a-zA-Z]\w*$")


def send_query(message, nameserver, timeout_s, protocol):
    if protocol == "udp":
        return dns.query.udp(
            message, nameserver, timeout=timeout_s, port=_DNS_PORT), False
    if protocol == "tcp":
        return dns.query.tcp(
            message, nameserver, timeout=timeout_s, port=_DNS_PORT), True
    return dns.query.udp_with_fallback(
        message, nameserver, timeout=timeout_s, port=_DNS_PORT)


def cap_answers(answers):
    if not answers:
        return None, None
    kept = []
    size = 2
    for answer in answers:
        size += len(json.dumps(answer)) + 1
        if size > _ANSWERS_MAX_BYTES:
            return (kept or None), 1
        kept.append(answer)
    return kept, 0


def _base_result(name, rdtype, nameserver):
    return {
        "query": name,
        "record_type": rdtype,
        "resolver": nameserver,
        "resolver_port": _DNS_PORT if nameserver else None,
        "resolver_source": None,
        "used_tcp": None,
        "answers": None,
        "answers_truncated": None,
        "answer_count": None,
        "query_count": None,
        "authority_count": None,
        "additional_count": None,
        "ttl": None,
        "rcode": None,
        "flag_aa": None,
        "flag_ad": None,
        "flag_tc": None,
        "transaction_id": None,
        "rtt_ms": None,
        "success": 0,
        "error": None,
    }


def _answer_rdata(response):
    answers = []
    ttl = None
    for rrset in response.answer:
        if ttl is None:
            ttl = rrset.ttl
        for rdata in rrset:
            answers.append(rdata.to_text())
    return (answers or None), ttl


def _response_fields(response):
    answers, ttl = _answer_rdata(response)
    kept, truncated = cap_answers(answers)
    flags = response.flags
    return {
        "answers": kept,
        "answers_truncated": truncated,
        "answer_count": sum(len(rrset) for rrset in response.answer),
        "query_count": len(response.question),
        "authority_count": sum(len(rrset) for rrset in response.authority),
        "additional_count": sum(len(rrset) for rrset in response.additional),
        "ttl": ttl,
        "rcode": int(response.rcode()),
        "flag_aa": 1 if flags & dns.flags.AA else 0,
        "flag_ad": 1 if flags & dns.flags.AD else 0,
        "flag_tc": 1 if flags & dns.flags.TC else 0,
        "transaction_id": int(response.id),
    }


def _finish(result, start=None):
    if start is not None:
        result["rtt_ms"] = round((time.perf_counter() - start) * 1000.0, 3)
    result["epoch"] = time.time()
    return result


def resolve(name, rdtype, nameserver=None, protocol="auto",
            timeout_s=_DEFAULT_TIMEOUT_S, _query=send_query):
    result = _base_result(name, rdtype, nameserver)
    if not nameserver:
        result["error"] = _NO_NAMESERVER
        return _finish(result)
    try:
        message = dns.message.make_query(
            name, dns.rdatatype.from_text(rdtype),
            use_edns=0, payload=_EDNS_PAYLOAD)
    except Exception as exc:
        result["error"] = type(exc).__name__
        return _finish(result)
    start = time.perf_counter()
    try:
        response, used_tcp = _query(message, nameserver, timeout_s, protocol)
    except (dns.exception.DNSException, OSError) as exc:
        result["error"] = type(exc).__name__
        return _finish(result, start)
    result["used_tcp"] = 1 if used_tcp else 0
    result["success"] = 1
    result.update(_response_fields(response))
    return _finish(result, start)


def resolve_any(name, rdtype, nameservers, protocol,
                timeout_s=_DEFAULT_TIMEOUT_S, _query=send_query):
    result = None
    for nameserver in nameservers:
        result = resolve(name, rdtype, nameserver, protocol, timeout_s,
                         _query=_query)
        if result["success"]:
            return result
    if result is None:
        result = _finish(_base_result(name, rdtype, None))
        result["error"] = _NO_NAMESERVER
    return result


def validate_protocol(raw):
    protocol = (raw or "").strip()
    if protocol and protocol not in _PROTOCOLS:
        raise ValueError("unsupported protocol: " + protocol)
    return protocol


def validate_nameserver(raw):
    literal = (raw or "").strip()
    if not literal:
        raise ValueError("nameserver is empty")
    try:
        ipaddress.ip_address(literal)
    except ValueError:
        raise ValueError(
            "nameserver must be an IP address literal, not a hostname: " + literal)
    return literal


def system_nameservers():
    return [str(server) for server in dns.resolver.Resolver(configure=True).nameservers]


def _settings(session_key, _reader, logger=None):
    try:
        return _reader(session_key, _SETTINGS_CONF, _SETTINGS_STANZA)
    except Exception as exc:
        if logger is not None:
            logger.warning(netkit_logging.kv(
                event="settings_read_failed",
                error=str(exc) or type(exc).__name__))
        return {}


def resolve_domains(session_key, group_name, targets_raw, _reader=netkit_config.read_stanza):
    group_name = (group_name or "").strip()
    targets_raw = (targets_raw or "").strip()
    if not group_name and not targets_raw:
        raise ValueError("specify a domain group, targets, or both")
    parts = []
    if group_name:
        if not _STORED_NAME_RE.match(group_name):
            raise ValueError("invalid domain group name: " + group_name)
        stanza = _reader(session_key, _DOMAIN_GROUP_CONF, group_name)
        parts.append(stanza.get("domains", "") or "")
    if targets_raw:
        parts.append(targets_raw)
    return parse_names("\n".join(parts))


def _default_protocol(settings):
    return validate_protocol(settings.get("default_protocol")) or "auto"


def resolve_target_resolver(session_key, resolver_ref, _reader=netkit_config.read_stanza,
                            _system=system_nameservers, logger=None):
    ref = (resolver_ref or "").strip()
    settings = _settings(session_key, _reader, logger)
    default_protocol = _default_protocol(settings)
    if ref:
        if _STORED_NAME_RE.match(ref):
            stanza = _reader(session_key, _RESOLVER_CONF, ref)
            nameserver = validate_nameserver(stanza.get("nameserver", ""))
            protocol = validate_protocol(stanza.get("protocol")) or default_protocol
        else:
            nameserver = validate_nameserver(ref)
            protocol = default_protocol
        return [nameserver], protocol, "input"
    if netkit_config.is_true(settings.get("override_system_resolver")):
        return ([validate_nameserver(settings.get("default_resolver", ""))],
                default_protocol, "default")
    servers = _system()
    if not servers:
        raise ValueError("no system nameserver configured in /etc/resolv.conf")
    return servers, default_protocol, "system"


def validate_record_types(raw):
    types = [chunk.strip().upper() for chunk in (raw or "").split(",")
             if chunk.strip()]
    if not types:
        raise ValueError("select at least one record type")
    for rdtype in types:
        if rdtype not in _RECORD_TYPES:
            raise ValueError("unsupported record type: " + rdtype)
    return types


def validate_input(definition):
    parameters = definition.parameters
    group = (parameters.get("domain_group") or "").strip()
    targets = (parameters.get("targets") or "").strip()
    if not group and not targets:
        raise ValueError("specify a domain group, targets, or both")
    if group and not _STORED_NAME_RE.match(group):
        raise ValueError("invalid domain group name: " + group)
    if targets:
        parse_names(targets)
    validate_record_types(parameters.get("record_types") or _DEFAULT_RECORD_TYPES)
    resolver = (parameters.get("resolver") or "").strip()
    if resolver and not _STORED_NAME_RE.match(resolver):
        validate_nameserver(resolver)
    netkit_config.validate_whole_number(
        parameters, "timeout_ms", *_TIMEOUT_MS_RANGE, default=_DEFAULT_TIMEOUT_MS)
    netkit_config.validate_interval(parameters, *_INTERVAL_RANGE_S)


def run_probe(names, record_types, nameservers, protocol, timeout_ms,
              _query=send_query):
    timeout_s = timeout_ms / 1000.0
    pairs = [(name, rdtype) for name in names for rdtype in record_types]
    return run_parallel(pairs, lambda pair: resolve_any(
        pair[0], pair[1], nameservers, protocol, timeout_s, _query=_query))


def _emit_config_failure(logger, name, input_item, event_writer, run_epoch, exc,
                         names=None):
    detail = str(exc) or type(exc).__name__
    logger.error(netkit_logging.kv(
        event="dependency_missing", input=name, error=detail))
    if names:
        queries = names
    else:
        try:
            queries = parse_names(input_item.get("targets") or "")
        except ValueError:
            queries = [None]
    for query in queries:
        result = _base_result(query, None, None)
        result["error"] = detail
        netkit_logging.emit_event(
            event_writer, name, _SOURCETYPE, run_epoch, result)


def _stream_one(logger, name, input_item, session_key, event_writer):
    run_epoch = time.time()
    timeout_ms = netkit_config.clamp_param(
        logger, name, "timeout_ms",
        int(input_item.get("timeout_ms") or _DEFAULT_TIMEOUT_MS),
        *_TIMEOUT_MS_RANGE)
    try:
        names = resolve_domains(
            session_key, input_item.get("domain_group"), input_item.get("targets"))
    except Exception as exc:
        _emit_config_failure(logger, name, input_item, event_writer, run_epoch, exc)
        return
    try:
        record_types = validate_record_types(
            input_item.get("record_types") or _DEFAULT_RECORD_TYPES)
        nameservers, protocol, source = resolve_target_resolver(
            session_key, input_item.get("resolver"), logger=logger)
    except Exception as exc:
        _emit_config_failure(
            logger, name, input_item, event_writer, run_epoch, exc, names=names)
        return
    run_start = time.perf_counter()
    results = run_probe(
        names, record_types, nameservers, protocol, timeout_ms,
        _query=send_query)
    for result in results:
        result["resolver_source"] = source
    answered = netkit_logging.emit_results(
        logger, name, event_writer, _SOURCETYPE, run_epoch, results,
        ok_field="success", fail_event="query_failed",
        fail_fields=("query", "record_type", "resolver", "error"),
        debug_fields=("query", "record_type", "rcode", "answer_count", "rtt_ms"))
    netkit_logging.log_complete(
        logger, name, run_start, queries=len(results), answered=answered)


def stream_events(inputs, event_writer):
    netkit_logging.run_input(inputs, event_writer, "dns_error", _stream_one)
