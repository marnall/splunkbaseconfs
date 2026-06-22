#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, json, time, hashlib, ssl, socket
from collections import deque
import feedparser
import html
from bs4 import BeautifulSoup

import splunklib.modularinput as smi

APP_ID = "rss_feeder_for_splunk"
CHECKPOINT_BASE = os.path.join(os.environ.get("SPLUNK_HOME", "."), "var", "lib", APP_ID)
DEFAULT_HISTORY_SIZE = 500
DEFAULT_USER_AGENT = "RSSFeeder/1.0 (+Splunk Modular Input)"
DEFAULT_TIMEOUT = 20  # seconds

def clean_html(raw_html):
    if not raw_html:
        return ""
    return html.unescape(BeautifulSoup(raw_html, "html.parser").get_text())

class RSSFeeder(smi.Script):
    def get_scheme(self):
        scheme = smi.Scheme("RSS Feeder")
        scheme.description = "Fetch RSS/Atom feeds and index new items with checkpointing."
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        # Custom arguments only
        scheme.add_argument(smi.Argument("rss_url", title="RSS/Atom URL", required_on_create=True, required_on_edit=True))
        scheme.add_argument(smi.Argument("history_size", title="Checkpoint history size", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("verify_ssl", title="Verify SSL (true/false)", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("user_agent", title="HTTP User-Agent", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("proxy", title="HTTP proxy (host:port)", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("timeout", title="HTTP timeout (seconds)", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("clean_summary", title="Strip HTML from summary (true/false)", required_on_create=False, required_on_edit=False))
        scheme.add_argument(smi.Argument("include_raw_summary", title="Include raw HTML summary (true/false)", required_on_create=False, required_on_edit=False))

        return scheme

    def validate_input(self, definition):
        url = definition.parameters.get("rss_url", "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise Exception("rss_url must start with http:// or https://")

    def stream_events(self, inputs, ew):
        os.makedirs(CHECKPOINT_BASE, exist_ok=True)

        for input_name, params in inputs.inputs.items():
            try:
                self._poll_once(input_name, params, ew)
            except Exception as e:
                ew.log("ERROR", f"RSSFeeder: fatal input error for {input_name}: {e}")

    def _poll_once(self, input_name, params, ew):
        url = params.get("rss_url")
        index = params.get("index", "main")
        sourcetype = params.get("sourcetype", "rss:feed")

        history_size = int(params.get("history_size", DEFAULT_HISTORY_SIZE))
        verify_ssl = str(params.get("verify_ssl", "true")).lower() == "true"
        user_agent = params.get("user_agent", DEFAULT_USER_AGENT)
        proxy = params.get("proxy", "").strip()
        timeout = int(params.get("timeout", DEFAULT_TIMEOUT))
        clean_summary_flag = str(params.get("clean_summary", "true")).lower() == "true"
        include_raw_summary_flag = str(params.get("include_raw_summary", "false")).lower() == "true"

        cp_path = self._checkpoint_path(url)
        seen = self._load_checkpoint(cp_path, history_size)

        ew.log("INFO", f"RSSFeeder: start input={input_name} url={url} index={index} sourcetype={sourcetype}")

        try:
            feed = self._fetch_feed(url, user_agent, verify_ssl, proxy, timeout)
            new_count = 0

            for entry in getattr(feed, "entries", []):
                entry_id = self._entry_id(entry)
                if entry_id and entry_id in seen:
                    continue

                event_time = self._entry_time(entry)
                payload = self._event_payload(entry, url, clean_summary_flag, include_raw_summary_flag)

                event = smi.Event(
                    data=json.dumps(payload, ensure_ascii=False),
                    sourcetype=sourcetype,
                    index=index
                )
                if event_time is not None:
                    event.time = event_time

                ew.write_event(event)
                if entry_id:
                    seen.append(entry_id)
                new_count += 1

            self._save_checkpoint(cp_path, seen)
            ew.log("INFO", f"RSSFeeder: polled url={url} indexed_new={new_count} checkpoint_size={len(seen)}")

        except Exception as e:
            ew.log("ERROR", f"RSSFeeder: poll error url={url}: {e}")

    def _fetch_feed(self, url, user_agent, verify_ssl, proxy, timeout):
        kwargs = {"request_headers": {"User-Agent": user_agent}}

        if proxy:
            os.environ["http_proxy"] = proxy
            os.environ["https_proxy"] = proxy

        socket.setdefaulttimeout(timeout)

        if not verify_ssl:
            orig_create_default_context = ssl.create_default_context
            try:
                ssl.create_default_context = lambda *args, **kwargs: ssl._create_unverified_context()
                feed = feedparser.parse(url, **kwargs)
            finally:
                ssl.create_default_context = orig_create_default_context
        else:
            feed = feedparser.parse(url, **kwargs)

        if getattr(feed, "bozo", False):
            raise Exception(f"feed parsing issue: {getattr(feed, 'bozo_exception', 'unknown')}")
        return feed

    def _entry_id(self, entry):
        candidate = entry.get("id") or entry.get("guid") or entry.get("link")
        if candidate:
            return self._hash(candidate)
        title = entry.get("title", "")
        pub = entry.get("published", "") or entry.get("updated", "")
        combo = f"{title}|{pub}"
        return self._hash(combo) if combo.strip() else None

    def _hash(self, s):
        return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()

    def _entry_time(self, entry):
        tm = entry.get("published_parsed") or entry.get("updated_parsed")
        if tm:
            try:
                return int(time.mktime(tm))
            except Exception:
                return None
        return None

    def _event_payload(self, entry, source_url, clean_summary_flag, include_raw_summary_flag):
        summary_raw = entry.get("summary", "")
        summary_clean = clean_html(summary_raw) if clean_summary_flag else summary_raw

        # Normalize tags: always present, even if empty
        tags = []
        if "tags" in entry and entry.get("tags"):
            tags = [t.get("term") for t in entry.get("tags", []) if t.get("term")]

        payload = {
            "source_url": source_url,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "author": entry.get("author", ""),
            "published": entry.get("published", "") or entry.get("updated", ""),
            "summary": summary_clean,
            "tags": tags
        }
        if include_raw_summary_flag:
            payload["summary_raw"] = summary_raw
        return payload

    def _checkpoint_path(self, url):
        safe = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return os.path.join(CHECKPOINT_BASE, f"cp_{safe}.json")

    def _load_checkpoint(self, path, history_size):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    ids = json.load(f)
                return deque(ids, maxlen=history_size)
        except Exception:
            pass
        return deque([], maxlen=history_size)

    def _save_checkpoint(self, path, dq):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(list(dq), f)
        except Exception:
            pass

if __name__ == "__main__":
    sys.exit(RSSFeeder().run(sys.argv))
