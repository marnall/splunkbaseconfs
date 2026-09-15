# Copyright 2026 Kamal Singh Bisht
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""REST API for the Eventgen Manager UI.

Registered at /services/eventgen_manager/api by default/restmap.conf.

Routes
------
GET    /health                     install and generator status
GET    /apps                       apps that can hold eventgen stanzas
GET    /samples?app=               sample files available to an app
GET    /sample?app=&name=&lines=   contents of one sample file
POST   /sample                     create or overwrite a sample file
DELETE /sample?app=&name=          remove a sample file
POST   /preview                    render events for a draft stanza

Stanza CRUD deliberately lives on Splunk's own configs/conf-eventgen
endpoint rather than here, so that permissions, replication, and conf-layer
precedence keep working the way administrators already expect.
"""

from __future__ import absolute_import, division, print_function

import json
import os
import platform
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402
from splunk.clilib.bundle_paths import make_splunkhome_path  # noqa: E402

import splunk.rest  # noqa: E402

import eventgen_preview  # noqa: E402

APP_NAME = "eventgen_manager"
EVENTGEN_APP = "SA-Eventgen"

# Apps that must never be written to: upgrades overwrite them, so anything
# stored there would be silently lost.
PROTECTED_APPS = frozenset([
    "SA-Eventgen", "system", "search", "splunk_instrumentation",
    "splunk_monitoring_console", "splunk_secure_gateway",
    "splunk_archiver", "splunk_httpinput", "learned", "user-prefs",
    "framework", "launcher", "gettingstarted", "legacy", "alert_logevent",
    "alert_webhook", "introspection_generator_addon", "journald_input",
    "python_upgrade_readiness_app", "sample_app", "appsbrowser",
    "splunk_gdi", "splunk_rapid_diag", "splunk_internal_metrics",
])

# Conservative: no directory separators, no leading dot, no shell characters.
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\- ]{0,127}$")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_READ_LINES = 500
SAMPLE_EXTENSIONS = (".sample", ".csv", ".log", ".txt", ".json", ".list",
                     ".tsv", ".xml", ".dat", "")


class ApiError(Exception):
    """An error with a message suitable for showing directly to the user."""

    def __init__(self, message, status=400):
        Exception.__init__(self, message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------
# Path helpers
# --------------------------------------------------------------------------


# Names Splunk will accept for the modular input executable.
MODINPUT_NAMES = ("modinput_eventgen", "modinput_eventgen.exe",
                  "modinput_eventgen.py", "modinput_eventgen.cmd",
                  "modinput_eventgen.bat", "modinput_eventgen.sh")


def platform_dir():
    """The platform directory Splunk searches on this host.

    Splunk looks in <app>/<system>_<arch>/bin before <app>/bin, which is how
    apps ship compiled helpers for more than one operating system.
    """
    system = platform.system().lower()
    machine = (platform.machine() or "").lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "i386": "x86",
            "i686": "x86", "arm64": "arm64", "aarch64": "arm64"}.get(
                machine, machine or "unknown")
    if system.startswith("win"):
        system = "windows"
    return "%s_%s" % (system, arch)


def eventgen_runtime():
    """Report whether SA-Eventgen can actually run on this instance.

    Being present on disk is not the same as being runnable. SA-Eventgen
    ships its generator as a compiled binary under a platform directory, so
    an instance whose platform is not among them will never register the
    modular input, no matter how the app is configured.
    """
    root = os.path.join(apps_root(), EVENTGEN_APP)
    here = platform_dir()
    info = {"installed": os.path.isdir(root), "platform": here,
            "binary": None, "shipped": []}
    if not info["installed"]:
        return info

    # Which platforms does this copy actually carry a generator for?
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        entries = []
    for entry in entries:
        directory = os.path.join(root, entry, "bin")
        if not os.path.isdir(directory):
            continue
        for name in MODINPUT_NAMES:
            if os.path.isfile(os.path.join(directory, name)):
                info["shipped"].append(entry)
                break

    # Splunk checks the platform directory first, then the plain bin folder.
    for directory in (os.path.join(root, here, "bin"),
                      os.path.join(root, "bin")):
        for name in MODINPUT_NAMES:
            candidate = os.path.join(directory, name)
            if os.path.isfile(candidate):
                info["binary"] = candidate
                return info
    return info


def apps_root():
    return make_splunkhome_path(["etc", "apps"])


def app_dir(app):
    """Return the validated directory for an app, guarding against traversal."""
    if not app:
        app = APP_NAME
    if not SAFE_NAME.match(app):
        raise ApiError("'%s' is not a valid app name." % app)

    root = os.path.realpath(apps_root())
    candidate = os.path.realpath(os.path.join(root, app))

    if candidate != root and not candidate.startswith(root + os.sep):
        raise ApiError("'%s' is outside the apps directory." % app)
    if not os.path.isdir(candidate):
        raise ApiError("The app '%s' is not installed." % app, status=404)
    return candidate


def samples_dir(app):
    """Resolve <app>/samples, which is where eventgen looks by default."""
    return os.path.join(app_dir(app), "samples")


def safe_sample_path(app, name):
    """Resolve a sample file inside an app, rejecting anything that escapes."""
    if not name:
        raise ApiError("A file name is required.")
    if not SAFE_NAME.match(name):
        raise ApiError(
            "'%s' is not a valid file name. Use letters, numbers, spaces, "
            "dots, dashes, and underscores." % name)
    if ".." in name or "/" in name or "\\" in name:
        raise ApiError("File names cannot contain path separators.")

    directory = os.path.realpath(samples_dir(app))
    target = os.path.realpath(os.path.join(directory, name))
    if target != directory and not target.startswith(directory + os.sep):
        raise ApiError("'%s' is outside the samples directory." % name)
    return target


def writable_app(app):
    if app in PROTECTED_APPS:
        raise ApiError(
            "%s ships with Splunk or with eventgen, and an upgrade would "
            "erase anything stored there. Save to %s instead."
            % (app, APP_NAME), status=403)
    return app


# --------------------------------------------------------------------------
# Handler
# --------------------------------------------------------------------------


class EventgenManagerApi(PersistentServerConnectionApplication):
    """Routes API requests for the Eventgen Manager pages."""

    def __init__(self, command_line=None, command_arg=None):
        PersistentServerConnectionApplication.__init__(self)

    # -- plumbing ----------------------------------------------------------

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
        except ValueError:
            return self._reply({"error": "The request was not valid JSON."}, 400)

        try:
            method = (request.get("method") or "GET").upper()
            path = self._route(request)
            query = self._pairs(request.get("query"))
            session_key = (request.get("session") or {}).get("authtoken", "")
            payload = self._payload(request)

            handler = self._resolve(method, path)
            body = handler(query=query, payload=payload,
                           session_key=session_key)
            return self._reply(body, 200)

        except ApiError as exc:
            return self._reply({"error": exc.message}, exc.status)
        except eventgen_preview.PreviewError as exc:
            return self._reply({"error": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001 - surface, don't swallow
            sys.stderr.write(
                "eventgen_manager: unhandled error: %s\n%s\n"
                % (exc, traceback.format_exc()))
            return self._reply(
                {"error": "The request failed: %s" % exc}, 500)

    def _resolve(self, method, path):
        routes = {
            ("GET", "health"): self.get_health,
            ("GET", "apps"): self.get_apps,
            ("GET", "samples"): self.get_samples,
            ("GET", "sample"): self.get_sample,
            ("POST", "sample"): self.post_sample,
            ("DELETE", "sample"): self.delete_sample,
            ("POST", "preview"): self.post_preview,
        }
        handler = routes.get((method, path))
        if handler is None:
            raise ApiError(
                "%s /%s is not an endpoint of this API." % (method, path),
                status=404)
        return handler

    @staticmethod
    def _route(request):
        path = request.get("path_info") or ""
        # Strip the registered prefix if splunkd passed the full path.
        path = re.sub(r"^/?(services/)?eventgen_manager/api/?", "", path)
        return path.strip("/").split("/")[0] if path.strip("/") else "health"

    @staticmethod
    def _pairs(raw):
        result = {}
        for item in raw or []:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                result[item[0]] = item[1]
        return result

    @staticmethod
    def _payload(request):
        raw = request.get("payload")
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw)
        except ValueError:
            raise ApiError("The request body was not valid JSON.")
        if not isinstance(parsed, dict):
            raise ApiError("The request body must be a JSON object.")
        return parsed

    @staticmethod
    def _reply(body, status):
        return {
            "status": status,
            "payload": json.dumps(body),
            "headers": {"Content-Type": "application/json"},
        }

    # -- routes ------------------------------------------------------------

    def get_health(self, query=None, payload=None, session_key=None):
        """Report whether everything needed to generate events is in place."""
        runtime = eventgen_runtime()
        eventgen_installed = runtime["installed"]

        checks = []
        checks.append({
            "id": "eventgen_installed",
            "label": "SA-Eventgen is installed",
            "ok": eventgen_installed,
            "detail": ("Found in etc/apps/%s." % EVENTGEN_APP)
                      if eventgen_installed else
                      ("Install SA-Eventgen from Splunkbase. Nothing will be "
                       "generated without it."),
        })

        # Presence on disk is not the same as being runnable here.
        runnable = bool(runtime["binary"])
        if eventgen_installed:
            if runnable:
                detail = ("Generator binary present for %s."
                          % runtime["platform"])
            elif runtime["shipped"]:
                detail = ("This copy of SA-Eventgen ships a generator for %s "
                          "only. This instance is %s, so the modular input "
                          "cannot start. Configurations are still saved, and "
                          "will work on a supported platform."
                          % (" and ".join(runtime["shipped"]),
                             runtime["platform"]))
            else:
                detail = ("No generator executable found under etc/apps/%s. "
                          "The install may be incomplete."
                          % EVENTGEN_APP)
            checks.append({
                "id": "platform_supported",
                "label": "SA-Eventgen runs on this platform",
                "ok": runnable,
                "detail": detail,
            })

        modinput = self._read_modinput(session_key) if eventgen_installed \
            else {"available": False, "reason": "not-installed"}
        enabled = modinput.get("enabled")
        reason = modinput.get("reason")

        if enabled:
            detail = ("Generating with %s generator and %s output workers."
                      % (modinput.get("generatorWorkers", "?"),
                         modinput.get("outputWorkers", "?")))
        elif modinput.get("available"):
            detail = ("Turn on the modular input to start generating. "
                      "Nothing is being produced right now.")
        elif eventgen_installed and not runnable:
            # The check above already gave the cause. Repeating it, or
            # pointing at splunkd.log, only sends the reader somewhere that
            # will not help.
            detail = ("Not running, and it cannot be started here. See the "
                      "platform note above.")
        elif reason == "unregistered":
            detail = ("Splunk has not registered the eventgen modular input, "
                      "so there is nothing to turn on. This is what happens "
                      "when SA-Eventgen has no generator for this platform.")
        elif reason == "forbidden":
            detail = ("Your role cannot read the eventgen modular input. "
                      "The admin or sc_admin role is needed.")
        elif reason == "no-input":
            detail = ("SA-Eventgen registered, but no input has been created. "
                      "Add a [modinput_eventgen://default] stanza.")
        elif reason == "not-installed":
            detail = "Install SA-Eventgen first."
        else:
            detail = ("Could not reach the modular input endpoint. Check "
                      "splunkd.log for errors from SA-Eventgen.")

        checks.append({
            "id": "modinput_enabled",
            "label": "The eventgen modular input is running",
            "ok": bool(enabled),
            "detail": detail,
        })

        directory = samples_dir(APP_NAME)
        writable = os.access(directory, os.W_OK) if os.path.isdir(directory) \
            else os.access(app_dir(APP_NAME), os.W_OK)
        checks.append({
            "id": "samples_writable",
            "label": "Sample files can be saved",
            "ok": bool(writable),
            "detail": directory if writable else
                      ("Splunk cannot write to %s. Check the directory "
                       "permissions." % directory),
        })

        stanza_count, enabled_count = self._count_stanzas(session_key)
        checks.append({
            "id": "stanzas",
            "label": "Configurations exist",
            "ok": stanza_count > 0,
            "detail": ("%d configured, %d turned on."
                       % (stanza_count, enabled_count)) if stanza_count
                      else "No configurations yet. Create one to get started.",
        })

        return {
            "ok": all(check["ok"] for check in checks),
            "checks": checks,
            "modinput": modinput,
            "runtime": runtime,
            "samplesDir": directory,
            "app": APP_NAME,
        }

    def get_apps(self, query=None, payload=None, session_key=None):
        """List apps that can hold eventgen stanzas, manager app first."""
        root = apps_root()
        found = []

        try:
            entries = sorted(os.listdir(root))
        except OSError:
            entries = []

        for name in entries:
            path = os.path.join(root, name)
            if not os.path.isdir(path) or name.startswith("."):
                continue

            has_conf = any(os.path.isfile(os.path.join(path, layer,
                                                       "eventgen.conf"))
                           for layer in ("local", "default"))
            has_samples = os.path.isdir(os.path.join(path, "samples"))

            if name != APP_NAME and not (has_conf or has_samples):
                continue

            protected = name in PROTECTED_APPS
            found.append({
                "name": name,
                "label": self._app_label(path, name),
                "hasConf": has_conf,
                "hasSamples": has_samples,
                "writable": (not protected) and os.access(path, os.W_OK),
                "protected": protected,
                "isDefault": name == APP_NAME,
            })

        found.sort(key=lambda item: (not item["isDefault"],
                                     item["name"].lower()))
        return {"apps": found, "defaultApp": APP_NAME}

    def get_samples(self, query=None, payload=None, session_key=None):
        """List the sample files an app exposes to eventgen."""
        app = (query or {}).get("app") or APP_NAME
        directory = samples_dir(app)

        files = []
        if os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                path = os.path.join(directory, name)
                if not os.path.isfile(path) or name.startswith("."):
                    continue
                try:
                    stat = os.stat(path)
                    line_count = self._count_lines(path)
                except OSError:
                    continue
                files.append({
                    "name": name,
                    "bytes": stat.st_size,
                    "modified": int(stat.st_mtime),
                    "lines": line_count,
                    "editable": os.access(path, os.W_OK),
                })

        return {
            "app": app,
            "dir": directory,
            "exists": os.path.isdir(directory),
            "files": files,
        }

    def get_sample(self, query=None, payload=None, session_key=None):
        """Return the first N lines of a sample file."""
        query = query or {}
        app = query.get("app") or APP_NAME
        path = safe_sample_path(app, query.get("name"))

        if not os.path.isfile(path):
            raise ApiError("'%s' was not found in %s."
                           % (query.get("name"), app), status=404)

        try:
            limit = int(query.get("lines", 200))
        except ValueError:
            limit = 200
        limit = max(1, min(limit, MAX_READ_LINES))

        lines, truncated, total = [], False, 0
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                for number, line in enumerate(handle):
                    total = number + 1
                    if number < limit:
                        lines.append(line.rstrip("\n").rstrip("\r"))
                    else:
                        truncated = True
                        break
        except OSError as exc:
            raise ApiError("Could not read '%s': %s" % (query.get("name"), exc))

        return {
            "app": app,
            "name": query.get("name"),
            "content": "\n".join(lines),
            "lines": len(lines),
            "totalLines": total,
            "truncated": truncated,
            "path": path,
        }

    def post_sample(self, query=None, payload=None, session_key=None):
        """Create or overwrite a sample file."""
        payload = payload or {}
        app = writable_app(payload.get("app") or APP_NAME)
        name = payload.get("name")
        content = payload.get("content")

        if content is None:
            raise ApiError("The file content is missing.")
        if isinstance(content, bytes):
            content = content.decode("utf-8", "replace")
        if len(content.encode("utf-8", "ignore")) > MAX_UPLOAD_BYTES:
            raise ApiError(
                "The file is larger than %d MB. Trim the sample or place it "
                "on the server directly."
                % (MAX_UPLOAD_BYTES // (1024 * 1024)))

        path = safe_sample_path(app, name)
        directory = os.path.dirname(path)

        if os.path.isfile(path) and not payload.get("overwrite"):
            raise ApiError(
                "'%s' already exists in %s. Choose another name or replace it."
                % (name, app), status=409)

        try:
            if not os.path.isdir(directory):
                os.makedirs(directory)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            raise ApiError("Could not save '%s': %s" % (name, exc), status=500)

        return {
            "saved": True,
            "app": app,
            "name": name,
            "path": path,
            "bytes": len(content.encode("utf-8", "ignore")),
            "lines": len(content.splitlines()),
        }

    def delete_sample(self, query=None, payload=None, session_key=None):
        """Remove a sample file."""
        query = query or {}
        app = writable_app(query.get("app") or APP_NAME)
        name = query.get("name")
        path = safe_sample_path(app, name)

        if not os.path.isfile(path):
            raise ApiError("'%s' was not found in %s." % (name, app),
                           status=404)
        try:
            os.remove(path)
        except OSError as exc:
            raise ApiError("Could not delete '%s': %s" % (name, exc),
                           status=500)

        return {"deleted": True, "app": app, "name": name}

    def post_preview(self, query=None, payload=None, session_key=None):
        """Render the events a draft stanza would produce."""
        payload = payload or {}
        stanza = payload.get("stanza") or {}
        if not isinstance(stanza, dict):
            raise ApiError("'stanza' must be an object of settings.")

        app = payload.get("app") or APP_NAME
        content = payload.get("content")

        if content is None:
            name = payload.get("sample")
            if not name:
                raise ApiError(
                    "Choose a sample file, or paste sample text to preview.")
            fetched = self.get_sample(
                query={"app": app, "name": name, "lines": MAX_READ_LINES})
            content = fetched["content"]

        directories = [samples_dir(app)]
        if app != APP_NAME:
            directories.append(samples_dir(APP_NAME))

        sample_dir_setting = stanza.get("sampleDir")
        if sample_dir_setting:
            resolved = self._resolve_sample_dir(app, sample_dir_setting)
            if resolved:
                directories.insert(0, resolved)

        result = eventgen_preview.render(
            stanza,
            content,
            search_dirs=directories,
            limit=payload.get("limit", 20),
            seed=payload.get("seed"),
        )
        result["app"] = app
        return result

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _resolve_sample_dir(app, setting):
        """Resolve the sampleDir setting relative to the conf file location."""
        setting = str(setting).strip()
        if not setting:
            return None
        if os.path.isabs(setting):
            return setting if os.path.isdir(setting) else None
        # Relative paths are resolved from the directory holding the conf file.
        base = os.path.join(app_dir(app), "local")
        candidate = os.path.realpath(os.path.join(base, setting))
        return candidate if os.path.isdir(candidate) else None

    @staticmethod
    def _count_lines(path, cap=200000):
        count = 0
        try:
            with open(path, "rb") as handle:
                for count, _ in enumerate(handle, 1):
                    if count >= cap:
                        break
        except OSError:
            return 0
        return count

    @staticmethod
    def _app_label(path, fallback):
        for layer in ("local", "default"):
            conf = os.path.join(path, layer, "app.conf")
            if not os.path.isfile(conf):
                continue
            try:
                with open(conf, "r", encoding="utf-8",
                          errors="replace") as handle:
                    in_ui = False
                    for line in handle:
                        stripped = line.strip()
                        if stripped.startswith("["):
                            in_ui = stripped == "[ui]"
                        elif in_ui and stripped.startswith("label"):
                            return stripped.split("=", 1)[1].strip()
            except OSError:
                continue
        return fallback

    @classmethod
    def _splunkd(cls, session_key, path, method="GET", **kwargs):
        """Call splunkd on the user's behalf, returning parsed JSON."""
        return cls._splunkd_ex(session_key, path, method, **kwargs)[1]

    @staticmethod
    def _splunkd_ex(session_key, path, method="GET", **kwargs):
        """As _splunkd, but also returns the outcome.

        Callers that need to explain a failure to the user cannot do so if
        every problem arrives as None. The first element is the HTTP status,
        or a string describing why no request was made.
        """
        if not session_key:
            return "no-session", None
        try:
            response, content = splunk.rest.simpleRequest(
                path, sessionKey=session_key, method=method,
                getargs={"output_mode": "json", "count": "0"}, **kwargs)
        except Exception as exc:  # noqa: BLE001 - endpoint may not exist
            # Splunk raises for a missing endpoint rather than returning 404,
            # and the status hides on the exception. Recovering it is what
            # lets the caller say "not registered" instead of "unreachable".
            status = getattr(exc, "statusCode", None) or \
                getattr(exc, "status", None)
            return (status if isinstance(status, int) else "unreachable"), None
        status = getattr(response, "status", None)
        if status not in (200, 201):
            return status, None
        try:
            return status, json.loads(content)
        except ValueError:
            return status, None

    def _read_modinput(self, session_key):
        """Read the SA-Eventgen modular input state.

        An empty result is ambiguous on its own, so the reason travels with
        it: the caller needs to distinguish an unregistered scheme from an
        input that simply has not been created yet.
        """
        status, data = self._splunkd_ex(
            session_key,
            "/servicesNS/nobody/%s/data/inputs/modinput_eventgen"
            % EVENTGEN_APP)

        if data is None:
            if status == 404:
                reason = "unregistered"
            elif status in (401, 403):
                reason = "forbidden"
            else:
                reason = "unreachable"
            return {"available": False, "reason": reason, "status": status}

        entries = data.get("entry", [])
        chosen = None
        for entry in entries:
            if entry.get("name") == "default":
                chosen = entry
                break
        if chosen is None and entries:
            chosen = entries[0]

        if chosen is None:
            return {"available": False, "reason": "no-input", "status": status}

        content = chosen.get("content", {})
        return {
            "available": True,
            "reason": "ok",
            "status": status,
            "name": chosen.get("name"),
            "enabled": not content.get("disabled", True),
            "generatorWorkers": content.get("generatorWorkers"),
            "outputWorkers": content.get("outputWorkers"),
            "verbosity": content.get("verbosity"),
        }

    def _count_stanzas(self, session_key):
        """Count eventgen stanzas across all apps."""
        data = self._splunkd(session_key, "/servicesNS/-/-/configs/conf-eventgen")
        if not data:
            return 0, 0

        total, enabled = 0, 0
        for entry in data.get("entry", []):
            name = entry.get("name", "")
            if name in ("default", "global"):
                continue
            total += 1
            content = entry.get("content", {})
            if str(content.get("disabled", "false")).lower() in ("0", "false"):
                enabled += 1
        return total, enabled
