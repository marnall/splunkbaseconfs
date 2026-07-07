import os
import json
import requests
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

# Replace with your Gemini API Key from Google AI Studio
GEMINI_API_KEY = ''

class AiHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super().__init__()

    def convert_to_dict(self, query):
        parameters = {}
        for key, val in query:
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]
            elif key in parameters:
                parameters[key].append(val)
            else:
                parameters[key] = val
        return parameters

    def parse_in_string(self, in_string):
        params = json.loads(in_string)
        params['method'] = params['method'].lower()
        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))
        return params
    
    def handle(self, args):
        try:
            # Parse the incoming Splunk request
            body = self.parse_in_string(args.decode('utf-8'))["form_parameters"]
            
            # Extract prompt
            prompt = body.get("prompt")
            if not prompt:
                return self._error("Missing required field: prompt", 400)
            
            # --- Gemini Specific Implementation ---
            # Using Gemini 1.5 Flash (fast & cost-effective) or Gemini 1.5 Pro
            model_id = "gemini-2.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
            
            # Gemini payload structure
            chat_payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }

            chat_res = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(chat_payload)
            )

            if chat_res.status_code != 200:
                return self._error(f"Gemini API failed: {chat_res.text}", 500)

            chat_json = chat_res.json()
            
            # Navigate the Gemini response nesting
            # candidates[0] -> content -> parts[0] -> text
            try:
                html_output = chat_json["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return self._error("Unexpected response format from Gemini", 500)
            # ---------------------------------------

            return {
                "status": 200,
                "payload": json.dumps({"html": html_output}),
                "headers": {'Content-Type': 'application/json'}
            }

        except Exception as e:
            with open("/tmp/my_ai_log.txt", "a") as f:
                f.write(f"Error: {str(e)}\n")
            return self._error(f"Unexpected error: {str(e)}", 500)

    def _error(self, message, code):
        return {
            "status": code,
            "payload": json.dumps({"error": message}),
            "headers": {'Content-Type': 'application/json'}
        }