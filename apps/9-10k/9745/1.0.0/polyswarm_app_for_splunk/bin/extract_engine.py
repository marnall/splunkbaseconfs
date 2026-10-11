"""IOC extraction and refang engine.

Pure functions. No I/O, no network, no logging, no module level state that a
call can mutate. Nothing in this module writes the text it was handed anywhere,
which is why a search command can hand it a raw field value.

This is a port of the same engine the PolySwarm browser extension and the iOS
app run, so that a hash, a domain, or a defanged URL is read the same way in
every product. The port is faithful rather than idiomatic on purpose: the
regular expressions, the candidate ordering, the overlap resolution, and the
suppression lists are the originals, because a difference in any of them is a
difference in what an analyst sees.

GROUND TRUTH: tests/fixtures/ioc-corpus.json is the cross-product contract. If
this engine and that corpus disagree, this engine is wrong. Every product
validates against the same file with deep equality.

Public surface:

    extract(text)        -> list of indicator dicts
    refang_text(text)    -> canonical form of a defanged string
    scrub_pii(text)      -> text with high-confidence PII replaced
    luhn_valid(digits)   -> checksum gate used by the payment-card detector

An indicator dict carries exactly these fields:

    type       one of sha256, sha1, md5, ip, domain, url, email
    value      refanged canonical form, safe to send to the API
    original   the exact source text, possibly still defanged
    start      offset of original in the scanned text
    end        offset one past the last character of original
    defanged   true when refanging changed the original

The field names are part of the contract and must not be renamed.

Notes on the two languages
--------------------------
The original engine is written for a regular expression dialect where \\w means
[A-Za-z0-9_] and \\d means [0-9], with no Unicode awareness at all. Python
widens both of those to Unicode by default, which would silently change word
boundaries and octet matching around accented text. Every pattern here is
therefore compiled with the ASCII flag, which narrows \\w, \\d and \\b back to
the original meaning and also confines case-insensitive matching to ASCII, so a
character such as the Kelvin sign does not match a plain letter. That flag is
the whole of the bridge between the two dialects; nothing else needed changing.
"""

import re

# Compiled with these flags everywhere. See the note in the module docstring:
# the ASCII flag is what makes the patterns mean the same thing here as they do
# in the original engine.
_FLAGS = re.IGNORECASE | re.ASCII

# Curated TLD allowlist, not a full public suffix list. Deliberately excludes
# TLDs that overlap common file extensions (zip, mov, sh) so a filename does
# not read as a domain.
ALLOWED_TLDS = (
    # common generic TLDs
    "com", "net", "org", "info", "biz", "pro", "name", "mobi", "asia",
    # infrastructure and newer generic TLDs frequently abused
    "io", "co", "app", "dev", "cloud", "tech", "online", "site", "store",
    "shop", "club", "live", "icu", "vip", "top", "xyz", "link", "click",
    "download", "stream", "work", "space", "fun", "monster", "cyou", "rest",
    # government, education, restricted
    "gov", "edu", "mil", "int",
    # country codes, common and threat relevant
    "us", "uk", "ca", "eu", "de", "fr", "nl", "it", "es", "pl", "se", "no",
    "fi", "dk", "ch", "at", "be", "cz", "ru", "su", "cn", "jp", "kr", "in",
    "br", "au", "za", "tr", "ua", "ir", "mx", "ar", "cc", "tv", "me", "ws",
    "pw", "tk", "ml", "ga", "cf", "gq",
)

# Reputable domains, and their subdomains, suppressed from bare domain
# extraction. Applied to the domain type only, never to a URL or an email, so a
# phishing link on a hosting provider still reports.
REPUTABLE_DOMAINS = (
    "google.com", "gstatic.com", "googleapis.com", "microsoft.com",
    "apple.com", "github.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "facebook.com", "amazon.com", "cloudflare.com",
    "wikipedia.org", "mozilla.org", "w3.org", "example.com", "example.net",
    "example.org",
)

# File extensions used to drop bare domain candidates that are really filenames
# (report.docx, evil.exe). Entries here must never intersect ALLOWED_TLDS; the
# TLD allowlist is the primary filename guard and this is the second line.
FILE_EXTENSIONS = (
    "exe", "dll", "sys", "bat", "cmd", "ps1", "vbs", "js", "jse", "wsf",
    "scr", "jar", "class", "apk", "dmg", "pkg", "deb", "rpm", "msi",
    "iso", "img", "bin", "dat", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "pdf", "rtf", "txt", "csv", "log", "html", "htm", "css", "php", "py",
    "rb", "sh", "zip", "rar", "7z", "gz", "tar", "mov", "mp4", "png",
    "jpg", "jpeg", "gif", "svg", "ico", "lnk", "hta", "chm",
)

