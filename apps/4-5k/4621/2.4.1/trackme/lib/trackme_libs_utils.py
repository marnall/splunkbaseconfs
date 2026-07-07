#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import json
import os
import sys
import re
import uuid

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))


def trackme_parse_describe_flag_from_payload(payload):
    """
    Parse the REST handler ``describe`` flag from a JSON request body string.

    Returns True only when the body is a JSON object and ``describe`` is
    either JSON boolean ``true`` or a string that equals ``true`` after
    stripping whitespace and case-folding (e.g. ``"true"``, ``" TRUE"``).

    Returns False for missing/invalid JSON, non-object root, boolean false,
    the string ``"false"``, or any other value (see issue #1055).
    """
    try:
        resp_dict = json.loads(str(payload))
    except Exception:
        return False
    if not isinstance(resp_dict, dict):
        return False
    raw = resp_dict.get("describe", False)
    if raw is True:
        return True
    if isinstance(raw, str) and raw.strip().lower() == "true":
        return True
    return False


def get_uuid():
    """
    Function to return a unique uuid which is used to trace performance run_time of each subtask.
    """
    return str(uuid.uuid4())


def remove_leading_spaces(text):
    """
    Remove leading spaces from each line of a variable
    """
    # split the text into lines, remove leading spaces from each line, and rejoin them
    cleaned_text = "\n".join([line.lstrip() for line in text.split("\n")])
    return cleaned_text


def sanitize_spl_input(s):
    """
    Strip non-printable control characters from SPL input strings.
    Preserves tab (0x09), newline (0x0A), and carriage return (0x0D) which are valid in SPL.
    Removes characters like backspace (0x08) that can sneak in from copy-pasting from PDFs or rich text.
    """
    if not isinstance(s, str):
        return s
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", s)


