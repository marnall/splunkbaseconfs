import os
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import ssl
import splunk.rest
from splunk.persistconn.application import PersistentServerConnectionApplication


class AINotableUpdateHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(AINotableUpdateHandler, self).__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get('method', 'GET')

            session_key = request.get('session', {}).get('authtoken', '')
            current_user = request.get('session', {}).get('user', 'unknown')

            form_data = {}
            for kv in request.get('form', []):
                form_data[kv[0]] = kv[1]

            
            
            
            event_id = form_data.get('event_id', '') or form_data.get('rule_id', '')
            rule_id = form_data.get('rule_id', '')          
            comment = form_data.get('comment', '')
            
            
            
            status_arg = form_data.get('status', '')
            disposition = form_data.get('disposition', '')

            def log_audit(status, error_msg=""):
                try:
                    log_dir = os.path.join(os.environ.get('SPLUNK_HOME', '/opt/splunk'), 'var', 'log', 'splunk')
                    os.makedirs(log_dir, exist_ok=True)
                    log_file = os.path.join(log_dir, 'dv_ai_assistant_ai_audit.log')
                    #log_file = os.path.join(log_dir, 'dv_ai_audit.log')
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    safe_comment = str(comment).replace('\n', ' ').replace('"', "'")
                    safe_error = str(error_msg).replace('\n', ' ').replace('"', "'")
                    log_entry = (f'{timestamp} action="notable_update" user="{current_user}" '
                                 f'event_id="{event_id}" rule_id="{rule_id}" status="{status}" '
                                 f'comment="{safe_comment}" error="{safe_error}"\n')
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(log_entry)
                except Exception:
                    pass

            if method != 'POST':
                return {'payload': json.dumps({"error": "Only POST is supported"}),
                        'status': 405, 'headers': {'Content-Type': 'application/json'}}

            if not event_id or not comment:
                log_audit("error", "Missing event_id/rule_id or comment")
                return {'payload': json.dumps({"error": "Missing event_id or comment"}),
                        'status': 400, 'headers': {'Content-Type': 'application/json'}}

            if "🤖 [AI Triage Report]" not in comment:
                comment = "🤖 [AI Triage Report]\n\n" + comment

            
            es_url = "https://127.0.0.1:8089"
            es_token = ""
            try:
                _, pwd_content = splunk.rest.simpleRequest(
                    '/servicesNS/nobody/dv_ai_assistant/storage/passwords?output_mode=json&search=realm="dv_ai_es_integration"',
                    sessionKey=session_key, method='GET'
                )
                passwords = json.loads(pwd_content).get('entry', [])
                for p in passwords:
                    uname = p.get('content', {}).get('username')
                    if uname == 'es_url':
                        es_url = p.get('content', {}).get('clear_password', es_url)
                    elif uname == 'es_token':
                        es_token = p.get('content', {}).get('clear_password', '')
            except Exception:
                pass

            
            try:
                es_host = (urllib.parse.urlparse(es_url).hostname or '').lower()
            except Exception:
                es_host = ''
            loopback = es_host in ('localhost', '127.0.0.1', '::1') or es_host.startswith('127.')
            ctx = ssl._create_unverified_context() if loopback else ssl.create_default_context()

            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if es_token:
                headers["Authorization"] = f"Bearer {es_token}"
            else:
                headers["Authorization"] = f"Splunk {session_key}"

            
            
            fields = {'ruleUIDs': event_id, 'comment': comment}
            if status_arg:
                fields['status'] = status_arg
            if disposition:
                fields['disposition'] = disposition
            payload = urllib.parse.urlencode(fields).encode('utf-8')

            es_endpoint = f"{es_url.rstrip('/')}/services/notable_update"

            try:
                req = urllib.request.Request(es_endpoint, data=payload, headers=headers, method='POST')
                urllib.request.urlopen(req, context=ctx)

                log_audit(status_arg or "comment_only")
                return {'payload': json.dumps({"status": "success",
                                               "message": f"Successfully updated notable {event_id}"}),
                        'status': 200, 'headers': {'Content-Type': 'application/json'}}

            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                log_audit("error", f"HTTP {e.code} - {error_body}")
                return {'payload': json.dumps({"error": f"ES HTTP Error {e.code}", "details": error_body}),
                        'status': e.code, 'headers': {'Content-Type': 'application/json'}}
            except Exception as e:
                log_audit("error", str(e))
                return {'payload': json.dumps({"error": "Internal Error", "details": str(e)}),
                        'status': 500, 'headers': {'Content-Type': 'application/json'}}

        except Exception as e:
            return {'payload': json.dumps({"error": "Unhandled Exception", "details": str(e)}),
                    'status': 500, 'headers': {'Content-Type': 'application/json'}}