IOC_TYPES = ("sha256", "sha1", "md5", "ip", "domain", "url", "email")

# The field names an indicator dict carries, in contract order.
IOC_FIELDS = ("type", "value", "original", "start", "end", "defanged")

# ---------------------------------------------------------------------------
# Reusable defang sub-patterns, as regex source rather than compiled objects.
# A "dot" may be a literal or any bracketed or parenthesised defang form, and
# an "at" likewise.
# ---------------------------------------------------------------------------

_DOT = r"(?:\.|\[\.\]|\(\.\)|\[dot\]|\(dot\))"
_AT = r"(?:@|\[@\]|\(@\)|\[at\]|\(at\))"
# Scheme separator: :// and its defanged variants [:]// and [://].
_SEP = r"(?:://|\[:\]//|\[://\])"
# Scheme keyword: http or https and the hxxp defang. Case comes from the flag.
_SCHEME = r"(?:hxxps?|https?)"

# A DNS label: 1 to 63 characters, alphanumeric with internal hyphens.
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"

# TLD alternation, longest first so that com wins over co at the same anchor.
# Both languages try alternatives left to right, and both sorts are stable, so
# ordering by descending length reproduces the original alternation exactly.
_TLD_ALT = "|".join(sorted(ALLOWED_TLDS, key=len, reverse=True))

# A host name: one or more labels then an allowlisted TLD.
_HOST = r"(?:" + _LABEL + _DOT + r")+(?:" + _TLD_ALT + r")"

# URL body characters after the scheme separator. Brackets and parentheses are
# allowed so a defanged span such as evil[.]com or x[.]php is captured whole;
# trailing sentence punctuation is trimmed after the match instead.
_URL_BODY = r"[A-Za-z0-9\-._~:/?#@!$&'()*+,;=%\[\]]"

# Patterns are built by concatenation rather than by formatting so that the
# repetition counts do not have to be brace escaped.
_PATTERN_SHA256 = r"\b[a-f0-9]{64}\b"
_PATTERN_SHA1 = r"\b[a-f0-9]{40}\b"
_PATTERN_MD5 = r"\b[a-f0-9]{32}\b"
_PATTERN_URL = r"(?<![\w@.])" + _SCHEME + _SEP + r"[A-Za-z0-9]" + _URL_BODY + r"*"
_PATTERN_EMAIL = (
    r"(?<![\w.+-])[a-z0-9][a-z0-9._%+-]*" + _AT + _HOST + r"(?![\w])"
)
# Trailing guards on the IP pattern. The first rejects a fifth digit or a glued
# letter. The second rejects only a period that continues a longer dotted token
# such as 1.2.3.4.5, so a sentence final period does not kill the match.
_PATTERN_IP = (
    r"(?<![\w.])\d{1,3}(?:" + _DOT + r"\d{1,3}){3}(?![\w])(?!\.[\w])"
)
_PATTERN_DOMAIN = r"(?<![\w@.])" + _HOST + r"(?![\w])"

# Grouping mirrors the type list. Order here does not decide winners; overlap
# resolution does.
_PATTERNS = (
    ("sha256", _PATTERN_SHA256),
    ("sha1", _PATTERN_SHA1),
    ("md5", _PATTERN_MD5),
    ("url", _PATTERN_URL),
    ("email", _PATTERN_EMAIL),
    ("ip", _PATTERN_IP),
    ("domain", _PATTERN_DOMAIN),
)

_COMPILED = tuple(
    (ioc_type, re.compile(source, _FLAGS)) for ioc_type, source in _PATTERNS
)

# Tie break priority when two kept candidates are the same length. Lower wins,
# so a URL beats the domain inside it and an email beats its own domain.
_PRIORITY = {
    "url": 0,
    "email": 1,
    "sha256": 2,
    "sha1": 3,
    "md5": 4,
    "ip": 5,
    "domain": 6,
}

_HASH_TYPES = frozenset(["sha256", "sha1", "md5"])