def sanitize_spl_quoted_arg(s):
    """Sanitise a value for safe interpolation inside a double-quoted SPL arg.

    Stronger than :func:`sanitize_spl_input`: in addition to stripping the
    non-printable control characters, also strips the characters that
    could let a value escape a quoted SPL argument — closing the quote
    (`"`), opening a backtick macro (`` ` ``) or a variable substitution
    (``$``). Use this anywhere a user-controlled string is about to land
    inside an SPL string literal
    (e.g. ``| trackmelookupsmonitor app_namespace="<user value>"``).

    Backslashes are deliberately preserved because some callers — the
    lookups ``name_pattern`` regex in particular — require sequences
    like ``\\d``, ``\\w`` or ``\\.``. The only backslash case that could
    let a value still escape the surrounding quoted arg is a *trailing*
    backslash (``foo\\``), which would turn the closing ``"`` into an
    escaped quote. We strip trailing backslashes for that reason.

    Non-string inputs are coerced to ``str`` before sanitisation
    (``None`` becomes the empty string). This prevents a malformed
    request that sends e.g. a list or a dict for ``app_namespace``
    from bypassing sanitisation entirely — the previous behaviour
    returned non-strings unchanged, which would interpolate the
    Python ``repr`` (with its own unescaped quotes) into the
    generated SPL.
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    s = sanitize_spl_input(s)
    for ch in ('"', "`", "$"):
        s = s.replace(ch, "")
    # Trim trailing backslashes so the value can never escape the
    # closing quote that the caller will append.
    while s.endswith("\\"):
        s = s[:-1]
    return s


def sanitize_flx_tracker_name_prefix(s):
    """Normalize a user-supplied FLX tracker_name prefix into a safe value.

    Applied at tracker creation time (`post_flx_tracker_simulation`,
    `post_flx_tracker_create`, `post_flx_converging_tracker_create`)
    *before* appending the uuid suffix. The result is used in several
    downstream contexts that all need it to be safe:

    - Saved-search name on disk.
    - The ``| eval tracker_name = "{tracker_name}"`` wrapper line in the
      generated SPL (must not contain ``"``).
    - The ``mytracker`` placeholder substitution inside use-case templates
      (must not contain SPL metacharacters that could escape a quoted arg
      or trigger macro expansion).
    - KV record tracker keys.

    Sanitisation chain:

    - Lowercase.
    - Replace whitespace (`` ``, ``\\t``, ``\\n``, ``\\r``) and ``:`` with ``-``
      (preserves the legacy normalization).
    - Strip SPL/scripting metacharacters that could escape contexts
      downstream: ``"``, `` ` ``, ``$``, ``\\``. Stripping (rather than
      escaping) keeps the value usable in *unquoted* contexts too
      (filesystem names, KV keys, the ``mytracker`` token-replacement).
    - Cap at 40 characters.

    Returns an empty string when the input is None or non-string; the
    caller is responsible for falling back to the default ``"flx"`` prefix
    in that case.
    """
    if not isinstance(s, str):
        return ""
    s = s.lower()
    # Replace whitespace and colon with hyphen (legacy normalization).
    for ch in (" ", "\t", "\n", "\r", ":"):
        s = s.replace(ch, "-")
    # Strip SPL/scripting metacharacters that could escape downstream
    # contexts (quoted SPL args, backtick macros, $variable$ substitution,
    # backslash escapes in eval string literals).
    for ch in ('"', "`", "$", "\\"):
        s = s.replace(ch, "")
    return s[:40]


def decode_unicode(s, replace_with="?"):
    """
    Decode strings with escaped bytes and clean non-printable characters, preserving UTF-8.
    """

    def clean_text(text):
        """Remove or replace non-printable characters, preserving UTF-8."""
        # This will preserve printable ASCII, extended ASCII (Latin-1 Supplement, etc.), and other Unicode characters
        # It will replace control characters (0x00-0x1F and 0x7F-0x9F) except newline (0x0A), carriage return (0x0D), and tab (0x09)
        return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", replace_with, text)

    def replace_backslashes(text):
        """Replace backslashes with their Unicode representation, avoiding double encoding."""
        return re.sub(r"(?<!\\)\\(?!u005c)", r"\\u005c", text)

    if isinstance(s, bytes):  # If it's bytes, decode as UTF-8
        decoded = s.decode("utf-8", errors="replace")
    else:
        # If string contains escape sequences, attempt to decode
        if "\\x" in s:
            try:
                decoded = (
                    bytes(s, "latin-1")
                    .decode("unicode_escape")
                    .encode("latin-1")
                    .decode("utf-8", errors="replace")
                )
            except Exception as e:
                decoded = s  # If any error occurs, use the original string
        else:
            decoded = s

    # Replace backslashes with their Unicode representation
    decoded = replace_backslashes(decoded)

    # Clean non-printable characters from the decoded string
    return clean_text(decoded)


def encode_unicode(s, replace_with="?"):
    """
    Encode strings by interpreting Unicode escape sequences and restoring original non-UTF8 characters.
    This is the reverse operation of decode_unicode.
    """
    
    if not isinstance(s, str):
        return s
    
    # First, handle the specific \u005c\u00xx pattern that decode_unicode creates
    # This needs to be done before the general unicode_escape decoding
    if '\\u005c\\u00' in s:
        # Replace \u005c\u00xx with the actual character
        s = re.sub(r'\\u005c\\u00([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), s)
    
    # Now try to use Python's built-in unicode_escape decoder for remaining sequences
    try:
        # This will handle all remaining Unicode escape sequences including \u00e8 -> è
        decoded = s.encode('latin-1').decode('unicode_escape')
        
        # Check if there are still any Unicode sequences that need processing
        if '\\u' in decoded:
            try:
                # Try to decode any remaining Unicode sequences
                final_decoded = decoded.encode('latin-1').decode('unicode_escape')
                return final_decoded
            except (UnicodeDecodeError, UnicodeEncodeError):
                # If that fails, use regex to handle remaining sequences
                final_decoded = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), decoded)
                return final_decoded
        
        return decoded
        
    except (UnicodeDecodeError, UnicodeEncodeError):
        # If that fails, use our custom approach for any remaining sequences
        def restore_unicode_escapes(text):
            """Restore Unicode escape sequences to their original characters."""
            # Handle other Unicode escape sequences
            text = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)
            
            # Handle hex escape sequences
            text = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), text)
            
            return text
        
        decoded = restore_unicode_escapes(s)
        return decoded


def interpret_boolean(value):
    """
    Function to interpret the boolean value:
    if the value is 1 or true (case insensitive), return True, otherwise return False

    """
    if isinstance(value, bool):
        return value
    elif isinstance(value, str):
        if value.lower() == "true" or value == "1":
            return True
        else:
            return False
    elif isinstance(value, int):
        if value == 1:
            return True
        else:
            return False
    else:
        return False


def strict_interpret_boolean(value):
    """
    Standardize a value to a proper boolean.
    Accepts:
    - String 'true'/'True' or 'false'/'False'
    - String '0' or '1'
    - Integer 0 or 1
    - Boolean True or False
    Returns:
    - Boolean True or False
    Raises:
    - ValueError if the input cannot be converted to a boolean
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value = value.lower()
        if value in ("true", "1"):
            return True
        if value in ("false", "0"):
            return False
    if isinstance(value, int):
        return bool(value)
    raise ValueError("Value must be one of: true/True/1 or false/False/0")


