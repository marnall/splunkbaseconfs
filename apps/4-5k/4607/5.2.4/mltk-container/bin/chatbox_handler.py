import os
import sys
import json
import requests
from urllib.parse import parse_qs

bin_path = os.path.join(os.path.dirname(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)

import configparser
path = os.path.join(os.path.dirname(__file__), "..", "local/containers.conf")
config = configparser.ConfigParser()
config.read(path)

llm_path = os.path.join(os.path.dirname(__file__), "..", "local/llm.conf")
llm_config = configparser.ConfigParser()
llm_config.read(llm_path)

from base_handler import BaseRestHandler


def join_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.lstrip("/")


class ChatboxProxyHandler(BaseRestHandler):
    API_BASE_URL = config.get('__dev__', 'api_url')

    def handle_POST(self):
        log = self.get_logger()
        log.info("ChatboxProxyHandler handle_POST called")

        try:
            raw_payload = self.request.get("payload", "") or ""
            params = parse_qs(raw_payload)

            action = params.get("action", [""])[0].strip()

            if action == "chatbox":
                resp = self._handle_chatbox(params)
                return self.send_json_response(resp)

            if action == "logReview":
                resp = self._handle_log_review(params)
                return self.send_json_response(resp)
            
            if action == "getllmlist":
                resp = self._handle_llm_list()
                return self.send_json_response(resp)

            return self.send_json_response({
                "status": "error",
                "message": "Missing/invalid action. Use action=chatbox or action=logReview."
            })

        except requests.Timeout:
            log.exception("Timeout calling upstream API")
            return self.send_json_response({"status": "error", "message": "Upstream API timeout"})
        except requests.RequestException as e:
            log.exception("HTTP error calling upstream API: %s", str(e))
            return self.send_json_response({"status": "error", "message": "Upstream API request failed"})
        except Exception as e:
            log.exception("Unhandled error: %s", str(e))
            return self.send_json_response({"status": "error", "message": "Unhandled server error"})

    def _handle_chatbox(self, params):
        log = self.get_logger()

        message = params.get("message", [""])[0]
        session_id = params.get("sessionID", [""])[0]
        user_name = params.get("userName", [""])[0]
        llm_option = params.get("llmOption", [""])[0]

        if not message or not session_id or not user_name:
            return {"status": "error", "message": "Required: message, sessionID, userName"}

        url = join_url(self.API_BASE_URL, "chatbox")
        payload = {"message": message, "sessionID": session_id, "userName": user_name, "llmOption": llm_option}

        log.info("Proxying chatbox request to %s", url)

        r = requests.post(url, json=payload, verify=False, timeout=60)
        r.raise_for_status()
        return r.json()

    def _handle_log_review(self, params):
        log = self.get_logger()

        user_name = params.get("userName", [""])[0]
        session_id = params.get("sessionID", [""])[0]

        # logs comes in as JSON string
        logs_raw = params.get("logs", [""])[0]

        if not user_name or not session_id or not logs_raw:
            return {"status": "error", "message": "Required: userName, sessionID, logs(JSON)"}

        try:
            logs = json.loads(logs_raw)
            if not isinstance(logs, list):
                return {"status": "error", "message": "logs must be a JSON array (list of objects)"}
        except Exception:
            return {"status": "error", "message": "logs must be valid JSON"}

        timestamp = params.get("timestamp", [""])[0]
        if not timestamp:
            from datetime import datetime, timezone
            timestamp = datetime.now(timezone.utc).isoformat()

        url = join_url(self.API_BASE_URL, "logReview")
        payload = {
            "userName": user_name,
            "sessionID": session_id,
            "timestamp": timestamp,
            "logs": logs
        }

        log.info("Proxying logReview request to %s (logs=%d)", url, len(logs))

        r = requests.post(url, json=payload, verify=False, timeout=120)
        r.raise_for_status()
        return r.json()
    
    def _handle_llm_list(self):
        llm_list = []
        try:
            if llm_config.get('llm_config', 'llm_ollama_is_configured') == "1":
                llm_list.append({'id':"ollama", 'label': "Ollama"})
        except:
            pass
        try:
            if llm_config.get('llm_config', 'llm_azure_is_configured') == "1":
                llm_list.append({'id':"azure_openai", 'label': "Azure OpenAI"})
        except:
            pass
        try:
            if llm_config.get('llm_config', 'llm_bedrock_is_configured') == "1":
                llm_list.append({'id':"bedrock", 'label': "AWS Bedrock"})
        except:
            pass

        try:
            if llm_config.get('llm_config', 'llm_openai_is_configured') == "1":
                llm_list.append({'id':"openai", 'label': "OpenAI"})
        except:
            pass

        try:
            if llm_config.get('llm_config', 'llm_gemini_is_configured') == "1":
                llm_list.append({'id':"gemini", 'label': "Gemini"})
        except:
            pass
        return {
            "status": "ok",
            "message": "Endpoint is reachable. Use POST with action=chatbox or action=logReview.",
            "llms": llm_list
        }
        

    def handle_GET(self):
        self.get_logger().info("Handler handle_GET is called to retrieve available LLM options or MCP status")
        log = self.get_logger()
        
        try:
            resp = self._handle_mcp_state()
            return self.send_json_response(resp)


        except requests.Timeout:
            log.exception("Timeout calling upstream API")
            return self.send_json_response({"status": "error", "message": "Upstream API timeout"})
        except requests.RequestException as e:
            log.exception("HTTP error calling upstream API: %s", str(e))
            return self.send_json_response({"status": "error", "message": "Upstream API request failed"})
        except Exception as e:
            log.exception("Unhandled error: %s", str(e))
            return self.send_json_response({"status": "error", "message": "Unhandled server error"})
        
        
    def _handle_mcp_state(self):
        log = self.get_logger()
        url = join_url(self.API_BASE_URL, "mcp/status")
        log.info("Proxying MCP status request to %s", url)

        try:
            r = requests.get(
                url,
                verify=False,
                timeout=10  # shorter timeout for polling endpoint
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            log.error("MCP status proxy failed: %s", str(e))
            return {
                "connected": False,
                "detail": "Backend unreachable",
                "error": str(e)
            }

    
