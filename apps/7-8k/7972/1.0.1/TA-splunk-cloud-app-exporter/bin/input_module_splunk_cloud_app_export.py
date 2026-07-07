import os
import json
from datetime import datetime


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    """
    Fetch list of apps from ACS API, then export each via victoria export endpoint
    """
    acs_stack = helper.get_arg('stack')
    acs_token = helper.get_arg('token')
    export_dir = helper.get_arg('export_dir')

    # set http timeout
    timeout = 600 

    base_url = f"https://admin.splunk.com/{acs_stack}/adminconfig/v2/apps/victoria"

    headers = {
        'Authorization': f"Bearer {acs_token}",
        'Content-Type': 'application/json'
    }

    # 1. Get app list
    app_list_url = f"{base_url}?count=0"
    try:
        resp = helper.send_http_request(
            app_list_url,
            method='GET',
            headers=headers,
            verify=True,
            timeout=timeout
        )
        resp.raise_for_status()
        apps_data = resp.json()
    except Exception as e:
        helper.log_error(f"Error fetching app list from ACS API: {e}")
        return

    apps = apps_data.get('apps', [])
    helper.log_info(f"Retrieved {len(apps)} apps from ACS API.")

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # 2. Export each app
    for app in apps:
        app_id = app.get('id') or app.get('name')
        if not app_id:
            helper.log_warning(f"Skipping app without id: {app}")
            continue

        export_url = (
            f"https://admin.splunk.com/{acs_stack}/adminconfig/v2/apps/victoria/export/download/{app_id}"
            "?local=true&default=true&users=true"
        )

        try:
            dl_resp = helper.send_http_request(
                export_url,
                method='GET',
                headers=headers,
                verify=True,
                timeout=timeout
            )
            dl_resp.raise_for_status()
            file_content = dl_resp.content
        except Exception as e:
            helper.log_error(f"Failed to download export for app {app_id}: {e}")
            continue

        # 3. Save to file
        file_name = f"{app_id}.spl"
        file_path = os.path.join(export_dir, file_name)

        try:
            with open(file_path, 'wb') as f:
                f.write(file_content)
            helper.log_info(f"Exported app {app_id} to {file_path}")
        except Exception as e:
            helper.log_error(f"Failed to save export for app {app_id}: {e}")

    helper.log_info("App export job finished.")

