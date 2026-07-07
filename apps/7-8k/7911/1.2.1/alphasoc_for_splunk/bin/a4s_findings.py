from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NamedTuple

from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(["etc", "apps", "alphasoc_for_splunk", "bin"]))

from a4slib import checkpoint
from a4slib.config import (
    ConfigError,
    CredentialError,
    get_api_key,
    get_api_url,
    get_findings_index,
)
from a4slib.http_client import AlphaSOCHttpClient, APIError
from a4slib.splunk_service import service_from_metadata
from a4slib.splunklib.modularinput import Event, EventWriter, Scheme, Script

if TYPE_CHECKING:
    from a4slib.splunklib.client import Service
    from a4slib.splunklib.modularinput import InputDefinition, ValidationDefinition

MAX_ITERATIONS: int = 100
MAX_WALLCLOCK_SECONDS: float = 600.0

_LOG_APP = "alphasoc_for_splunk"
_LOG_INPUT = "findings"


def _log(ew: EventWriter, severity: str, message: str, name: str, **fields: object) -> None:
    """Emit a structured log line: `<message> app=<app> input=<input> name=<name> [...]`.

    Enables `index=_internal app=alphasoc_for_splunk input=findings` queries
    for debugging.
    """
    pairs = " ".join(f"{k}={v}" for k, v in fields.items())
    suffix = f" {pairs}" if pairs else ""
    ew.log(severity, f"{message} app={_LOG_APP} input={_LOG_INPUT} name={name}{suffix}")


@dataclass
class RunContext:
    """Per-invocation context shared by every stanza in this run."""

    service: Service
    checkpoint_dir: str
    ew: EventWriter


@dataclass
class IngestConfig:
    """Parameters that stay constant across pagination iterations."""

    client: AlphaSOCHttpClient
    checkpoint_dir: str
    input_name: str
    short_name: str
    workspace_id: str
    index: str | None
    sourcetype: str


class PaginationResult(NamedTuple):
    iterations: int
    total_records: int
    # True when the loop exited with more pages still available (hit
    # MAX_ITERATIONS or MAX_WALLCLOCK_SECONDS) — next poll will resume.
    capped: bool
    failed: bool


class FindingsInput(Script):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AlphaSOC Findings")
        scheme.description = "This input polls the AlphaSOC Analytics Engine for OCSF-formatted findings."
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.streaming_mode = Scheme.streaming_mode_xml
        return scheme

    def validate_input(self, definition: ValidationDefinition) -> None:
        service = service_from_metadata(definition.metadata)
        try:
            get_api_key(service)
            get_api_url(service)
        except (CredentialError, ConfigError) as exc:
            msg = (
                f"AlphaSOC settings are not configured: {exc}. "
                "Open AlphaSOC for Splunk → Settings to complete the configuration."
            )
            raise ValueError(msg) from exc

    def stream_events(self, inputs: InputDefinition, ew: EventWriter) -> None:
        ctx = RunContext(
            service=service_from_metadata(inputs.metadata),
            checkpoint_dir=str(inputs.metadata.get("checkpoint_dir", "")),
            ew=ew,
        )

        for input_name, input_params in inputs.inputs.items():
            short = input_name.split("://", 1)[-1] if "://" in input_name else input_name
            try:
                self._run_input(ctx, input_name, short, input_params)
            except Exception as exc:  # noqa: BLE001  # per-stanza isolation
                _log(ew, EventWriter.ERROR, "input crashed", short, error=repr(exc))

    def _run_input(
        self,
        ctx: RunContext,
        input_name: str,
        short_name: str,
        input_params: dict[str, Any],
    ) -> None:
        ew = ctx.ew
        try:
            client = AlphaSOCHttpClient.from_service(ctx.service)
        except (CredentialError, ConfigError) as exc:
            _log(
                ew,
                EventWriter.ERROR,
                "settings not configured",
                short_name,
                error=repr(str(exc)),
            )
            return

        # Validate key + fetch workspace_id up front so a bad key fails fast
        # instead of churning through the pagination loop. Could be cached
        # by (api_key, base_url) later if this round-trip ever shows up.
        try:
            status = client.account_status()
        except APIError as exc:
            _log(
                ew,
                EventWriter.ERROR,
                "account status check failed; skipping poll",
                short_name,
                status_code=exc.status_code,
                error=repr(str(exc)),
            )
            return

        if status.get("expired") is True:
            _log(ew, EventWriter.ERROR, "API key has expired; skipping poll", short_name)
            return
        if status.get("registered") is False:
            _log(ew, EventWriter.ERROR, "API key is not registered; skipping poll", short_name)
            return

        workspace_id = str(status.get("workspaceID") or "").strip()
        if not workspace_id:
            _log(ew, EventWriter.ERROR, "account status missing workspaceID; skipping poll", short_name)
            return

        try:
            default_index = get_findings_index(ctx.service)
        except ConfigError:
            default_index = ""

        # None lets splunklib omit <index> entirely; "" would emit an empty
        # element and break indexing.
        resolved_index = (input_params.get("index") or default_index) or None

        config = IngestConfig(
            client=client,
            checkpoint_dir=ctx.checkpoint_dir,
            input_name=input_name,
            short_name=short_name,
            workspace_id=workspace_id,
            index=resolved_index,
            sourcetype=str(input_params.get("sourcetype") or "").strip(),
        )

        _log(ew, EventWriter.INFO, "poll start", short_name, workspace=workspace_id)
        result = self._pagination_loop(config, ew)
        _log(
            ew,
            EventWriter.INFO,
            "poll end",
            short_name,
            iterations=result.iterations,
            records=result.total_records,
            capped=result.capped,
            failed=result.failed,
        )

    def _pagination_loop(
        self,
        config: IngestConfig,
        ew: EventWriter,
    ) -> PaginationResult:
        start_time = time.monotonic()
        iterations = 0
        total_records = 0
        more = False

        while True:
            if iterations >= MAX_ITERATIONS:
                break
            if time.monotonic() - start_time > MAX_WALLCLOCK_SECONDS:
                break

            try:
                n, more = self._poll_once(config, ew)
            except APIError as exc:
                _log(
                    ew,
                    EventWriter.ERROR,
                    "API request failed",
                    config.short_name,
                    status_code=exc.status_code,
                    error=repr(str(exc)),
                )
                return PaginationResult(iterations, total_records, capped=False, failed=True)

            total_records += n
            iterations += 1
            if not more:
                break

        return PaginationResult(iterations, total_records, capped=more, failed=False)

    def _poll_once(
        self,
        config: IngestConfig,
        ew: EventWriter,
    ) -> tuple[int, bool]:
        follow = checkpoint.read_follow(config.checkpoint_dir, config.workspace_id, config.input_name)
        _log(ew, EventWriter.INFO, "read follow", config.short_name, follow=follow)

        records, next_follow, more = config.client.findings(follow=follow)

        for record in records:
            event_time = _event_time(record.get("time"))
            event = Event(
                data=json.dumps(record),
                index=config.index,
                sourcetype=config.sourcetype,
                time=event_time,
            )
            ew.write_event(event)

        if next_follow:
            _log(ew, EventWriter.INFO, "saving follow", config.short_name, follow=next_follow)
            checkpoint.write_follow(config.checkpoint_dir, config.workspace_id, config.input_name, next_follow)

        return len(records), more


def _event_time(raw: object) -> float | None:
    if isinstance(raw, (int, float)):
        return float(raw)
    return None


if __name__ == "__main__":
    sys.exit(FindingsInput().run(sys.argv))