def update_wildcard(object_value):
    """
    Update wildcard in the object value and replace it with '.*' so we interpret it as regex
    """
    # This regex will find '*' that are not preceded by a dot
    pattern = r"(?<!\.)\*"
    # Replace those '*' with '.*'
    return re.sub(pattern, r".*", object_value)


def escape_backslash(object_value):
    """
    Escape backslashes in the object_value
    """
    # This regex will find '\' and replace it with '\\'
    pattern = r"\\"
    # Replace those '\' with '\\'
    return re.sub(pattern, r"\\\\", object_value)


def replace_encoded_backslashes(object_value):
    """
    Replace encoded backslashes with actual backslashes
    """
    # This regex will find '\\u005c' and replace it with '\'
    pattern = r"\\u005c"
    # Replace those '\\u005c' with '\'
    return re.sub(pattern, r"\\", object_value)


def replace_encoded_doublebackslashes(object_value):
    """
    Replace encoded backslashes with double backslashes
    """
    # This regex will find '\\u005c' and replace it with '\'
    pattern = r"\\u005c"
    # Replace those '\\u005c' with '\'
    return re.sub(pattern, r"\\\\", object_value)


def replace_encoded_fourbackslashes(object_value):
    """
    Replace encoded backslashes with four backslashes
    """
    # This regex will find '\\u005c' and replace it with '\'
    pattern = r"\\u005c"
    # Replace those '\\u005c' with '\'
    return re.sub(pattern, r"\\\\\\\\", object_value)


def check_tenant_id(value):
    """
    Convert a time value with unit to seconds.
    Supports formats:
    - Integer (assumed to be seconds)
    - String with unit suffix (e.g. "1h", "1d", "1w")
    Returns the value in seconds as an integer.
    """

    # trim the tenant_name
    value = value.strip()
    # make it lowercase
    value = value.lower().replace(" ", "-")
    # avoid ending with multiple underscores in the tenant id
    value = re.sub(r"_{1,}", "_", value)
    # replace any underscore with a hyphen
    value = re.sub(r"_", "-", value)
    # replace anything that is not a letter, number or hyphen with a hyphen
    value = re.sub(r"[^a-zA-Z0-9-]", "-", value)

    return value


