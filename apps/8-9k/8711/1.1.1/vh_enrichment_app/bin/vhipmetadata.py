#!/usr/bin/env python3
"""VH IP-metadata direct-API investigation command (generating).

Usage:  | vhipmetadata ip="<ip>"

Calls the VisionHeight /ip/metadata API directly for a single IP and emits
one event with vh_* fields. This is the investigation companion to the
cache-only enrichment command vhip — it intentionally does NOT touch the
KV Store, does NOT cache, and does NOT enrich existing events.

Output semantics:
  vh_status = found         | API record applied; vh_source=api
  vh_status = not_found     | API returned an empty list
  vh_status = invalid_input | ip argument missing/empty/not a valid IP
  vh_error  = <reason>      | real failure (auth_error, api_timeout,
                              api_http_<code>, internal_error)
"""

import json
import os
import socket
import ssl
import sys
import urllib.error
import urllib.request
from ipaddress import ip_address

# Vendored Splunk SDK lives under bin/lib/.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
# Also expose bin/ so `import vh_http` works no matter where splunkd
# invokes us from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
)
import vh_http  # noqa: E402


APP_NAME = "vh_enrichment_app"
# Route appended to the canonical API base URL (resolved at runtime via
# vh_http.load_api_base) to build the full request URL.  Keeping the
# route literal here puts the wire path next to the code that knows the
# server contract; the host comes from Setup-UI config.
METADATA_ROUTE = "/ip/metadata"
API_TIMEOUT_SEC = 15
CRED_TIMEOUT_SEC = 10


# API field -> output field. Scalars and arrays both go through this map;
# nested pulse_origin is unpacked separately in _shape_event.
_OUTPUT_FIELDS = (
    ("ip_country",           "vh_ip_country"),
    ("ip_company",           "vh_ip_company"),
    ("isp",                  "vh_isp"),
    ("entity_type",          "vh_entity_type"),
    ("risk",                 "vh_risk"),
    ("is_tor",               "vh_is_tor"),
    ("is_residential_proxy", "vh_is_residential_proxy"),
    ("is_commercial_vpn",    "vh_is_commercial_vpn"),
    ("ports",                "vh_ports"),
    ("total_domains",        "vh_total_domains"),
    ("tags",                 "vh_tags"),
    ("has_linked_ips",       "vh_has_linked_ips"),
)


