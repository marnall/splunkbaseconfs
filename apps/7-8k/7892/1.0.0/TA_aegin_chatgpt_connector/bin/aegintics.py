import os
import sys
import json
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option

@Configuration(requires_preop=True)
class AeginTics(ReportingCommand):
    prompt = Option(require=True)

    @Configuration()
    def map(self, records):
        for record in records:
            yield record

    def reduce(self, records):
        # [AEGINMOD] Securely get API key using session key
        session_key = self._metadata.searchinfo.session_key
        api_key = self.get_api_key(session_key)

        # Prepare data
        all_records = list(records)
        records_text = "\n".join(json.dumps(r, ensure_ascii=False) for r in all_records)
        full_prompt = f"{self.prompt}\n\n===\nData:\n{records_text}"

        # Send to OpenAI
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": full_prompt}]
        }

        try:
            request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                result = json.loads(response.read())
                reply = result["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"[ERROR] {str(e)}"

        yield {"chatgpt_response": reply}

    def get_api_key(self, session_key):
        app = "TA_aegin_chatgpt_connector"  # [AEGINMOD] Change this to your actual app name
        url = f"https://localhost:8089/servicesNS/nobody/{app}/storage/passwords?output_mode=json"

        headers = {
            "Authorization": f"Splunk {session_key}"
        }

        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read())
                for entry in result["entry"]:
                    if entry["content"].get("realm") == "openai" and entry["content"].get("username") == "openai_key":
                        return entry["content"]["clear_password"]
                raise Exception("OpenAI API key not found in secure storage.")
        except Exception as e:
            raise Exception(f"Failed to retrieve API key: {str(e)}")

dispatch(AeginTics, sys.argv, sys.stdin, sys.stdout, __name__)