# Characters trimmed from the tail of a URL match as sentence punctuation.
_URL_TAIL_PUNCTUATION = ".,;:!?'\""

# Scheme, authority, remainder of an already refanged URL. The remainder uses
# an any-character class and an absolute end anchor so that a trailing newline
# is kept rather than quietly dropped, which is what the original pattern does.
_URL_SHAPE_RE = re.compile(
    r"^([a-zA-Z][a-zA-Z0-9+.\-]*)://([^/?#]*)([\s\S]*)\Z", re.ASCII
)

_OCTET_RE = re.compile(r"^[0-9]{1,3}\Z", re.ASCII)
_DIGITS_ONLY_RE = re.compile(r"^[0-9]+\Z", re.ASCII)

# Refang rewrites, applied in this order. The order matters: the scheme rewrite
# runs before the separator rewrites, and the dot-word rewrite runs before the
# at-word rewrite so that [dot] is not mistaken for anything else.
_REFANG_SCHEME_RE = re.compile(r"h[xX]{2}p", _FLAGS)
_REFANG_DOT_RE = re.compile(r"\[\.\]|\(\.\)", re.ASCII)
_REFANG_DOT_WORD_RE = re.compile(r"\[dot\]|\(dot\)", _FLAGS)
_REFANG_AT_RE = re.compile(r"\[@\]|\(@\)", re.ASCII)
_REFANG_AT_WORD_RE = re.compile(r"\[at\]|\(at\)", _FLAGS)


def refang_text(text):
    """Rewrite common defang conventions into canonical form.

    Handles [.], (.), [dot], (dot), hxxp, [:]//, [://], [@], (@), [at] and
    (at). Safe on a whole document or on a single matched span.

    :param text: the possibly defanged text.
    :returns: the canonical form.
    """
    out = _REFANG_SCHEME_RE.sub("http", text)
    # These two are literal, so a plain replacement covers every occurrence.
    out = out.replace("[://]", "://")
    out = out.replace("[:]//", "://")
    out = _REFANG_DOT_RE.sub(".", out)
    out = _REFANG_DOT_WORD_RE.sub(".", out)
    out = _REFANG_AT_RE.sub("@", out)
    out = _REFANG_AT_WORD_RE.sub("@", out)
    return out


def _is_defanged(original):
    """True when refanging changes the span, so a defang token was present."""
    return refang_text(original) != original


def _canonical_url(refanged):
    """Lowercase the scheme and host of a refanged URL, keep the path case."""
    shape = _URL_SHAPE_RE.match(refanged)
    if shape is None:
        return refanged
    return "{0}://{1}{2}".format(
        shape.group(1).lower(), shape.group(2).lower(), shape.group(3)
    )


def _canonical_email(refanged):
    """Lowercase the domain of a refanged address, keep the local part."""
    at = refanged.rfind("@")
    if at < 0:
        return refanged
    return "{0}@{1}".format(refanged[:at], refanged[at + 1:].lower())


def _count(text, character):
    total = 0
    for candidate_character in text:
        if candidate_character == character:
            total += 1
    return total


def _trim_url_tail(span):
    """Trim trailing sentence punctuation and unbalanced closers from a URL.

    :param span: the raw URL match.
    :returns: a (trimmed, removed) pair, where removed is the character count
        taken off the tail so the caller can shorten the span end.
    """
    end = len(span)
    while True:
        if end == 0:
            break
        character = span[end - 1]
        if character in _URL_TAIL_PUNCTUATION:
            end -= 1
            continue
        head = span[:end]
        if character == ")" and _count(head, "(") < _count(head, ")"):
            end -= 1
            continue
        if character == "]" and _count(head, "[") < _count(head, "]"):
            end -= 1
            continue
        break
    return span[:end], len(span) - end


def _is_valid_ipv4(refanged):
    """True when every octet of a refanged IPv4 candidate is 0 to 255."""
    parts = refanged.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if _OCTET_RE.match(part) is None:
            return False
        if int(part) > 255:
            return False
    return True


def _is_reputable(domain):
    """Registrable suffix check against the reputable exclusion list."""
    for reputable in REPUTABLE_DOMAINS:
        if domain == reputable or domain.endswith("." + reputable):
            return True
    return False


def _looks_like_filename(domain):
    """True when the final label of a domain is a known file extension."""
    labels = domain.split(".")
    return labels[-1] in FILE_EXTENSIONS