@Configuration(distributed=False)
class VhIpMetadataCommand(GeneratingCommand):

    ip = Option(
        doc="IP address to look up via the VisionHeight direct API.",
        require=True,
    )

    # ---- credential retrieval -------------------------------------------

    def _get_api_key(self):
        """Same retrieval the modular input uses: wildcard-owner under the
        app namespace via raw splunkd REST. Avoids splunklib's
        storage_passwords collection which requires a non-wildcard
        namespace and would break if this command is invoked from a saved
        search whose app context is not vh_enrichment_app.
        """
        session_key = self._metadata.searchinfo.session_key
        splunkd_uri = self._metadata.searchinfo.splunkd_uri
        path = (
            "/servicesNS/-/{app}/storage/passwords/{app}:api_key:?output_mode=json"
            .format(app=APP_NAME)
        )
        ctx = ssl.create_default_context()
        cafile = os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem")
        if os.path.exists(cafile):
            ctx.load_verify_locations(cafile=cafile)
        ctx.check_hostname = False
        req = urllib.request.Request(
            url="{base}{p}".format(base=splunkd_uri, p=path),
            headers={"Authorization": "Splunk {tok}".format(tok=session_key)},
            method="GET",
        )
        try:
            # splunkd loopback — explicitly proxy_cfg=None so any
            # configured corporate proxy or HTTP_PROXY env var is bypassed.
            with vh_http.urlopen(req, context=ctx, timeout=CRED_TIMEOUT_SEC,
                                 proxy_cfg=None) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            self.logger.error("vhipmetadata: api_key fetch HTTP %s", e.code)
            return None
        except Exception as e:  # noqa: BLE001
            self.logger.exception("vhipmetadata: api_key fetch failed: %s", e)
            return None
        entries = data.get("entry") or []
        if not entries:
            return None
        return entries[0].get("content", {}).get("clear_password")

    # ---- proxy config (search-command scope) ----------------------------

    def _splunkd_loopback_ctx(self):
        """SSLContext sized for the splunkd loopback (self-signed by default).

        Same construction proxy and endpoint loaders need; kept in one
        place so both helpers honour SPLUNK_HOME's CA bundle when present
        and degrade to system-default trust otherwise.
        """
        ctx = ssl.create_default_context()
        cafile = os.path.join(os.environ.get("SPLUNK_HOME", ""), "etc/auth/cacert.pem")
        if os.path.exists(cafile):
            ctx.load_verify_locations(cafile=cafile)
        ctx.check_hostname = False
        return ctx

    def _load_proxy_cfg(self):
        """Read the outbound-proxy settings from KV + storage/passwords.

        Uses the same splunkd loopback the credential fetch uses; failures
        are tolerated (returns a disabled ProxyConfig) so a transient KV
        hiccup never breaks an investigation search outright.
        """
        return vh_http.load_proxy_config(
            session_key=self._metadata.searchinfo.session_key,
            splunkd_base=self._metadata.searchinfo.splunkd_uri,
            ssl_context=self._splunkd_loopback_ctx(),
            app_name=APP_NAME,
            logger=lambda m: self.logger.warning("vhipmetadata: %s", m),
        )

    def _load_api_base(self):
        """Resolve the canonical API base URL from KV (Setup UI value).

        Always returns a populated ApiBase — vh_http.load_api_base falls
        through to the shipped default on any KV/REST hiccup, so the
        request path never sees a None-typed URL.
        """
        return vh_http.load_api_base(
            session_key=self._metadata.searchinfo.session_key,
            splunkd_base=self._metadata.searchinfo.splunkd_uri,
            ssl_context=self._splunkd_loopback_ctx(),
            app_name=APP_NAME,
            logger=lambda m: self.logger.warning("vhipmetadata: %s", m),
        )

    def _load_tls_settings(self):
        """Resolve outbound-TLS trust settings from the same KV doc.

        Returns an OutboundTls value object; an inactive (empty path)
        result is the Splunk Cloud / standard public-CA default and
        produces a stock default ssl context downstream.
        """
        return vh_http.load_outbound_tls_settings(
            session_key=self._metadata.searchinfo.session_key,
            splunkd_base=self._metadata.searchinfo.splunkd_uri,
            ssl_context=self._splunkd_loopback_ctx(),
            app_name=APP_NAME,
            logger=lambda m: self.logger.warning("vhipmetadata: %s", m),
        )

    # ---- API call -------------------------------------------------------

    def _post_api(self, api_key, normalized_ip, proxy_cfg, api_base, tls_settings):
        """POST to the metadata endpoint. Returns (records, err) where err
        is None on success or one of: auth_error, api_timeout,
        api_http_<code>, tls_error, internal_error.

        `api_base` carries the Setup-UI-resolved canonical API base URL;
        the route is appended here so the wire request literal stays
        adjacent to the API contract that defines it.

        `tls_settings` is the OutboundTls value loaded from the same KV
        settings doc the modular input reads.  When the operator has
        configured a custom CA bundle, it is added to the default trust
        store via build_outbound_ssl_context — same semantics the modinput
        uses for ingestion, so an on-prem customer only configures TLS
        once and it covers both code paths.
        """
        body = json.dumps({"ip_addresses": [normalized_ip]}).encode("utf-8")
        req = urllib.request.Request(
            url=api_base.url + METADATA_ROUTE,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
            },
            data=body,
            method="POST",
        )
        ctx = vh_http.build_outbound_ssl_context(
            tls_settings,
            logger=lambda m: self.logger.warning("vhipmetadata: %s", m),
        )
        try:
            with vh_http.urlopen(req, context=ctx, timeout=API_TIMEOUT_SEC,
                                 proxy_cfg=proxy_cfg) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload, None
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return None, "auth_error"
            return None, "api_http_{code}".format(code=e.code)
        except socket.timeout:
            return None, "api_timeout"
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", None)
            if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
                return None, "api_timeout"
            # Surface TLS verification failures distinctly so an on-prem
            # operator can map vh_error=tls_error directly to the Setup
            # page's "Custom CA Bundle Path" knob.  The detailed reason
            # goes to the splunkd log via classify_outbound_tls_error;
            # the search event keeps a short stable token.
            tls_msg = vh_http.classify_outbound_tls_error(e)
            if tls_msg is not None:
                self.logger.error("vhipmetadata: %s", tls_msg)
                return None, "tls_error"
            self.logger.error("vhipmetadata: URL error: %s", e)
            return None, "internal_error"
        except Exception as e:  # noqa: BLE001
            self.logger.exception("vhipmetadata: unexpected API error: %s", e)
            return None, "internal_error"

    # ---- record shaping --------------------------------------------------

    @staticmethod
    def _shape_event(rec, normalized_ip):
        evt = {
            "ip": rec.get("ip", normalized_ip),
            "vh_status": "found",
            "vh_source": "api",
        }
        for src, dst in _OUTPUT_FIELDS:
            v = rec.get(src)
            if v is not None:
                evt[dst] = v
        pulse = rec.get("pulse_origin")
        if isinstance(pulse, dict):
            countries = pulse.get("countries")
            languages = pulse.get("languages")
            if countries is not None:
                evt["vh_pulse_origin_countries"] = countries
            if languages is not None:
                evt["vh_pulse_origin_languages"] = languages
        return evt

    # ---- generating entry point -----------------------------------------

    def generate(self):
        raw = (self.ip or "").strip()
        try:
            normalized = str(ip_address(raw))
        except (ValueError, TypeError):
            yield {"ip": raw, "vh_status": "invalid_input"}
            return

        api_key = self._get_api_key()
        if not api_key:
            yield {"ip": normalized, "vh_error": "auth_error"}
            return

        proxy_cfg    = self._load_proxy_cfg()
        api_base     = self._load_api_base()
        tls_settings = self._load_tls_settings()
        self.logger.info("vhipmetadata: %s | %s | %s",
                         proxy_cfg.debug_repr(), api_base.debug_repr(),
                         tls_settings.debug_repr())

        payload, err = self._post_api(api_key, normalized, proxy_cfg, api_base,
                                      tls_settings)
        if err is not None:
            yield {"ip": normalized, "vh_error": err}
            return

        if not isinstance(payload, list) or not payload:
            yield {"ip": normalized, "vh_status": "not_found"}
            return

        for rec in payload:
            if isinstance(rec, dict):
                yield self._shape_event(rec, normalized)


dispatch(VhIpMetadataCommand, sys.argv, sys.stdin, sys.stdout, __name__)
