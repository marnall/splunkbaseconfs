"""Checkbox value normalization for UCC-based REST handlers.

UCC React checkbox component (UCC 5.x, including 5.69.1 used by this add-on)
renders the checked state ONLY when the field value equals "1" or 1. Any
other representation — Python Title-case "True"/"False" (returned by Splunk
normTrueBool() for fields declared as <boolean> in .conf.spec), lower-case
"true"/"false", "yes"/"no", empty string, None — is treated as unchecked.

This module provides:

  * `coerce_bool_to_01(value)` — pure function: collapses any reasonable
    truthy/falsy representation to the strict "0"/"1" string contract.

  * `CheckboxNormalizerMixin` — mixin for splunktaucclib REST handlers.
    Subclasses set `CHECKBOX_FIELDS = (...)`; the mixin exposes
    `_normalize_payload()` (write path) and `_normalize_confinfo(confInfo)`
    (read path). Handlers wire these around the splunktaucclib super-calls.

Intended for `handleCreate`, `handleEdit`, `handleList` of:
  - elasticsearch_source (Inputs)
  - es_clusters (Configuration -> ES Clusters)
  - settings (Configuration -> Proxy)
"""

_TRUTHY_TOKENS = frozenset({"1", "true", "yes", "y", "t", "on"})


def coerce_bool_to_01(value):
    """Return "1" or "0" — never anything else.

    Accepts: bool, int (0/1), str ("1","0","true","false","True","False",
    "yes","no","on","off","y","n","t","f"), None, whitespace, unknown.
    Unknown / falsy / empty inputs collapse to "0" (safe default).
    """
    if value is None:
        return "0"
    if isinstance(value, bool):
        return "1" if value else "0"
    s = str(value).strip().lower()
    return "1" if s in _TRUTHY_TOKENS else "0"


class CheckboxNormalizerMixin:
    """Mixin to coerce checkbox-typed fields to '0'/'1' across the REST seam.

    Subclasses MUST define::

        CHECKBOX_FIELDS = ("field_a", "field_b", ...)

    Then wire the normalizers around splunktaucclib super-calls, e.g.::

        def handleCreate(self, confInfo):
            self._normalize_payload()
            super().handleCreate(confInfo)

        def handleEdit(self, confInfo):
            self._normalize_payload()
            super().handleEdit(confInfo)

        def handleList(self, confInfo):
            super().handleList(confInfo)
            self._normalize_confinfo(confInfo)
    """

    CHECKBOX_FIELDS = ()

    def _normalize_payload(self):
        """Coerce checkbox fields in incoming form payload to '0'/'1'."""
        caller_args = getattr(self, "callerArgs", None)
        data = getattr(caller_args, "data", None) if caller_args else None
        if not data:
            return
        for field_name in self.CHECKBOX_FIELDS:
            if field_name not in data:
                continue
            raw = data[field_name]
            if isinstance(raw, list):
                first = raw[0] if raw else None
                data[field_name] = [coerce_bool_to_01(first)]
            else:
                data[field_name] = coerce_bool_to_01(raw)

    def _normalize_confinfo(self, confInfo):
        """Coerce checkbox fields in outgoing confInfo (REST GET) to '0'/'1'."""
        if confInfo is None:
            return
        # splunktaucclib confInfo behaves dict-like; iterate stanza names.
        try:
            stanza_names = list(confInfo.keys())
        except AttributeError:
            return
        for stanza_name in stanza_names:
            stanza = confInfo[stanza_name]
            for field_name in self.CHECKBOX_FIELDS:
                if field_name in stanza:
                    stanza[field_name] = coerce_bool_to_01(stanza[field_name])
