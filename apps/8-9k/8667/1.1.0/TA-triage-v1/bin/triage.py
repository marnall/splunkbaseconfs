#!/usr/bin/env python3
"""Splunk custom streaming search command: | triage

Supports:
- model=claude with Anthropic Messages API via ANTHROPIC_API_KEY
- model=ollama with local Ollama-compatible HTTP API
- cache=true cache_ttl=<seconds> cache_key_fields="field1,field2"
- context_fields="field1,field2"

Fallback:
- If remote model access is unavailable, returns deterministic heuristic triage.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import request, error

try:
    import splunk.Intersplunk as intersplunk
except Exception as exc:  # pragma: no cover
    raise RuntimeError("This script must run inside Splunk.") from exc

APP_NAME = "TA-triage"
CACHE_DIR = Path(os.environ.get("SPLUNK_HOME", "/opt/splunk")) / "var" / "run" / APP_NAME / "cache"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "mistral"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

MITRE_MAP = [
    (re.compile(r"powershell|pwsh", re.I), ("T1059.001", "PowerShell", "Execution")),
    (re.compile(r"cmd\.exe|/c\\b|cmd /c", re.I), ("T1059.003", "Windows Command Shell", "Execution")),
    (re.compile(r"rundll32", re.I), ("T1218.011", "Rundll32", "Defense Evasion")),
    (re.compile(r"regsvr32", re.I), ("T1218.010", "Regsvr32", "Defense Evasion")),
    (re.compile(r"mshta", re.I), ("T1218.005", "Mshta", "Defense Evasion")),
    (re.compile(r"wscript|cscript", re.I), ("T1059.005", "Visual Basic", "Execution")),
    (re.compile(r"mimikatz|sekurlsa", re.I), ("T1003", "OS Credential Dumping", "Credential Access")),
    (re.compile(r"encodedcommand|-enc\\b|frombase64string", re.I), ("T1027", "Obfuscated/Compressed Files and Information", "Defense Evasion")),
    (re.compile(r"psexec|wmic|winrm", re.I), ("T1021", "Remote Services", "Lateral Movement")),
    (re.compile(r"curl|wget|bitsadmin|invoke-webrequest", re.I), ("T1105", "Ingress Tool Transfer", "Command and Control")),
]

SEVERITY_LABELS = [
    (0, "Informational"),
    (3, "Low"),
    (5, "Medium"),
    (7, "High"),
    (9, "Critical"),
]


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_csv(value: Any) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]


def severity_label(score: int) -> str:
    current = "Informational"
    for threshold, label in SEVERITY_LABELS:
        if score >= threshold:
            current = label
    return current


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def safe_json_dumps(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)


def build_cache_key(event: Dict[str, Any], cache_key_fields: List[str]) -> str:
    if cache_key_fields:
        base = {field: event.get(field) for field in cache_key_fields}
    else:
        # Exclude volatile Splunk internals where possible.
        base = {k: v for k, v in event.items() if not str(k).startswith("_")}
    digest = hashlib.sha256(safe_json_dumps(base).encode("utf-8")).hexdigest()
    return digest


def load_cache(key: str, ttl: int) -> Dict[str, Any] | None:
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if int(time.time()) - int(raw.get("cached_at", 0)) > ttl:
            return None
        return raw.get("result")
    except Exception:
        return None


def save_cache(key: str, result: Dict[str, Any]) -> None:
    path = CACHE_DIR / f"{key}.json"
    payload = {"cached_at": int(time.time()), "result": result}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def extract_iocs(text: str) -> Dict[str, List[str]]:
    ipv4s = []
    domains = []
    urls = []
    hashes = []

    for candidate in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
        try:
            ipaddress.ip_address(candidate)
            ipv4s.append(candidate)
        except ValueError:
            pass

    urls.extend(re.findall(r"https?://[^\s\"']+", text, flags=re.I))
    hashes.extend(re.findall(r"\b[a-fA-F0-9]{32,64}\b", text))

    domain_candidates = re.findall(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b", text)
    for dom in domain_candidates:
        if not any(dom in u for u in urls) and not re.match(r"^\d+\.\d+\.\d+\.\d+$", dom):
            domains.append(dom)

    return {
        "ipv4": sorted(set(ipv4s)),
        "domains": sorted(set(domains)),
        "urls": sorted(set(urls)),
        "hashes": sorted(set(hashes)),
    }


def flatten_context(event: Dict[str, Any], context_fields: List[str]) -> str:
    if context_fields:
        items = {field: event.get(field, "") for field in context_fields}
    else:
        items = {k: v for k, v in event.items() if not str(k).startswith("_")}

    parts = []
    for k, v in items.items():
        if isinstance(v, list):
            v = ", ".join(map(str, v))
        parts.append(f"{k}: {v}")
    return "\n".join(parts)


def heuristic_triage(event: Dict[str, Any], context_fields: List[str]) -> Dict[str, Any]:
    text = flatten_context(event, context_fields)
    text_l = text.lower()
    score = 2
    reasons: List[str] = []
    mitre_id, mitre_name, kill_chain = "T1595", "Active Scanning", "Reconnaissance"

    for pattern, mapping in MITRE_MAP:
        if pattern.search(text):
            mitre_id, mitre_name, kill_chain = mapping
            score += 2
            reasons.append(f"Matched pattern for {mitre_name} ({mitre_id})")
            break

    if re.search(r"encodedcommand|-enc\\b|base64|frombase64string", text, re.I):
        score += 3
        reasons.append("Obfuscation or encoded payload indicators detected")
    if re.search(r"mimikatz|lsass|sekurlsa|credential dump", text, re.I):
        score += 4
        reasons.append("Credential access indicators detected")
    if re.search(r"rundll32|regsvr32|mshta|powershell|cmd\.exe", text, re.I):
        score += 2
        reasons.append("Living-off-the-land execution utilities present")
    if re.search(r"crowdstrike", text_l) and re.search(r"detection|malicious|suspicious|prevented", text_l):
        score += 1
        reasons.append("Native EDR detection semantics indicate elevated suspicion")

    score = max(1, min(10, score))
    fp_likelihood = "Low" if score >= 7 else "Medium" if score >= 4 else "High"
    iocs = extract_iocs(text)

    analysis = (
        f"Event suggests {mitre_name} behavior with severity {score}/10. "
        f"Primary reasoning: {'; '.join(reasons[:3]) or 'limited context available'}."
    )
    recommendation = (
        "Validate host/user context, review process ancestry, confirm parent-child execution chain, "
        "and isolate the endpoint if additional corroborating indicators exist."
    )

    return {
        "triage_model_used": "heuristic",
        "triage_mitre_technique": mitre_id,
        "triage_mitre_name": mitre_name,
        "triage_severity": score,
        "triage_severity_label": severity_label(score),
        "triage_analysis": analysis,
        "triage_recommendation": recommendation,
        "triage_false_positive_likelihood": fp_likelihood,
        "triage_false_positive_reason": "Heuristic estimate based on observable indicators and available context.",
        "triage_kill_chain_phase": kill_chain,
        "triage_iocs": safe_json_dumps(iocs),
        "triage_cached": False,
    }


def http_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 30) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset)
        return json.loads(body)


def prompt_for_event(event: Dict[str, Any], context_fields: List[str]) -> str:
    context = flatten_context(event, context_fields)
    return (
        "You are a SOC triage assistant. Analyze the event and return strict JSON with keys: "
        "mitre_technique, mitre_name, severity, severity_label, analysis, recommendation, "
        "false_positive_likelihood, false_positive_reason, kill_chain_phase, iocs. "
        "The iocs value must be an object with keys ipv4, domains, urls, hashes. "
        "Severity must be an integer 1-10.\n\n"
        f"Event:\n{context}"
    )


def normalize_llm_result(raw: Dict[str, Any], model_name: str) -> Dict[str, Any]:
    severity = int(raw.get("severity", 5))
    severity = max(1, min(10, severity))
    iocs = raw.get("iocs", {})
    if not isinstance(iocs, dict):
        iocs = {"raw": iocs}
    return {
        "triage_model_used": model_name,
        "triage_mitre_technique": raw.get("mitre_technique", "Unknown"),
        "triage_mitre_name": raw.get("mitre_name", "Unknown"),
        "triage_severity": severity,
        "triage_severity_label": raw.get("severity_label", severity_label(severity)),
        "triage_analysis": raw.get("analysis", "No analysis returned."),
        "triage_recommendation": raw.get("recommendation", "No recommendation returned."),
        "triage_false_positive_likelihood": raw.get("false_positive_likelihood", "Unknown"),
        "triage_false_positive_reason": raw.get("false_positive_reason", "No reason returned."),
        "triage_kill_chain_phase": raw.get("kill_chain_phase", "Unknown"),
        "triage_iocs": safe_json_dumps(iocs),
        "triage_cached": False,
    }


def extract_json_block(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if match:
        return json.loads(match.group(0))
    raise ValueError("No JSON object found in model output")


def triage_with_claude(event: Dict[str, Any], context_fields: List[str], model: str) -> Dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    payload = {
        "model": "claude-3-5-sonnet-latest",
        "max_tokens": 700,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt_for_event(event, context_fields)}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    response = http_json(ANTHROPIC_URL, payload, headers=headers)
    parts = response.get("content", [])
    text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
    raw = extract_json_block("\n".join(text_parts))
    return normalize_llm_result(raw, model)


def triage_with_ollama(event: Dict[str, Any], context_fields: List[str], ollama_url: str, ollama_model: str) -> Dict[str, Any]:
    base = ollama_url.rstrip("/")
    payload = {
        "model": ollama_model,
        "stream": False,
        "format": "json",
        "prompt": prompt_for_event(event, context_fields),
    }
    headers = {"Content-Type": "application/json"}
    response = http_json(f"{base}/api/generate", payload, headers=headers)
    raw_text = response.get("response", "{}")
    raw = extract_json_block(raw_text)
    return normalize_llm_result(raw, f"ollama:{ollama_model}")


def triage_event(event: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    context_fields = parse_csv(options.get("context_fields"))
    cache_enabled = parse_bool(options.get("cache"), default=False)
    cache_ttl = int(options.get("cache_ttl", 3600))
    cache_key_fields = parse_csv(options.get("cache_key_fields"))
    model = str(options.get("model", "heuristic")).strip().lower()
    ollama_url = str(options.get("ollama_url", DEFAULT_OLLAMA_URL)).strip() or DEFAULT_OLLAMA_URL
    ollama_model = str(options.get("ollama_model", DEFAULT_OLLAMA_MODEL)).strip() or DEFAULT_OLLAMA_MODEL

    cache_key = None
    if cache_enabled:
        ensure_cache_dir()
        cache_key = build_cache_key(event, cache_key_fields)
        cached = load_cache(cache_key, cache_ttl)
        if cached:
            cached = dict(cached)
            cached["triage_cached"] = True
            return cached

    result: Dict[str, Any]
    try:
        if model == "claude":
            result = triage_with_claude(event, context_fields, model)
        elif model == "ollama":
            result = triage_with_ollama(event, context_fields, ollama_url, ollama_model)
        else:
            result = heuristic_triage(event, context_fields)
    except Exception as exc:
        result = heuristic_triage(event, context_fields)
        result["triage_model_requested"] = model
        result["triage_error"] = str(exc)

    if cache_enabled and cache_key:
        save_cache(cache_key, result)

    return result


def main() -> None:
    try:
        _keywords, options = intersplunk.getKeywordsAndOptions()
        results, _, _ = intersplunk.getOrganizedResults()

        output = []
        for event in results:
            triage = triage_event(dict(event), options)
            merged = dict(event)
            merged.update(triage)
            output.append(merged)

        intersplunk.outputResults(output)
    except Exception as exc:
        intersplunk.generateErrorResults(str(exc))


if __name__ == "__main__":
    main()