def convert_time_to_seconds(time_value):
    """
    Convert a time value with unit to seconds.
    Supports formats:
    - Integer (assumed to be seconds)
    - String with unit suffix (e.g. "15m", "1h", "1d", "1w")
    Returns the value in seconds as an integer.
    """
    try:
        # If it's already an integer, return it
        if isinstance(time_value, int):
            return time_value

        # If it's a string, try to parse the unit
        if isinstance(time_value, str):
            # Remove any whitespace
            time_value = time_value.strip()

            # Check if it ends with a unit
            if time_value.endswith("m"):
                return int(float(time_value[:-1]) * 60)  # minutes to seconds
            elif time_value.endswith("h"):
                return int(float(time_value[:-1]) * 3600)  # hours to seconds
            elif time_value.endswith("d"):
                return int(float(time_value[:-1]) * 86400)  # days to seconds
            elif time_value.endswith("w"):
                return int(float(time_value[:-1]) * 604800)  # weeks to seconds
            else:
                # Try to convert to integer (assumed to be seconds)
                return int(float(time_value))

        # If we get here, try to convert to float then int
        return int(float(time_value))

    except (ValueError, TypeError):
        raise ValueError(
            f"Invalid time value format: {time_value}. Expected format: integer or string with unit suffix (m/h/d/w)"
        )


def normalize_anomaly_reason(anomaly_reason):
    """
    Normalizes the anomaly_reason field into a consistent list of strings.

    This function handles various input formats for anomaly_reason, including:
    - A single string with delimiters (pipe, newline, or comma)
    - A list of strings, where each string might also contain delimiters
    - None, "N/A", or other null-like values

    It processes the input and returns a sorted list of unique, clean reason strings.

    Args:
        anomaly_reason (str, list, None): The input anomaly_reason to normalize.

    Returns:
        list: A sorted list of unique, non-empty reason strings. Returns an
              empty list if no valid reasons are found.
    """
    if not anomaly_reason:
        return []

    raw_reasons = []

    # If the input is a list, recursively process each item
    if isinstance(anomaly_reason, list):
        for item in anomaly_reason:
            raw_reasons.extend(normalize_anomaly_reason(item))

    # If the input is a string, split it by common delimiters
    elif isinstance(anomaly_reason, str):
        # Ignore common null-like values
        if anomaly_reason.strip().lower() in ("n/a", "none", "null", ""):
            return []
        # Split by pipe, newline, or comma
        raw_reasons = re.split(r"[|\n,]", anomaly_reason)

    # For any other type, we cannot process it
    else:
        return []

    # Clean up the list:
    # - Strip whitespace from each reason
    # - Filter out any resulting empty or null-like strings
    # - Use a set to get unique reasons, then convert back to a list and sort it

    unique_reasons = {
        reason.strip()
        for reason in raw_reasons
        if reason
        and reason.strip()
        and reason.strip().lower() not in ("n/a", "none", "null")
    }

    return sorted(list(unique_reasons))


def build_dhm_asset_list(object_value, alias_value=None):
    """
    Build the ``asset`` multivalue field for a DHM (Data Host Monitoring)
    entity: a deduplicated, sorted, lowercase set of every known variation of
    the endpoint, so TrackMe data can be cross-correlated against the rest of
    Splunk with case-insensitive KV store lookups.

    For each source value (the entity ``object`` and its ``alias``) the
    following variations are collected:

    - the value itself (lowercased) — this preserves the object verbatim,
      including any leading ``key:host|`` prefix used by the push / inject path;
    - the "bare" value with a leading ``key:host|`` prefix stripped, so the raw
      endpoint name is directly lookup-able;
    - the short hostname when the bare value is an FQDN — i.e. it contains a dot
      and its first label is not purely numeric. The numeric guard excludes
      IPv4 literals (``10.0.109.184`` → first label ``10`` is numeric, so it is
      left intact); IPv6 literals carry no dot and are likewise left intact.

    This mirrors the SPL ``trackme_dhm_build_asset`` macro one-for-one so the
    live tracker path and the schema-migration backfill produce identical
    storage. The result is stored as a native list, surfacing automatically as
    a multivalue field from the SPL perspective.

    Args:
        object_value (str): the entity object (lowercased host, optionally
            ``key:host|`` prefixed).
        alias_value (str, optional): the entity alias (operator-editable display
            value). Defaults to None.

    Returns:
        list: sorted, deduplicated, lowercase asset variations. Empty list when
              no usable input is provided.
    """
    key_prefix = "key:host|"
    assets = set()

    for raw in (object_value, alias_value):
        if not raw:
            continue
        value = str(raw).strip().lower()
        if not value:
            continue

        assets.add(value)

        bare = value[len(key_prefix):] if value.startswith(key_prefix) else value
        if not bare:
            continue
        assets.add(bare)

        if "." in bare:
            short_host = bare.split(".", 1)[0]
            # only an FQDN short name — skip IPv4 first octets (numeric labels)
            if short_host and not short_host.isdigit():
                assets.add(short_host)

    return sorted(assets)


