import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

import splunk.admin as admin
import splunk.rest


APP_ID = "dv_ai_assistant"


class AIProviderTestHandler(admin.MConfigHandler):
    def setup(self):
        # In an EAI create request, the POST field "name" is consumed by Splunk
        # and exposed as self.callerArgs.id. It must not be treated as a normal arg.
        return

    def handleList(self, confInfo):
        self._write_result(confInfo, {
            "status": "ready",
            "url": "",
            "code": 200,
            "body": "Provider test endpoint is ready."
        })

    def handleCreate(self, confInfo):
        try:
            provider_id = str(self.callerArgs.id or "").strip()
            if not provider_id:
                return self._write_result(confInfo, {
                    "status": "failed",
                    "url": "",
                    "code": None,
                    "body": "Provider name is required."
                })

            provider = self._read_provider(provider_id)
            if not provider:
                return self._write_result(confInfo, {
                    "status": "failed",
                    "url": "",
                    "code": None,
                    "body": "Provider '%s' was not found." % provider_id
                })

            engine_type = str(provider.get("engine_type", "ollama") or "ollama").strip().lower()
            url = str(provider.get("url", "") or "").strip()
            model = str(provider.get("model", "") or "").strip()

            if not url:
                return self._write_result(confInfo, {
                    "status": "failed",
                    "url": "",
                    "code": None,
                    "body": "Provider endpoint URL is empty."
                })

            session_key = self.getSessionKey()
            api_key = ""
            if engine_type != "ollama":
                api_key = self._get_api_key(session_key, provider_id)

            timeout, security = self._get_runtime_settings()
            request_url, headers, payload = self._build_request(
                engine_type, url, model, api_key
            )

            request = urllib.request.Request(
                request_url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            try:
                response = urllib.request.urlopen(
                    request,
                    context=self._ssl_context(request_url, security),
                    timeout=timeout
                )
                status_code = getattr(response, "status", None) or response.getcode()
                body = response.read().decode("utf-8", "replace")

                return self._write_result(confInfo, {
                    "status": "success",
                    "url": request_url,
                    "code": status_code,
                    "body": body[:32768]
                })

            except urllib.error.HTTPError as e:
                try:
                    body = e.read().decode("utf-8", "replace")
                except Exception:
                    body = str(e)

                return self._write_result(confInfo, {
                    "status": "http_error",
                    "url": request_url,
                    "code": e.code,
                    "body": body[:32768]
                })

            except Exception as e:
                return self._write_result(confInfo, {
                    "status": "failed",
                    "url": request_url,
                    "code": None,
                    "body": "%s: %s" % (e.__class__.__name__, str(e))
                })

        except Exception as e:
            # Never let the EAI handler itself return HTTP 500 for a test failure.
            return self._write_result(confInfo, {
                "status": "failed",
                "url": "",
                "code": None,
                "body": "Provider test handler error: %s: %s" % (
                    e.__class__.__name__, str(e)
                )
            })

    def _read_provider(self, provider_id):
        conf = self.readConf("ai_providers") or {}
        settings = conf.get(provider_id)
        if not settings:
            return None
        return dict(settings)

    def _get_runtime_settings(self):
        try:
            conf = self.readConf("ai_assistant") or {}
            query = conf.get("query", {}) or {}
            security = conf.get("security", {}) or {}
            value = int(query.get("llm_timeout_seconds", 60) or 60)
        except Exception:
            value = 60
            security = {}
        return max(5, min(value, 180)), security

    @staticmethod
    def _get_api_key(session_key, provider_id):
        realm = "dv_ai_provider_%s" % provider_id
        path = "/servicesNS/nobody/%s/storage/passwords?output_mode=json&search=%s" % (
            APP_ID,
            urllib.parse.quote('realm="%s"' % realm)
        )

        try:
            _, content = splunk.rest.simpleRequest(
                path,
                sessionKey=session_key,
                method="GET"
            )
            entries = json.loads(content).get("entry", [])
            for entry in entries:
                data = entry.get("content", {}) or {}
                if data.get("realm") == realm and data.get("username") == "api_key":
                    return data.get("clear_password", "") or ""
        except Exception:
            pass

        return ""

    @staticmethod
    def _build_request(engine_type, url, model, api_key):
        request_url = url.rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if engine_type == "ollama":
            if request_url.endswith("/api"):
                request_url += "/generate"
            elif not request_url.endswith("/api/generate") and not request_url.endswith("/api/chat"):
                request_url += "/api/generate"

            if request_url.endswith("/api/chat"):
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Reply with exactly OK"}
                    ],
                    "stream": False
                }
            else:
                payload = {
                    "model": model,
                    "prompt": "Reply with exactly OK",
                    "stream": False
                }

        elif engine_type == "openai":
            headers["Authorization"] = "Bearer %s" % api_key
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Reply with exactly OK"}
                ],
                "max_tokens": 16
            }

        elif engine_type == "gemini":
            headers["X-goog-api-key"] = api_key
            if ":generatecontent" not in request_url.lower():
                base = request_url.split("/v1beta")[0].rstrip("/")
                request_url = "%s/v1beta/models/%s:generateContent" % (
                    base,
                    urllib.parse.quote(model, safe="")
                )
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": "Reply with exactly OK"}]
                }]
            }

        else:
            if api_key:
                headers["Authorization"] = "Bearer %s" % api_key
            payload = {"prompt": "Reply with exactly OK"}

        return request_url, headers, payload

    @staticmethod
    def _ssl_context(url, security=None):
        security = security or {}
        try:
            host = (urllib.parse.urlparse(url).hostname or "").lower()
        except Exception:
            host = ""

        loopback = host in ("localhost", "127.0.0.1", "::1", "0.0.0.0") or host.startswith("127.")
        verify_tls = str(security.get("verify_tls", "true")).strip().lower() not in ("0", "false", "no", "off")
        skip_hosts = {
            item.strip().lower()
            for item in str(security.get("tls_skip_verify_hosts", "") or "").split(",")
            if item.strip()
        }

        if (not verify_tls) or loopback or host in skip_hosts:
            return ssl._create_unverified_context()
        return ssl.create_default_context()

    @staticmethod
    def _write_result(confInfo, payload):
        # EAI response must be a normal content dictionary.
        confInfo["test"]["data"] = json.dumps(payload, ensure_ascii=False)
        return


if __name__ == "__main__":
    admin.init(AIProviderTestHandler, admin.CONTEXT_APP_AND_USER)
