import sys
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl


def setup_logger(log_path, max_bytes=5 * 1024 * 1024, backup_count=5):
    def rotate_if_needed():
        try:
            if not os.path.exists(log_path):
                return

            if os.path.getsize(log_path) < max_bytes:
                return

            oldest = f"{log_path}.{backup_count}"
            if os.path.exists(oldest):
                os.remove(oldest)

            for i in range(backup_count - 1, 0, -1):
                src = f"{log_path}.{i}"
                dst = f"{log_path}.{i + 1}"
                if os.path.exists(src):
                    os.replace(src, dst)

            os.replace(log_path, f"{log_path}.1")
        except Exception:
            pass

    def log(msg):
        rotate_if_needed()
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

    return log


def run():
    splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
    app_local_dir = os.path.join(splunk_home, 'etc', 'apps', 'dv_ai_assistant', 'local')
    os.makedirs(app_local_dir, exist_ok=True)

    log = setup_logger(os.path.join(app_local_dir, 'worker_debug.log'))
    log('worker started')

    session_key = sys.stdin.read().strip()
    if not session_key:
        log('[ERROR] Empty session key; Splunk authorization was not provided.')
        return

    ctx = ssl._create_unverified_context()
    base_url = 'https://127.0.0.1:8089'
    headers = {
        'Authorization': f'Splunk {session_key}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        req = urllib.request.Request(
            f'{base_url}/servicesNS/nobody/dv_ai_assistant/configs/conf-ai_settings/global_settings?output_mode=json',
            headers=headers
        )
        resp = urllib.request.urlopen(req, context=ctx)
        content = json.loads(resp.read())['entry'][0]['content']
        auto_triage = str(content.get('auto_triage', '0')).lower()
        auto_interval = int(content.get('auto_interval', 120))
    except Exception as e:
        log(f'[ERROR] Failed to read settings: {str(e)}')
        return

    if auto_triage not in ('1', 'true', 'yes', 'on'):
        log('Autonomous triage is disabled.')
        return

    timestamp_file = os.path.join(app_local_dir, 'triage_last_run.txt')
    now = time.time()

    if os.path.exists(timestamp_file):
        try:
            with open(timestamp_file, 'r', encoding='utf-8') as f:
                last_run = float(f.read().strip() or 0)
        except Exception:
            last_run = 0
        if now - last_run < auto_interval:
            log(f'Next run is not due. Remaining: {int(auto_interval - (now - last_run))} seconds.')
            return

    with open(timestamp_file, 'w', encoding='utf-8') as f:
        f.write(str(now))

    log('Scanning Splunk ES notable events...')

    search_query = (
        'search `notable` '
        '| search status_group IN ("New", "In Progress") '
        '| search NOT comment="*🤖 [AI Triage Report]*" '
        '| head 5'
    )
    search_payload = urllib.parse.urlencode({
        'search': search_query,
        'output_mode': 'json',
        'exec_mode': 'oneshot'
    }).encode('utf-8')

    try:
        req = urllib.request.Request(
            f'{base_url}/servicesNS/nobody/dv_ai_assistant/search/jobs',
            data=search_payload,
            headers=headers,
            method='POST'
        )
        resp = urllib.request.urlopen(req, context=ctx)
        results = json.loads(resp.read()).get('results', [])
        log(f'{len(results)} unprocessed notable events found.')
    except urllib.error.HTTPError as e:
        log(f'[ERROR] Splunk search API failed: {e.code} - {e.read().decode("utf-8", "replace")}')
        return
    except Exception as e:
        log(f'[ERROR] Connection failed: {str(e)}')
        return

    if not results:
        log('No new notable events require analysis.')
        return

    for event in results:
        event_id = str(event.get('event_id', '') or event.get('event_hash', '') or '')
        rule_id = str(event.get('rule_id', '') or event.get('rule_uid', '') or '')
        rule_name = str(
            event.get('alert_name', '') or
            event.get('rule_name', '') or
            event.get('search_name', '') or
            event.get('signature', '') or
            'Unknown'
        )

        log(f'Starting AI analysis -> Rule: {rule_name} | Event ID: {event_id or "N/A"}')

        prompt = json.dumps(event, ensure_ascii=False, indent=2, default=str)
        chat_payload = urllib.parse.urlencode({
            'name': f'triage_{int(time.time())}_{(event_id or rule_id or "event")[-8:]}',
            'prompt': prompt,
            'mode': 'triage',
            'provider_id': ''
        }).encode('utf-8')

        try:
            chat_req = urllib.request.Request(
                f'{base_url}/servicesNS/nobody/dv_ai_assistant/admin/ai_chat?output_mode=json',
                data=chat_payload,
                headers=headers,
                method='POST'
            )
            chat_resp = urllib.request.urlopen(chat_req, context=ctx)
            chat_data = json.loads(chat_resp.read())
            reply = chat_data['entry'][0]['content']['reply']

            if '[ERROR]' in reply or 'Error:' in reply:
                log(f'[ERROR] AI response failed: {reply}')
                continue

            log('AI analysis completed. Updating Splunk Enterprise Security...')

            update_payload = urllib.parse.urlencode({
                'event_id': event_id,
                'rule_id': rule_id,
                'comment': reply
            }).encode('utf-8')
            update_req = urllib.request.Request(
                f'{base_url}/services/dv_ai_notable_update/ai_notable_update_action?output_mode=json',
                data=update_payload,
                headers=headers,
                method='POST'
            )
            urllib.request.urlopen(update_req, context=ctx)

            log(f'SUCCESS: Notable event updated. (Event ID: {event_id or rule_id})')

        except urllib.error.HTTPError as e:
            log(f'[ERROR] API request rejected: {e.code} - {e.read().decode("utf-8", "replace")}')
        except Exception as e:
            log(f'[ERROR] AI or Splunk ES connection failed: {str(e)}')


if __name__ == '__main__':
    run()