def build_dhm_asset_index(records):
    """
    Build a flat lowercase set of every ``asset`` value across a list of DHM
    entity records, for asset-based recognition (e.g. the Inject Expected Hosts
    wizard). Defensive about the stored shape: ``asset`` may be a multivalue
    list, a single string, or absent.

    Args:
        records (iterable): DHM entity records (dicts) as returned by a KV store
            query.

    Returns:
        set[str]: lowercased, stripped asset values. Empty when no record
                  carries a usable asset.
    """
    index = set()
    for record in records or []:
        asset = record.get("asset") if isinstance(record, dict) else None
        if not asset:
            continue
        if isinstance(asset, str):
            asset = [asset]
        for value in asset:
            if value:
                index.add(str(value).strip().lower())
    return index


def dhm_host_matches_asset_index(object_value, alias_value, asset_index):
    """
    Return True when any known variation of an incoming DHM host already exists
    in ``asset_index`` (built by :func:`build_dhm_asset_index`).

    The incoming host's variations are computed with
    :func:`build_dhm_asset_list`, so short <-> FQDN equivalence is recognised in
    both directions (the short hostname is the common token). Returns False on
    an empty index or when nothing matches — never raises.

    Args:
        object_value (str): the incoming entity object (e.g. ``key:host|<host>``).
        alias_value (str): the incoming alias / raw host value (may be None).
        asset_index (set[str]): the existing-entities asset index.

    Returns:
        bool: True if the incoming host is already known via an asset variation.
    """
    if not asset_index:
        return False
    for variation in build_dhm_asset_list(object_value, alias_value):
        if variation in asset_index:
            return True
    return False