def _candidate(ioc_type, raw, start):
    """Build a validated candidate for one raw match, or None to suppress it.

    A candidate is a tuple in IOC_FIELDS order. Tuples rather than dicts so
    that the sort keys stay cheap and the shape is fixed.
    """
    original = raw

    if ioc_type in _HASH_TYPES:
        value = original.lower()
    elif ioc_type == "ip":
        value = refang_text(original)
        if not _is_valid_ipv4(value):
            return None
    elif ioc_type == "domain":
        refanged = refang_text(original).lower()
        if _looks_like_filename(refanged):
            return None
        if _is_reputable(refanged):
            return None
        value = refanged
    elif ioc_type == "email":
        value = _canonical_email(refang_text(original))
    elif ioc_type == "url":
        trimmed, removed = _trim_url_tail(original)
        if removed > 0:
            original = trimmed
        value = _canonical_url(refang_text(original))
    else:
        return None

    return (
        ioc_type,
        value,
        original,
        start,
        start + len(original),
        _is_defanged(original),
    )


def _longest_first(candidate):
    """Sort key: longest original first, type priority breaking length ties."""
    return (-len(candidate[2]), _PRIORITY[candidate[0]])


def _by_position(candidate):
    """Sort key: source order, type priority breaking a shared start."""
    return (candidate[3], _PRIORITY[candidate[0]])


def _overlaps_any(candidate, kept):
    for other in kept:
        if candidate[3] < other[4] and candidate[4] > other[3]:
            return True
    return False


def extract(text):
    """Extract indicators from text, with source offsets.

    No deduplication: a caller that wants unique values dedupes by value, and a
    caller that highlights needs every instance. On overlap the longest match
    wins, with type priority breaking length ties, so a URL beats the domain
    and IP inside it and an email beats its own domain.

    :param text: the text to scan.
    :returns: a list of indicator dicts, ordered by start offset.
    """
    candidates = []
    for ioc_type, pattern in _COMPILED:
        for match in pattern.finditer(text):
            candidate = _candidate(ioc_type, match.group(0), match.start())
            if candidate is not None:
                candidates.append(candidate)

    # Both sorts below are stable in both languages, so candidates that tie on
    # every key stay in discovery order.
    candidates.sort(key=_longest_first)

    kept = []
    for candidate in candidates:
        if not _overlaps_any(candidate, kept):
            kept.append(candidate)

    kept.sort(key=_by_position)

    return [dict(zip(IOC_FIELDS, candidate)) for candidate in kept]


# Name parity with the shared engine, for callers that grep across products.
extract_iocs = extract


# ---------------------------------------------------------------------------
# Single value classification
# ---------------------------------------------------------------------------
#
# extract() answers "which indicators are somewhere in this text". classify_ioc
# answers a different question: "this whole field value is one indicator, so
# which type is it". An enrichment command has the second question and not the
# first, because a Splunk field holds one value and the command has to choose an
# endpoint for it.
#
# IT REUSES THE PATTERNS ABOVE RATHER THAN CARRYING ITS OWN. A second set of
# regular expressions for the same seven types would be a second answer to the
# same question, and tests/fixtures/ioc-corpus.json only guards the first one,
# so the second would be free to drift with nothing to catch it. What is reused
# is the compiled patterns, the type priority that decides ties, and the IPv4
# octet validator. Nothing is restated.
#
# ONE THING IS DELIBERATELY NOT REUSED: the noise suppression lists.
# _candidate() drops a bare domain on REPUTABLE_DOMAINS, and one whose last
# label is a file extension. Both are right for extraction, where the job is to
# surface what is interesting in a page of text and a page full of google.com
# links is noise, and docs/dashboards.md documents that behaviour against the
# Triage sample. The reputable list is wrong here. An operator who points an
# enrichment command at a domain field is asking about that exact value, and
# answering "not an indicator" for google.com would refuse to look up the one
# domain this repository holds a recorded platform verdict for:
# tests/fixtures/search-url-recorded.json is google.com, answered 200 with a
# polyscore of its own. Suppression is an extraction policy. It is not a
# statement about what a value is.
#
# THE DOMAIN RULE IS SPLIT BY AUDIENCE FOR THE SAME REASON, and this is the
# second and larger divergence. ALLOWED_TLDS is a curated 81-entry list, not a
# public suffix list, and it is the right shape for extract(): scanning a page
# or an event, an unrecognised final label is far more often a filename or a
# version string than a host, so the allowlist buys precision on text nobody
# asked about. It is the wrong shape here. An operator typing a value into
# polyswarmsearch has already asserted that the value is an indicator, and the
# allowlist has no entry for .ly, .si, or the several hundred other live TLDs it
# omits, so it turns a legitimate FQDN into "not an indicator" and the analyst
# reads an unknown that the platform was never asked about.
#
# The two failure modes are not symmetric, which is what decides the rule:
#
#   a wrong route   costs one lookup that comes back 204 and is cached for an
#                   hour, and the note field says the platform has not seen it
#   a wrong refusal FABRICATES an unknown for a real domain, with no lookup
#                   behind it and nothing in the row to say a lookup never
#                   happened
#
# So classification asks whether the value is STRUCTURALLY PLAUSIBLE as a host
# to look up, not whether its final label is on a curated list: two or more
# labels, each label a legal DNS label, and a final label that is alphabetic and
# of a length a TLD actually takes. Two classes of value are then refused
# outright, because for them a lookup cannot mean anything rather than merely
# being unlikely to hit: a terminal label on NON_ROUTABLE_TLDS, and an
# all-numeric host. The filename guard stays, because ALLOWED_TLDS used to
# enforce it implicitly and a filename is not a host by any reading.

