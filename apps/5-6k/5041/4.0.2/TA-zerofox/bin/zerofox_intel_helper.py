"""UCC input helper for generic ZeroFox CTI intel (splunklib modular input)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from solnlib import conf_manager
from splunklib import modularinput as smi
from splunklib.modularinput import Event
from zerofox_intel_collect import collect_intel_for_stanza
from zerofox_intel_sources import IntelRegistry, resolve_intel_sources_path
from zerofox_proxy import build_proxies


def _ucc_conf_stanzas(bin_dir: Path) -> tuple[str, str, str]:
    gc_path = bin_dir.parent / "appserver" / "static" / "js" / "build" / "globalConfig.json"
    gc = json.loads(gc_path.read_text(encoding="utf-8"))
    meta = gc["meta"]
    addon_name = str(meta["name"])
    rest_root = str(meta["restRoot"])
    tail = rest_root[3:] if rest_root.startswith("TA_") else rest_root
    suffix = tail.lower()
    return addon_name, f"ta_{suffix}_account", f"ta_{suffix}_settings"


def _account_credentials(
    session_key: str,
    addon_name: str,
    account_conf: str,
    account_name: str,
) -> tuple[str, str]:
    realm = f"__REST_CREDENTIAL__#{addon_name}#configs/conf-{account_conf}"
    cfm = conf_manager.ConfManager(session_key, addon_name, realm=realm)
    stanza = cfm.get_conf(account_conf).get(account_name)
    user = stanza.get("username")
    pwd = stanza.get("password")
    if not user or not pwd:
        msg = f"Account {account_name!r} is missing username or password"
        raise ValueError(msg)
    return str(user), str(pwd)


def validate_input(definition: smi.ValidationDefinition) -> None:
    params = definition.parameters
    if not (params.get("account") or "").strip():
        msg = "Account is required"
        raise ValueError(msg)
    if not (params.get("intel_source") or "").strip():
        msg = "Intel source is required"
        raise ValueError(msg)


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter) -> None:
    bin_dir = Path(__file__).resolve().parent
    addon_name, account_conf, settings_conf = _ucc_conf_stanzas(bin_dir)
    yaml_path = resolve_intel_sources_path(__file__)
    registry = IntelRegistry.from_path(yaml_path)
    session_key = inputs.metadata["session_key"]
    checkpoint_dir = str(inputs.metadata.get("checkpoint_dir") or "")
    proxies = build_proxies(session_key, addon_name, settings_conf)

    for input_name, input_item in inputs.inputs.items():
        p = {str(k): v for k, v in dict(input_item).items()}
        account_name = (p.get("account") or "").strip()
        intel_source = (p.get("intel_source") or "").strip()
        if not account_name or not intel_source:
            event_writer.log(
                event_writer.ERROR,
                f"{input_name}: account and intel_source are required",
            )
            continue

        try:
            try:
                logger = __import__("logging").getLogger(__name__)
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=addon_name,
                    conf_name=settings_conf,
                )
                logger.setLevel(log_level)
            except Exception:
                pass

            username, password = _account_credentials(
                session_key,
                addon_name,
                account_conf,
                account_name,
            )
        except Exception as err:
            event_writer.log(event_writer.ERROR, f"{input_name}: credential error: {err}")
            continue

        api_base = os.environ.get("ZFOX_DEV_API_BASE", "https://api.zerofox.com")

        optional: dict[str, str] = {}
        if p.get("email_domain"):
            optional["email_domain"] = str(p.get("email_domain"))

        stanza_str = str(input_name)
        try:
            spec = registry.require(intel_source)
        except KeyError as err:
            event_writer.log(event_writer.ERROR, f"{input_name}: {err}")
            continue

        legacy_in = str(spec.get("legacy_modular_input") or "")
        legacy_full: list[str] = []
        if legacy_in and "://" in stanza_str:
            _, _, inst = stanza_str.partition("://")
            if inst:
                legacy_full = [f"{legacy_in}://{inst}"]

        def emit(raw: str, sourcetype: str, epoch: float, st: str) -> None:
            ev = Event(
                data=raw,
                stanza=st,
                time="%.3f" % epoch,
                sourcetype=sourcetype,
                index=p.get("index"),
                done=True,
            )
            event_writer.write_event(ev)

        try:
            collect_intel_for_stanza(
                registry=registry,
                intel_source=intel_source,
                splunk_stanza=stanza_str,
                checkpoint_dir=checkpoint_dir,
                api_base_url=api_base,
                username=username,
                password=password,
                optional_args=optional,
                emit=emit,
                log_error=lambda m: event_writer.log(event_writer.ERROR, m),
                log_debug=lambda m: event_writer.log(event_writer.DEBUG, m),
                proxies=proxies or None,
                legacy_checkpoint_stanzas=legacy_full or None,
            )
        except Exception as err:
            event_writer.log(
                event_writer.ERROR,
                f"{input_name}: collection failed: {err}",
            )