def dhm_reconcile_hosts(trackme_records, lookup_entries, match_asset_field=True):
    """
    Reconcile a set of reference (lookup / CMDB) hosts against tracked DHM
    entities, classifying both sides into coverage-gap buckets.

    Asset-variation aware: when ``match_asset_field`` is True (default), a short
    hostname in the lookup matches a tracked FQDN entity and vice versa (the
    short hostname is the common token across both sides' variations). When
    False, falls back to exact ``object`` equality.

    Args:
        trackme_records (iterable[dict]): tracked DHM entity records — each needs
            ``object`` and (for asset matching) ``asset``; ``alias`` is echoed back.
        lookup_entries (iterable[dict]): normalised lookup hosts. Each dict MUST
            carry ``object`` (e.g. ``key:host|<host>``) and ``host`` (raw value).
            Any other keys are passed through untouched into the result rows
            (so the caller can surface the original lookup columns in a CSV).
        match_asset_field (bool): asset-variation matching (True) vs exact
            ``object`` matching (False).

    Returns:
        dict with three lists:
            ``only_in_lookup``  — lookup rows with no tracked counterpart (the gap)
            ``in_both``         — lookup rows matched, each with ``matched_object``
            ``only_in_trackme`` — tracked entities absent from the lookup
                                  (``{"object", "alias"}``)

    Never raises; tolerates missing fields and odd shapes (non-dict rows skipped).
    """
    trackme_records = [r for r in (trackme_records or []) if isinstance(r, dict)]
    lookup_entries = [e for e in (lookup_entries or []) if isinstance(e, dict)]

    # ── Index the tracked side ──────────────────────────────────────────────
    # For each tracked entity we precompute its effective asset variation set:
    # the stored `asset`, or — if that is missing/empty — the set computed from
    # object/alias. This keeps an asset-less entity (e.g. discovered but not yet
    # backfilled) correctly reconciled in BOTH directions.
    trackme_object_set = set()
    asset_to_object = {}  # asset variation (lower) -> a tracked object (first wins)
    tracked = []  # (object_raw, alias, object_lower, effective_variation_set)
    for rec in trackme_records:
        obj_raw = rec.get("object")
        obj = str(obj_raw or "").strip().lower()
        if obj:
            trackme_object_set.add(obj)
        effective = set()
        if match_asset_field:
            asset = rec.get("asset")
            if isinstance(asset, str):
                asset = [asset]
            if asset:
                effective = {str(v).strip().lower() for v in asset if v}
            if not effective:
                # no stored asset — derive variations from object/alias
                effective = set(build_dhm_asset_list(obj_raw, rec.get("alias")))
            for value in effective:
                asset_to_object.setdefault(value, obj_raw)
        tracked.append((obj_raw, rec.get("alias"), obj, effective))

    # ── Classify each lookup row, and build the lookup-side index ───────────
    lookup_index = set()
    only_in_lookup = []
    in_both = []
    seen_lookup_objects = set()
    for entry in lookup_entries:
        obj = str(entry.get("object", "") or "").strip().lower()
        if not obj or obj in seen_lookup_objects:
            continue
        seen_lookup_objects.add(obj)

        if match_asset_field:
            variations = build_dhm_asset_list(obj, entry.get("host"))
            lookup_index.update(variations)
            matched_object = None
            for variation in variations:
                if variation in asset_to_object:
                    matched_object = asset_to_object[variation]
                    break
            if matched_object is not None:
                in_both.append({**entry, "matched_object": matched_object})
            else:
                only_in_lookup.append(entry)
        else:
            lookup_index.add(obj)
            if obj in trackme_object_set:
                in_both.append({**entry, "matched_object": entry.get("object")})
            else:
                only_in_lookup.append(entry)

    # ── Tracked entities with no counterpart in the lookup ──────────────────
    only_in_trackme = []
    for obj_raw, alias, obj, effective in tracked:
        if not obj:
            continue
        if match_asset_field:
            in_lookup = any(v in lookup_index for v in effective) if effective else (obj in lookup_index)
        else:
            in_lookup = obj in lookup_index
        if not in_lookup:
            only_in_trackme.append({"object": obj_raw, "alias": alias})

    return {
        "only_in_lookup": only_in_lookup,
        "in_both": in_both,
        "only_in_trackme": only_in_trackme,
    }


def build_feed_comparison_key(values):
    """
    Build the comparison key for a DSM feed from an ordered list of break-by
    field values: lowercased, stripped, ``:``-joined (the same grain a DSM
    ``object`` uses, ``<index>:<sourcetype>``). Used by the Feeds coverage gap
    analysis tool to reduce both the reference and the tracked side to a common
    break-by grain.

    Returns an empty string when every component is empty (so the caller can
    skip a useless all-blank key).
    """
    parts = [str(v if v is not None else "").strip().lower() for v in (values or [])]
    if not any(parts):
        return ""
    return ":".join(parts)