# Terminal labels a global lookup can never answer for, so an enrichment request
# ending in one is refused rather than routed. RFC 6761 reserves example,
# invalid, localhost and test; RFC 6762 and the multicast DNS ecosystem take
# local; arpa is the reverse-mapping tree. internal, lan, home and corp are the
# de facto private-network names handed out by cloud private zones, consumer
# routers and directory services, which is where the AWS-internal FQDNs in the
# regression rows come from. onion (RFC 7686) resolves inside Tor and needs no
# lookup here.
NON_ROUTABLE_TLDS = (
    "internal", "local", "localhost", "arpa", "lan", "home", "corp",
    "invalid", "test", "example", "onion",
)

# One DNS label, whole: 1 to 63 characters, alphanumeric with internal hyphens
# only. Same shape as _LABEL above, anchored at the end so a partial label is
# not a label.
_LOOKUP_LABEL_RE = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", re.ASCII
)

# A final label: letters only, and a length a real TLD takes. The shortest live
# TLD is two characters and the longest is comfortably inside 24.
_LOOKUP_TLD_RE = re.compile(r"[a-z]{2,24}\Z", re.ASCII)


def _is_plausible_lookup_host(host):
    """True when a refanged, lowercased value is shaped like a host to look up.

    The classification-only domain rule. Structural, deliberately not the
    ALLOWED_TLDS allowlist extract() uses; see the note above for why the two
    audiences get different rules.

    :param host: a refanged, lowercased candidate value.
    :returns: True when the value may be routed as a domain.
    """
    if _DIGITS_ONLY_RE.match(host.replace(".", "")) is not None:
        # An all-numeric host is an address or garbage, never a name. The ip
        # branch has already had its turn and declined by the time this runs,
        # so what reaches here is 999.999.999.999 and its relatives.
        return False

    labels = host.split(".")
    if len(labels) < 2:
        # A single label is a short name off a local resolver, a word, or a
        # truncated value. None of them is a domain a global lookup answers for.
        return False

    for label in labels:
        if _LOOKUP_LABEL_RE.match(label) is None:
            return False

    tld = labels[-1]
    if _LOOKUP_TLD_RE.match(tld) is None:
        return False
    if tld in NON_ROUTABLE_TLDS:
        return False
    if tld in FILE_EXTENSIONS:
        # The one suppression list that carries over. ALLOWED_TLDS enforced this
        # implicitly, because the two lists are held disjoint by an invariant, so
        # keeping it is what stops report.docx becoming a routable host the day
        # the allowlist stops gating this path.
        return False

    return True


_COMPILED_BY_TYPE = dict(_COMPILED)

# Types tried in tie-break priority order, so that a value matching more than
# one pattern is classified as whatever extract()'s overlap resolution would
# have called it. Derived from _PRIORITY rather than written out, so a change to
# the priority table cannot leave this ordering behind.
_CLASSIFY_ORDER = tuple(
    sorted(
        (ioc_type for ioc_type, _ in _PATTERNS),
        key=lambda ioc_type: _PRIORITY[ioc_type],
    )
)


