#!/usr/bin/env python
# coding=utf-8
"""
OAI - Ollama AI Integration for Splunk
A custom streaming command for running AI prompts against a local Ollama instance.
"""

import sys
import os
import requests
import configparser
import json
import re
import logging
import time
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

try:
    from splunklib import client, results
except Exception:
    client = None
    results = None


KNOWN_OPTIONS = {
    "type",
    "model",
    "prompt",
    "conversation_id",
    "web_search",
    "num_of_sites",
    "max_word",
    "debug",
    "persist",
    "persist_index",
    "investigate",
}


def normalize_argv(argv):
    """Coerce unknown key=value tokens into prompt=... to avoid option parser errors."""
    if not argv or len(argv) <= 1:
        return argv

    new_args = [argv[0]]
    pending_prompt_tokens = []

    def flush_pending():
        if pending_prompt_tokens:
            new_args.append(f"prompt={' '.join(pending_prompt_tokens)}")
            pending_prompt_tokens.clear()

    for token in argv[1:]:
        if '=' in token:
            name = token.split('=', 1)[0]
            if name not in KNOWN_OPTIONS:
                pending_prompt_tokens.append(token)
                continue

        flush_pending()
        new_args.append(token)

    flush_pending()
    return new_args


@Configuration()
class OAICommand(StreamingCommand):
    """
    Integrates with a local Ollama instance to provide AI capabilities within Splunk.

    Syntax:
        | oai "What is the weather like?"
        | oai model="qwen2.5:1.5b-instruct" prompt="What is the weather like?"
        | oai investigate=true "index=_internal summarize events"
    """

    config_file = os.path.join(os.path.dirname(__file__), '..', 'local', 'oai.conf')
    default_config_file = os.path.join(os.path.dirname(__file__), '..', 'default', 'oai.conf')
    legacy_config_file = os.path.join(os.path.dirname(__file__), '..', 'local', 'qai.conf')
    legacy_default_config_file = os.path.join(os.path.dirname(__file__), '..', 'default', 'qai.conf')

    type = Option(require=False, doc="Feature type")
    model = Option(require=False, doc="AI model to use")
    prompt = Option(require=False, doc="Input prompt")
    conversation_id = Option(require=False, doc="Conversation ID for context")
    web_search = Option(require=False, default=False, validate=validators.Boolean())
    num_of_sites = Option(require=False, default=1, validate=validators.Integer())
    max_word = Option(require=False, default=500, validate=validators.Integer())
    debug = Option(require=False, default=False, validate=validators.Boolean())
    persist = Option(require=False, default=False, validate=validators.Boolean())
    persist_index = Option(require=False, doc="Index to persist events when persist=true")
    investigate = Option(require=False, default=False, validate=validators.Boolean(),
                         doc="Run an index investigation based on the prompt")

    warnings = []
    errors = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qlogger = self.setup_logger()

    def _protocol_v2_option_parser(self, arg):
        """Handle quoted strings containing '=' signs properly."""
        stripped = arg.strip()
        if stripped.startswith('"') or stripped.startswith("'"):
            return [arg]

        if '=' not in arg:
            return [arg]

        parts = arg.split('=', 1)
        name = parts[0]

        if not name or ' ' in name or not name[0].isalpha():
            return [arg]

        if name not in KNOWN_OPTIONS:
            return [arg]

        return parts

    class EpochFormatter(logging.Formatter):
        def format(self, record):
            ts = int(record.created)
            level = record.levelname.upper()
            message = record.getMessage()
            return f"{ts} [{level}], oai.log, {message}"

    def setup_logger(self, config_section=None):
        level_str = "DEBUG"
        if config_section and config_section.get('log_level'):
            level_str = config_section.get('log_level').upper()

        level = getattr(logging, level_str, logging.DEBUG)

        logger = logging.getLogger('oai')
        logger.setLevel(level)
        logger.propagate = False

        if not logger.handlers:
            log_root = os.path.join(os.environ.get('SPLUNK_HOME', '/opt/splunk'), 'var', 'log', 'splunk')
            try:
                os.makedirs(log_root, exist_ok=True)
                handler = logging.FileHandler(os.path.join(log_root, 'oai.log'))
                handler.setFormatter(self.EpochFormatter())
                logger.addHandler(handler)
            except PermissionError:
                handler = logging.StreamHandler(sys.stderr)
                handler.setFormatter(self.EpochFormatter())
                logger.addHandler(handler)

        for handler in logger.handlers:
            handler.setLevel(level)

        return logger

    def format_response(self, text):
        """Format the response text for better readability."""
        try:
            text = re.sub(r'(\d+\.)', r'\n\1', text)
            text = re.sub(r'\*\*([^*]+)\*\*:', r'\n**\1**:\n', text)
            text = re.sub(r'\s\*([^*]+)\*:', r'\n*\1*:', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r'\s*([.,])\s*', r'\1 ', text)
            return text.strip()
        except Exception as e:
            self.errors.append(f"Error formatting response: {e}")
            return text

    def load_config(self):
        """Load configuration from oai.conf (with legacy qai.conf fallback)."""
        sources = []
        if os.path.exists(self.config_file):
            sources.append(self.config_file)
        elif os.path.exists(self.legacy_config_file):
            sources.append(self.legacy_config_file)
            self.warnings.append("Using legacy qai.conf; please save settings to write local/oai.conf")
        if not sources and os.path.exists(self.default_config_file):
            sources.append(self.default_config_file)
            self.warnings.append(
                "Using default configuration; please save settings in the setup page to generate local/oai.conf"
            )
        elif not sources and os.path.exists(self.legacy_default_config_file):
            sources.append(self.legacy_default_config_file)
            self.warnings.append("Using legacy default/qai.conf; please resave to create default/oai.conf")
        if not sources:
            self.errors.append(
                f"Configuration file not found: {self.config_file} (and no default/oai.conf or legacy qai.conf)"
            )
            return None

        config = configparser.ConfigParser()
        config.read(sources)

        for section in ('ollama', '1min.ai'):
            if section in config:
                section_proxy = config[section]
                if section == '1min.ai':
                    self.warnings.append(
                        "Using legacy 1min.ai configuration; re-run setup to save Ollama settings."
                    )
                    legacy_base = section_proxy.get('base_url', '')
                    if '1min.ai' in legacy_base:
                        section_proxy['base_url'] = 'http://localhost:11434'

                if 'default_model' not in section_proxy:
                    section_proxy['default_model'] = section_proxy.get(
                        'default_chat_model', 'qwen2.5:1.5b-instruct'
                    )

                self.qlogger = self.setup_logger(section_proxy)
                self.qlogger.debug("Loaded configuration section '%s'", section)
                return section_proxy

        self.errors.append("Ollama configuration section missing")
        return None

    def persist_event(self, raw_text, index_name, event_time, verify=True, user=None):
        """Persist the raw event to a Splunk index via the receivers API."""
        try:
            searchinfo = getattr(self, '_metadata', None)
            searchinfo = getattr(searchinfo, 'searchinfo', None)
            session_key = getattr(searchinfo, 'session_key', None)
            if not session_key:
                self.qlogger.warning("persist=true but no session_key available; skipping persistence")
                return

            uri = getattr(searchinfo, 'splunkd_uri', None)
            if uri:
                parsed = urlparse(uri)
                host_port = parsed.netloc or f"{parsed.hostname}:{parsed.port or '8089'}"
                scheme = parsed.scheme or 'https'
                url = f"{scheme}://{host_port}/services/receivers/simple"
            else:
                mgmt_host = os.environ.get('SPLUNKD_HOST', '127.0.0.1')
                mgmt_port = os.environ.get('SPLUNKD_PORT', '8089')
                scheme = os.environ.get('SPLUNKD_PROTOCOL', 'https')
                url = f"{scheme}://{mgmt_host}:{mgmt_port}/services/receivers/simple"

            params = {'output_mode': 'json'}
            if index_name:
                params['index'] = index_name
            if event_time:
                params['time'] = str(event_time)

            headers = {'Authorization': f'Splunk {session_key}'}

            payload = raw_text
            if user:
                payload = f"user={user} {raw_text}"

            self.qlogger.debug(
                "Persisting event len=%s index=%s time=%s url=%s verify=%s",
                len(payload), index_name, event_time, url, verify,
            )

            try:
                resp = requests.post(
                    url, params=params,
                    data=payload.encode('utf-8', errors='replace'),
                    headers=headers, verify=verify, timeout=10,
                )
            except requests.exceptions.SSLError as ssl_exc:
                self.qlogger.warning("Persist TLS failure (%s); retrying with verify=False", ssl_exc)
                resp = requests.post(
                    url, params=params,
                    data=payload.encode('utf-8', errors='replace'),
                    headers=headers, verify=False, timeout=10,
                )
            if resp.status_code >= 300:
                self.qlogger.warning("Failed to persist event status=%s body=%s", resp.status_code, resp.text)
            else:
                self.qlogger.debug("Persisted event status=%s", resp.status_code)
        except Exception as exc:
            self.qlogger.error("Error persisting event: %s", exc)

    def prepare_payload(self, config, prompt_text=None):
        """Prepare the API payload based on command parameters and configuration."""
        if not self.prompt and not self.model and len(self.fieldnames) > 0:
            self.prompt = self.fieldnames[0]

        model = (
            self.model
            or config.get('default_model')
            or config.get('default_chat_model')
            or 'qwen2.5:1.5b-instruct'
        )

        effective_prompt = prompt_text if prompt_text is not None else (self.prompt if self.prompt else "")
        if effective_prompt is None:
            effective_prompt = ""
        if not isinstance(effective_prompt, str):
            effective_prompt = str(effective_prompt)

        self.qlogger.debug("Prepared payload with model=%s prompt_len=%s", model, len(effective_prompt))

        return {
            "model": model,
            "prompt": effective_prompt,
            "stream": False,
        }

    def stream(self, records):
        """Main processing method for the command."""
        self.qlogger.debug(
            "OAI stream invoked: investigate=%s prompt=%r fieldnames=%r",
            self.investigate, self.prompt, getattr(self, 'fieldnames', None)
        )

        if not self.prompt and self.fieldnames:
            self.prompt = self.fieldnames[0]
            self.qlogger.debug("Extracted prompt from fieldnames: %r", self.prompt)

        config = self.load_config()
        if not config:
            error_message = '; '.join(self.errors) if self.errors else 'Unknown configuration error'
            self.trigger_errors()

            yielded = False
            for record in records:
                yielded = True
                record["error"] = error_message
                yield record
            if not yielded:
                yield {"error": error_message}
            return

        effective_persist_index = self.persist_index or config.get('persist_index', 'oai')

        def process_record(record):
            orig_raw = record.get("_raw", "")
            if orig_raw is None:
                orig_raw = ""
            if not isinstance(orig_raw, str):
                orig_raw = str(orig_raw)

            def merged_raw(text):
                if orig_raw:
                    return f"{text}\n\n---\n{orig_raw}"
                return text

            if "_time" in record and record.get("_time") is not None:
                try:
                    event_time = int(float(record.get("_time")))
                except Exception:
                    event_time = int(time.time())
            else:
                event_time = int(time.time())
                record["_time"] = event_time
            user = getattr(getattr(self, '_metadata', None), 'searchinfo', None)
            record["user"] = getattr(user, 'username', '') if user else ''

            base_prompt = self.prompt or ""
            if orig_raw:
                event_text = orig_raw
            else:
                event_text = ""

            if base_prompt and event_text:
                prompt_text = f"{base_prompt}\n\nContext from event:\n{event_text}"
            elif base_prompt:
                prompt_text = base_prompt
            else:
                prompt_text = event_text or ""

            if self.debug:
                record.update({
                    "type": self.type,
                    "model": self.model,
                    "payload": self.prepare_payload(config, prompt_text)
                })
                record["_raw"] = merged_raw(json.dumps(record["payload"], ensure_ascii=False))

                if self.persist:
                    self.persist_event(
                        raw_text=record["_raw"],
                        index_name=effective_persist_index,
                        event_time=event_time,
                        verify=config.getboolean('verify', True) if 'verify' in config else True,
                        user=record.get("user", ""),
                    )
                return record

            base_url = config.get('base_url', 'http://localhost:11434').rstrip('/')
            timeout = int(config.get('timeout', '60'))
            verify = config.getboolean('verify', True) if 'verify' in config else True

            url = f"{base_url}/api/generate"
            payload = self.prepare_payload(config, prompt_text)

            response = self.rest(url=url, payload=payload, timeout=timeout, verify=verify)

            if response:
                self.qlogger.debug("Received response status=%s", response.status_code)
                record["status_code"] = response.status_code
                try:
                    response_json = response.json()
                except ValueError:
                    response_json = None

                if response.status_code < 200 or response.status_code >= 300:
                    record["error"] = response.text
                    record["_raw"] = merged_raw(response.text)
                    self.qlogger.warning(
                        "Non-2xx from Ollama status=%s body=%s",
                        response.status_code, response.text,
                    )

                    if self.persist:
                        self.persist_event(
                            raw_text=record.get("_raw", ""),
                            index_name=effective_persist_index,
                            event_time=event_time,
                            verify=config.getboolean('verify', True) if 'verify' in config else True,
                            user=record.get("user", ""),
                        )
                    self.trigger_warnings()
                    return record

                if response_json:
                    if isinstance(response_json, dict):
                        response_text = response_json.get("response", response_json)
                        if isinstance(response_text, str):
                            response_text = self.format_response(response_text)
                        record["response"] = response_text
                        record["_raw"] = merged_raw(response_text)
                        if "context" in response_json:
                            record["context"] = response_json["context"]
                    else:
                        record["response"] = self.format_response(str(response_json))
                        record["_raw"] = merged_raw(record["response"])
                else:
                    record["response"] = self.format_response(response.text)
                    record["_raw"] = merged_raw(record["response"])

                if self.persist:
                    self.persist_event(
                        raw_text=record.get("_raw", ""),
                        index_name=effective_persist_index,
                        event_time=event_time,
                        verify=config.getboolean('verify', True) if 'verify' in config else True,
                        user=record.get("user", ""),
                    )
            else:
                error_message = '; '.join(self.errors) if self.errors else 'No response received from Ollama'
                record["error"] = error_message
                record["_raw"] = merged_raw(error_message)
                self.qlogger.error("%s", error_message)
                self.trigger_errors()

                if self.persist:
                    self.persist_event(
                        raw_text=record.get("_raw", ""),
                        index_name=effective_persist_index,
                        event_time=event_time,
                        verify=config.getboolean('verify', True) if 'verify' in config else True,
                        user=record.get("user", ""),
                    )

            return record

        yielded = False
        for record in records:
            yielded = True
            yield process_record(record)

        if not yielded:
            prompt_text = self.prompt or (self.fieldnames[0] if self.fieldnames else "")
            if self.investigate or (prompt_text and prompt_text.strip().lower().startswith("investigate")):
                yield self.investigate_index(config, prompt_text)
            else:
                yield process_record({})

    def rest(self, url, payload, timeout, verify):
        """Make HTTP requests to the Ollama API."""
        try:
            self.qlogger.debug("POST %s payload_keys=%s", url, list(payload.keys()))
            return requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
                verify=verify,
            )
        except requests.exceptions.RequestException as e:
            self.errors.append(f"HTTP request failed: {e}")
            self.qlogger.error("HTTP request failed: %s", e)
            return None

    def extract_index_from_prompt(self, prompt_text):
        """Extract the first index=... term from the prompt."""
        if not prompt_text:
            return None
        match = re.search(r"index=(\"([^\"]+)\"|'([^']+)'|(\S+))", prompt_text)
        if not match:
            return None
        return match.group(2) or match.group(3) or match.group(4)

    def extract_search_filters(self, prompt_text):
        """
        Extract all field=value pairs from the prompt for use in Splunk searches.

        Returns a tuple of (filter_string, llm_prompt):
          - filter_string: SPL filter like 'index=_internal sourcetype=splunkd log_level=ERROR'
          - llm_prompt: The remaining text for the LLM
        """
        if not prompt_text:
            return "", ""

        field_pattern = r'(\w+)=(\"[^\"]*\"|\'[^\']*\'|\S+)'

        filters = []
        remaining_text = prompt_text

        for match in re.finditer(field_pattern, prompt_text):
            full_match = match.group(0)
            field_name = match.group(1)

            skip_words = {'and', 'or', 'not', 'the', 'is', 'are', 'what', 'how', 'why', 'when', 'where', 'which'}
            if field_name.lower() in skip_words:
                continue

            filters.append(full_match)
            remaining_text = remaining_text.replace(full_match, '', 1)

        remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
        remaining_text = re.sub(r'^(and|or|then|also|please|now)\s+', '', remaining_text, flags=re.IGNORECASE).strip()

        filter_string = ' '.join(filters)

        self.qlogger.debug("Extracted search filters: %r, LLM prompt: %r", filter_string, remaining_text)

        return filter_string, remaining_text

    def get_time_bounds(self):
        """Return earliest/latest time bounds from search metadata if available."""
        searchinfo = getattr(getattr(self, '_metadata', None), 'searchinfo', None)
        earliest = getattr(searchinfo, 'earliest_time', None) if searchinfo else None
        latest = getattr(searchinfo, 'latest_time', None) if searchinfo else None
        return earliest, latest

    def connect_splunk_service(self, verify=True):
        """Create a Splunk service connection using the current session key."""
        if client is None:
            self.errors.append("splunklib client not available; install dependencies to use investigate mode")
            return None

        searchinfo = getattr(getattr(self, '_metadata', None), 'searchinfo', None)
        if not searchinfo:
            self.errors.append("No search metadata available; cannot run investigation")
            return None

        session_key = getattr(searchinfo, 'session_key', None)
        if not session_key:
            self.errors.append("Missing session_key; investigation mode requires an authenticated search context")
            return None

        uri = getattr(searchinfo, 'splunkd_uri', None)
        parsed = urlparse(uri) if uri else None

        host = parsed.hostname if parsed and parsed.hostname else os.environ.get('SPLUNKD_HOST', '127.0.0.1')
        port = parsed.port if parsed and parsed.port else int(os.environ.get('SPLUNKD_PORT', '8089'))
        scheme = parsed.scheme if parsed and parsed.scheme else os.environ.get('SPLUNKD_PROTOCOL', 'https')

        self.qlogger.debug("Connecting to Splunk service host=%s port=%s scheme=%s verify=%s", host, port, scheme, verify)

        try:
            service = client.connect(
                token=session_key,
                host=host,
                port=port,
                scheme=scheme,
                verify=verify,
            )
            return service
        except Exception as exc:
            self.errors.append(f"Failed to connect to Splunk service: {exc}")
            self.qlogger.error("Failed to connect to Splunk service: %s", exc)
            return None

    def run_oneshot(self, service, search_query, earliest=None, latest=None, count=0):
        """Run a oneshot search and return result rows."""
        if results is None:
            self.errors.append("splunklib results module not available; cannot run investigation searches")
            return []

        kwargs = {"count": count}
        if earliest:
            kwargs["earliest_time"] = str(earliest)
        if latest:
            kwargs["latest_time"] = str(latest)

        self.qlogger.debug("Running investigation search: %s kwargs=%s", search_query, kwargs)

        try:
            reader = results.ResultsReader(service.jobs.oneshot(search_query, **kwargs))
        except Exception as exc:
            self.errors.append(f"Investigation search failed: {exc}")
            self.qlogger.error("Investigation search failed: %s", exc)
            return []

        rows = []
        for item in reader:
            if isinstance(item, dict):
                rows.append(item)
            elif isinstance(item, results.Message):
                self.warnings.append(str(item))
        return rows

    def investigate_index(self, config, user_prompt):
        """Collect stats from Splunk and summarize with the model."""
        base_filter, llm_prompt = self.extract_search_filters(user_prompt)

        if not base_filter or 'index=' not in base_filter.lower():
            msg = "Investigate mode requires an index=... term in the prompt"
            self.errors.append(msg)
            return {"error": msg, "_raw": msg}

        verify = config.getboolean('verify', True) if 'verify' in config else True
        service = self.connect_splunk_service(verify=verify)
        if not service:
            msg = '; '.join(self.errors) if self.errors else "Unable to connect to Splunk service"
            return {"error": msg, "_raw": msg}

        earliest, latest = self.get_time_bounds()
        base_search = f"search {base_filter}"

        self.qlogger.debug("Investigation base search: %s", base_search)

        stats_rows = self.run_oneshot(
            service,
            f"{base_search} | stats count as total_events earliest(_time) as earliest latest(_time) as latest",
            earliest, latest, count=0,
        )
        total_events = 0
        earliest_ts = None
        latest_ts = None
        if stats_rows:
            row = stats_rows[0]
            try:
                total_events = int(float(row.get('total_events', 0)))
            except Exception:
                total_events = 0
            try:
                earliest_ts = float(row.get('earliest')) if row.get('earliest') is not None else None
            except Exception:
                earliest_ts = None
            try:
                latest_ts = float(row.get('latest')) if row.get('latest') is not None else None
            except Exception:
                latest_ts = None

        duration = None
        eps = None
        if earliest_ts is not None and latest_ts is not None and latest_ts > earliest_ts:
            duration = latest_ts - earliest_ts
            eps = total_events / duration if duration > 0 else None

        top_sourcetypes = [
            {"sourcetype": r.get('sourcetype'), "count": r.get('count')}
            for r in self.run_oneshot(
                service, f"{base_search} | top limit=5 sourcetype",
                earliest, latest, count=0,
            )
            if r.get('sourcetype')
        ]

        top_sources = [
            {"source": r.get('source'), "count": r.get('count')}
            for r in self.run_oneshot(
                service, f"{base_search} | top limit=5 source",
                earliest, latest, count=0,
            )
            if r.get('source')
        ]

        sample_logs = [
            {
                "time": r.get('_time'),
                "host": r.get('host'),
                "sourcetype": r.get('sourcetype'),
                "source": r.get('source'),
                "raw": r.get('_raw'),
            }
            for r in self.run_oneshot(
                service, f"{base_search} | head 5 | table _time host sourcetype source _raw",
                earliest, latest, count=5,
            )
        ]

        effective_llm_prompt = llm_prompt if llm_prompt else "Summarize the index"

        analysis_prompt = (
            "You are investigating a Splunk index and need to summarize findings for an operator. "
            "Use the collected metrics to report total events, events per second, typical logs, and a brief summary.\n"
            f"Search filter used: {base_filter}\n"
            f"User request: {effective_llm_prompt}\n"
            f"Total events: {total_events}\n"
            f"Earliest _time: {earliest_ts}\n"
            f"Latest _time: {latest_ts}\n"
            f"Events per second: {eps}\n"
            f"Top sourcetypes: {top_sourcetypes}\n"
            f"Top sources: {top_sources}\n"
            f"Sample logs: {sample_logs}\n"
            "Provide a concise bullet summary with: (1) total events and EPS, (2) dominant sourcetypes/sources, "
            "(3) a short description of typical logs, (4) any anomalies to look at next."
        )

        base_url = config.get('base_url', 'http://localhost:11434').rstrip('/')
        timeout = int(config.get('timeout', '60'))
        payload = self.prepare_payload(config, analysis_prompt)

        response = self.rest(
            url=f"{base_url}/api/generate",
            payload=payload,
            timeout=timeout,
            verify=verify,
        )

        record = {
            "search_filter": base_filter,
            "total_events": total_events,
            "events_per_second": eps,
            "earliest": earliest_ts,
            "latest": latest_ts,
            "top_sourcetypes": top_sourcetypes,
            "top_sources": top_sources,
            "sample_logs": sample_logs,
            "analysis_payload": payload,
        }

        if response:
            try:
                response_json = response.json()
            except ValueError:
                response_json = None

            if response.status_code >= 300:
                record["error"] = response.text
                record["status_code"] = response.status_code
                record["_raw"] = response.text
                self.qlogger.warning(
                    "Investigation call returned non-2xx status=%s body=%s",
                    response.status_code, response.text,
                )
                return record

            if response_json and isinstance(response_json, dict) and "response" in response_json:
                record["response"] = self.format_response(response_json.get("response", ""))
            else:
                record["response"] = self.format_response(response.text)
            record["_raw"] = record["response"]
            if response_json and isinstance(response_json, dict) and "context" in response_json:
                record["context"] = response_json["context"]
        else:
            msg = '; '.join(self.errors) if self.errors else 'No response received from Ollama during investigation'
            record["error"] = msg
            record["_raw"] = msg
            self.qlogger.error("%s", msg)

        return record

    def trigger_warnings(self):
        """Write any accumulated warnings."""
        if self.warnings:
            for warning in self.warnings:
                self.write_warning(warning)

    def trigger_errors(self):
        """Write any accumulated errors."""
        if self.errors:
            for error in self.errors:
                self.write_error(error)


sys.argv = normalize_argv(sys.argv)
dispatch(OAICommand, sys.argv, sys.stdin, sys.stdout, __name__, allow_empty_input=True)