def reconcile_feed_keys(trackme_entries, reference_entries):
    """
    Exact-key reconciliation for DSM Feeds coverage gap analysis. Both inputs are
    lists of dicts each carrying a precomputed ``_cmp_key`` (built by
    :func:`build_feed_comparison_key`) plus any passthrough columns to surface in
    the result / CSV. Deduplicated by key on each side.

    Returns three lists (keys mirror the DHM tool for a shared frontend):
        ``only_in_lookup``  — reference feeds with no tracked counterpart (the gap)
        ``in_both``         — reference feeds covered by TrackMe
        ``only_in_trackme`` — tracked feeds absent from the reference

    Never raises; non-dict / keyless rows are skipped.
    """
    trackme_entries = [e for e in (trackme_entries or []) if isinstance(e, dict)]
    reference_entries = [e for e in (reference_entries or []) if isinstance(e, dict)]

    trackme_keys = {e.get("_cmp_key") for e in trackme_entries if e.get("_cmp_key")}

    only_in_lookup = []
    in_both = []
    reference_keys = set()
    seen_ref = set()
    for entry in reference_entries:
        key = entry.get("_cmp_key")
        if not key or key in seen_ref:
            continue
        seen_ref.add(key)
        reference_keys.add(key)
        if key in trackme_keys:
            in_both.append(entry)
        else:
            only_in_lookup.append(entry)

    only_in_trackme = []
    seen_tk = set()
    for entry in trackme_entries:
        key = entry.get("_cmp_key")
        if not key or key in seen_tk:
            continue
        seen_tk.add(key)
        if key not in reference_keys:
            only_in_trackme.append(entry)

    return {
        "only_in_lookup": only_in_lookup,
        "in_both": in_both,
        "only_in_trackme": only_in_trackme,
    }


def validate_variable_delay_slots(slots_config, min_delay_seconds=0):
    """
    Validate variable delay slots configuration.
    Used by both lagging classes and entity-level variable delay handlers.

    Args:
        slots_config: dict — the parsed JSON slots configuration
        min_delay_seconds: int — minimum allowed max_delay_allowed value
            (0 for lagging classes, 60 for entity variable delay)

    Returns:
        list[str] — validation errors (empty if valid)
    """
    errors = []

    if not isinstance(slots_config, dict):
        return ["variable_delay_slots must be a JSON object"]

    slots = slots_config.get("slots", [])
    if not isinstance(slots, list):
        return ["variable_delay_slots.slots must be a JSON array"]

    for i, slot in enumerate(slots):
        if not isinstance(slot, dict):
            errors.append(f"Slot at index {i}: each slot must be a JSON object")
            continue
        slot_name = slot.get("slot_name", f"slot_{i}")

        # validate days
        days = slot.get("days", [])
        if (
            not isinstance(days, list)
            or len(days) == 0
            or not all(isinstance(d, int) and 0 <= d <= 6 for d in days)
        ):
            errors.append(
                f"Slot '{slot_name}': days must be a non-empty list of integers 0-6 (0=Monday, 6=Sunday)"
            )

        # validate hours
        hours = slot.get("hours", [])
        if (
            not isinstance(hours, list)
            or len(hours) == 0
            or not all(isinstance(h, int) and 0 <= h <= 23 for h in hours)
        ):
            errors.append(
                f"Slot '{slot_name}': hours must be a non-empty list of integers 0-23"
            )

        # validate max_delay_allowed
        max_delay = slot.get("max_delay_allowed")
        if max_delay is None:
            errors.append(f"Slot '{slot_name}': max_delay_allowed is required")
        else:
            try:
                val = int(max_delay)
                if min_delay_seconds > 0:
                    if val < min_delay_seconds:
                        errors.append(
                            f"Slot '{slot_name}': max_delay_allowed must be >= {min_delay_seconds} seconds"
                        )
                else:
                    if val <= 0:
                        errors.append(
                            f"Slot '{slot_name}': max_delay_allowed must be a positive integer"
                        )
            except (ValueError, TypeError):
                errors.append(
                    f"Slot '{slot_name}': max_delay_allowed must be a valid integer"
                )

    return errors