def classify_ioc(value):
    """Classify one whole field value as a single IOC type, or None.

    The value has to match a pattern end to end. A partial match is not a
    classification: a sentence that contains a URL is text to run extract()
    over, not a URL, and treating it as one would send a whole sentence to an
    API as though it were an indicator. Surrounding whitespace is stripped
    first, because a field value out of a log line routinely carries some.

    Defang forms classify, because the patterns themselves accept them, so
    evil[.]com is a domain and hxxp://evil[.]com is a url. That falls out of the
    reuse rather than being built for it, and it is not the expected input here:
    a value reaching this function through polyswarmextract has already been
    refanged. Nothing is rewritten on the way out. This function returns a type
    and only a type; the caller keeps the value it started with, which is what
    lets the caller decide whether folding its case is safe.

    THE DOMAIN TYPE DOES NOT USE THE ALLOWED_TLDS ALLOWLIST. It uses structural
    plausibility instead, because on this path a wrong route costs one lookup
    that comes back 204 and is cached for an hour, while a wrong refusal
    fabricates an unknown for a real domain with no lookup behind it. The
    allowlist omits .ly, .si and most of the live root zone, so it refused
    legitimate FQDNs. extract() keeps the allowlist unchanged; the corpus is its
    contract. The full rationale is in the note above this function and in
    decision D10.

    :param value: one field value.
    :returns: one of IOC_TYPES, or None when the value is not a single
        recognisable indicator.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    for ioc_type in _CLASSIFY_ORDER:
        if ioc_type == "domain":
            # The one type whose rule is not the compiled pattern, because the
            # pattern carries the extraction TLD allowlist inside it.
            if _is_plausible_lookup_host(refang_text(text).lower()):
                return "domain"
            continue

        match = _COMPILED_BY_TYPE[ioc_type].match(text)
        if match is None or match.end() != len(text):
            continue
        if ioc_type == "ip" and not _is_valid_ipv4(refang_text(text)):
            # The pattern admits 999.1.1.1 because it counts digits rather than
            # ranges. The octet validator is what makes a match an address, and
            # it is the same gate _candidate() applies.
            continue
        return ioc_type

    return None


# ---------------------------------------------------------------------------
# Extraction aware PII scrub
# ---------------------------------------------------------------------------
#
# High-confidence PII that is not itself an extracted indicator is replaced
# with a typed placeholder. This REDUCES PII in whatever the caller does next
# with the text. It is not full protection and must never be described as a
# compliance guarantee.
#
# Priority is redaction over preservation. A missed value is gone irreversibly
# once it leaves; an over-redacted indicator is recoverable, because extract()
# already found the indicators. On an uncertain classification, redact: a bare
# nine digit run is treated as a possible national identifier even though that
# catches some benign reference numbers.
#
# Extraction aware: extract() runs first and only PII that does not overlap an
# extracted indicator is redacted. Anything the engine flagged, a phishing
# sender address or a residential command and control address, is PRESERVED
# even when it also looks like PII, because dropping an indicator is the worse
# failure.
#
# Known gaps, which is why this reduces rather than protects:
#   - Names, street addresses and free text PII that no regular expression can
#     recognise are NOT redacted. This is the largest gap and it is inherent to
#     the approach.
#   - An address whose domain is on the TLD allowlist counts as an indicator
#     and is PRESERVED, so a victim address on a common TLD rides along. The
#     engine's flagging is the arbiter.
#   - Addresses in the IP sense are always extracted as indicators, so a victim
#     host is PRESERVED. There is no victim versus infrastructure judgement.
#   - Only common phone shapes are matched. A bare run of ten digits is not
#     treated as a phone number.
#   - National identifier formats beyond a bare nine digit run are not covered.
#
# The values removed are never returned separately, echoed, or written
# anywhere. Only the scrubbed string leaves scrub_pii.

# Typed placeholders. A reader still sees the sentence structure, so the
# surrounding prose stays useful while the value itself is gone.
_PLACEHOLDER = {
    "email": "[REDACTED-EMAIL]",
    "ssn": "[REDACTED-SSN]",
    "cc": "[REDACTED-CC]",
    "phone": "[REDACTED-PHONE]",
}

# The phone shapes this module recognises, as regex source.
#
# ONE LIST ON PURPOSE. Anything else that needs to know whether a page carries
# a phone number reads this, because a second copy of these patterns would be a
# second answer to the same question, and the one dangerous combination is a
# number that some other check counts and this scrub does not replace.
PHONE_PATTERN_SOURCES = (
    r"\b[0-9]{3}-[0-9]{3}-[0-9]{4}\b",
    r"\([0-9]{3}\) [0-9]{3}-[0-9]{4}",
    r"\+[0-9]{1,2} [0-9]{3} [0-9]{3} [0-9]{4}\b",
)

_SEPARATOR_RE = re.compile(r"[ -]", re.ASCII)


def luhn_valid(digits):
    """Luhn checksum over a candidate payment card number.

    Separators are stripped by the caller. A number that passes is treated as a
    card and redacted; one that fails is left alone, so a sixteen digit order
    number that is not a card survives.

    :param digits: a string of digits.
    :returns: True when the checksum passes.
    """
    if _DIGITS_ONLY_RE.match(digits) is None:
        return False
    total = 0
    double = False
    for index in range(len(digits) - 1, -1, -1):
        digit = ord(digits[index]) - 48
        if double:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        double = not double
    return total % 10 == 0


def _luhn_over_grouped(matched):
    return luhn_valid(_SEPARATOR_RE.sub("", matched))


# Each detector is (class, priority, source, validator). Detector order does
# not decide winners, priority does. Addresses first, because they can share a
# shape with an indicator and have to be tested for overlap, then the strongly
# formatted identifiers, then the looser phone shapes, then the bare nine digit
# national identifier guess last.
_DETECTORS = (
    ("email", 0, r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", None),
    ("ssn", 1, r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b", None),
    (
        "cc",
        2,
        r"\b[0-9]{4}[ -][0-9]{4}[ -][0-9]{4}[ -][0-9]{1,4}\b",
        _luhn_over_grouped,
    ),
    ("cc", 2, r"\b[0-9]{13,19}\b", luhn_valid),
    ("phone", 3, PHONE_PATTERN_SOURCES[0], None),
    ("phone", 3, PHONE_PATTERN_SOURCES[1], None),
    ("phone", 3, PHONE_PATTERN_SOURCES[2], None),
    ("ssn", 4, r"\b[0-9]{9}\b", None),
)

# The detectors are case sensitive in the original, so only the ASCII flag is
# applied here, not the case-insensitive one.
_COMPILED_DETECTORS = tuple(
    (pii_class, priority, re.compile(source, re.ASCII), validator)
    for pii_class, priority, source, validator in _DETECTORS
)


def _redaction_sort(span):
    """Sort key for redaction spans: longest, then priority, then earliest."""
    return (-(span[1] - span[0]), span[3], span[0])


def scrub_pii(text):
    """Replace high-confidence PII in text, preserving extracted indicators.

    :param text: the text to scrub.
    :returns: the scrubbed text. The removed values are never surfaced.
    """
    if text == "":
        return text

    # Extract first. Indicator spans are protected: a PII candidate that
    # overlaps any of them is preserved rather than redacted.
    indicators = extract(text)

    candidates = []
    for pii_class, priority, pattern, validator in _COMPILED_DETECTORS:
        for match in pattern.finditer(text):
            matched = match.group(0)
            if matched == "":
                continue
            if validator is not None and not validator(matched):
                continue
            start = match.start()
            candidates.append(
                (start, start + len(matched), pii_class, priority)
            )

    eligible = []
    for candidate in candidates:
        protected = False
        for indicator in indicators:
            if (
                candidate[0] < indicator["end"]
                and candidate[1] > indicator["start"]
            ):
                protected = True
                break
        if not protected:
            eligible.append(candidate)

    # Resolve overlaps among the redactions themselves, the same shape as the
    # extraction engine's own overlap resolution so the two behave predictably
    # together.
    eligible.sort(key=_redaction_sort)

    kept = []
    for candidate in eligible:
        clash = False
        for other in kept:
            if candidate[0] < other[1] and candidate[1] > other[0]:
                clash = True
                break
        if not clash:
            kept.append(candidate)

    if not kept:
        return text

    # Rebuild left to right, replacing each kept span with its placeholder.
    kept.sort()
    pieces = []
    cursor = 0
    for span in kept:
        pieces.append(text[cursor:span[0]])
        pieces.append(_PLACEHOLDER[span[2]])
        cursor = span[1]
    pieces.append(text[cursor:])
    return "".join(pieces)
