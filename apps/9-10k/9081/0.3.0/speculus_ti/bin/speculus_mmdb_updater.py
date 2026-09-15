#!/usr/bin/env python3
"""Speculus MMDB updater modular input.

The filename is load-bearing: Splunk derives a modular input's kind from the
script name in bin/, so this must stay in step with the [speculus_mmdb_updater]
stanzas in default/inputs.conf and README/inputs.conf.spec. (Unlike a custom
search command, inputs.conf has no `filename` key to point elsewhere.)

On each scheduled run, downloads the Speculus combined MMDB from the
configured endpoint (GET /v1/mmdb, Bearer auth) into the app's local/data/
directory. Uses the server's strong ETag for conditional GETs so an unchanged
database costs one 304 round-trip. The API key is moved into Splunk secure
storage (storage/passwords) on first run and masked in inputs.conf.
"""

import json
import os
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.request

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(APP_DIR, "bin", "lib"))

import maxminddb  # noqa: E402
from splunklib import client  # noqa: E402
from splunklib.modularinput import (  # noqa: E402
    Argument,
    Event,
    Scheme,
    Script,
)

APP_NAME = "speculus_ti"
KIND = "speculus_mmdb_updater"
MASK = "<encrypted>"
CRED_REALM = APP_NAME
MMDB_DIR = os.path.join(APP_DIR, "local", "data")
MMDB_PATH = os.path.join(MMDB_DIR, "speculus_combined.mmdb")


class SpeculusMMDBUpdater(Script):
    def get_scheme(self):
        scheme = Scheme("Speculus MMDB Updater")
        scheme.description = (
            "Downloads the Speculus combined threat intelligence database "
            "(MMDB) used by the | speculus search command."
        )
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        endpoint = Argument("endpoint_url")
        endpoint.title = "Endpoint URL"
        endpoint.description = (
            "Full URL of the Speculus MMDB download endpoint, "
            "e.g. https://mmdb.example.com/v1/mmdb"
        )
        endpoint.required_on_create = True
        scheme.add_argument(endpoint)

        api_key = Argument("api_key")
        api_key.title = "API key"
        api_key.description = (
            "Speculus API key. Stored in Splunk secure storage and masked "
            "here after the first run."
        )
        api_key.required_on_create = True
        scheme.add_argument(api_key)

        verify_ssl = Argument("verify_ssl")
        verify_ssl.title = "Verify TLS certificate"
        verify_ssl.description = "Set to 0 only for testing against self-signed endpoints."
        verify_ssl.data_type = Argument.data_type_boolean
        verify_ssl.required_on_create = False
        scheme.add_argument(verify_ssl)

        return scheme

    def validate_input(self, validation_definition):
        url = validation_definition.parameters.get("endpoint_url", "")
        if not url.startswith(("http://", "https://")):
            raise ValueError("endpoint_url must start with http:// or https://")

    # --- credential handling -------------------------------------------------

    def _service(self):
        return client.Service(
            token=self._input_definition.metadata["session_key"],
            scheme="https",
            host="localhost",
            port=8089,
            app=APP_NAME,
            owner="nobody",
        )

    def _secure_api_key(self, input_name, stanza_key, ew):
        """Return the real API key; migrate it to storage/passwords if needed.

        stanza_key is what inputs.conf currently holds: either the real key
        (first run after configuration) or MASK.
        """
        service = self._service()
        cred_name = input_name  # e.g. "speculus_mmdb_updater://default"

        if stanza_key and stanza_key != MASK:
            for storage_password in service.storage_passwords:
                if (
                    storage_password.realm == CRED_REALM
                    and storage_password.username == cred_name
                ):
                    storage_password.delete()
                    break
            service.storage_passwords.create(stanza_key, cred_name, CRED_REALM)

            # Mask the plaintext copy in inputs.conf.
            kind_input = service.inputs[input_name.split("://", 1)[1], KIND]
            kind_input.update(api_key=MASK)
            ew.log("INFO", "speculus_ti: api_key migrated to secure storage")
            return stanza_key

        for storage_password in service.storage_passwords:
            if (
                storage_password.realm == CRED_REALM
                and storage_password.username == cred_name
            ):
                return storage_password.clear_password
        raise ValueError(
            "API key not found in secure storage. Re-enter the api_key on the "
            "input to store it again."
        )

    # --- download ------------------------------------------------------------

    def _etag_path(self, checkpoint_dir):
        return os.path.join(checkpoint_dir, "mmdb_etag.json")

    def _load_etag(self, checkpoint_dir):
        try:
            with open(self._etag_path(checkpoint_dir)) as f:
                return json.load(f).get("etag", "")
        except (OSError, ValueError):
            return ""

    def _save_etag(self, checkpoint_dir, etag):
        with open(self._etag_path(checkpoint_dir), "w") as f:
            json.dump({"etag": etag, "saved_at": int(time.time())}, f)

    def _download(self, url, api_key, etag, verify_ssl):
        """Return (status, new_etag, bytes_written). status: 200 | 304."""
        headers = {"Authorization": "Bearer " + api_key}
        if etag and os.path.isfile(MMDB_PATH):
            headers["If-None-Match"] = etag
        request = urllib.request.Request(url, headers=headers)

        context = None
        if url.startswith("https://"):
            context = ssl.create_default_context()
            if not verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE

        try:
            response = urllib.request.urlopen(request, timeout=600, context=context)
        except urllib.error.HTTPError as err:
            if err.code == 304:
                return 304, etag, 0
            body = err.read(200).decode("utf-8", "replace")
            raise ValueError("download failed: HTTP %d %s" % (err.code, body))

        os.makedirs(MMDB_DIR, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=MMDB_DIR, suffix=".mmdb.tmp")
        written = 0
        try:
            with os.fdopen(fd, "wb") as tmp:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
                    written += len(chunk)

            # Refuse to install a file that doesn't open as an MMDB.
            probe = maxminddb.open_database(tmp_path, mode=maxminddb.MODE_AUTO)
            probe.close()

            os.replace(tmp_path, MMDB_PATH)
        except Exception:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

        return 200, response.headers.get("ETag", ""), written

    # --- entry point ----------------------------------------------------------

    def stream_events(self, inputs, ew):
        checkpoint_dir = inputs.metadata["checkpoint_dir"]
        for input_name, params in inputs.inputs.items():
            try:
                url = params["endpoint_url"].strip()
                verify_ssl = str(params.get("verify_ssl", "1")).lower() not in (
                    "0",
                    "false",
                    "f",
                    "no",
                )
                api_key = self._secure_api_key(
                    input_name, params.get("api_key", ""), ew
                )

                etag = self._load_etag(checkpoint_dir)
                status, new_etag, written = self._download(
                    url, api_key, etag, verify_ssl
                )
                if new_etag and new_etag != etag:
                    self._save_etag(checkpoint_dir, new_etag)

                if status == 304:
                    message = "speculus mmdb up to date etag=%s" % etag
                else:
                    message = "speculus mmdb updated bytes=%d etag=%s path=%s" % (
                        written,
                        new_etag,
                        MMDB_PATH,
                    )
                ew.log("INFO", "speculus_ti: " + message)
                ew.write_event(
                    Event(
                        stanza=input_name,
                        sourcetype="speculus:mmdb_updater",
                        data=message,
                    )
                )
            except Exception as err:  # keep the input alive for the next run
                ew.log("ERROR", "speculus_ti: mmdb update failed: %s" % err)
                ew.write_event(
                    Event(
                        stanza=input_name,
                        sourcetype="speculus:mmdb_updater",
                        data="speculus mmdb update failed: %s" % err,
                    )
                )


if __name__ == "__main__":
    sys.exit(SpeculusMMDBUpdater().run(sys.argv))
