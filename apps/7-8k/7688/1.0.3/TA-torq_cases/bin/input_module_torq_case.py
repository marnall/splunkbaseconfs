# encoding = utf-8

import os
import sys
import time
import datetime
import base64
import json

def validate_input(helper, definition):
    """Validate modular input parameters"""
    backfill = definition.parameters.get('backfill_date', None)
    
    if backfill:
        try:
            datetime.datetime.strptime(backfill, '%m-%d-%Y')
        except ValueError:
            raise ValueError("Backfill datetime must be in format MM-DD-YYYY")

def collect_events(helper, ew):
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)
    helper.log_info(f"Log level set: {log_level}")

    
    """Collect SOAR case metrics"""
    helper.log_debug("Starting collection")
    
    # Get configuration
    backfill = helper.get_arg('backfill_date')
    client_id = helper.get_arg('client_id')
    client_secret = helper.get_arg('client_secret')
    interval = helper.get_arg('interval')
    fresh_run = helper.get_arg('fresh_run')
    
    if not client_id or not client_secret:
        helper.log_critical("Global account credentials not configured")
        raise ValueError("Global account credentials missing")
    
    # If fresh run is enabled, delete the checkpoint
    if fresh_run:
        helper.log_info("Fresh run enabled, deleting checkpoint")
        helper.delete_check_point('last_run')
    
    # Get checkpoint or use backfill/interval
    last_run = helper.get_check_point('last_run')
    if not last_run:
        if backfill:
            last_run = datetime.datetime.strptime(backfill, '%m-%d-%Y').replace(tzinfo=datetime.timezone.utc).isoformat()
        elif interval:
            last_run = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=int(interval))).isoformat()
        helper.log_debug(f"Using initial last_run: {last_run}")
    
    # Create basic auth header
    auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    # Get OAuth token
    auth_url = "https://auth.torq.io/v1/auth/token"
    try:
        token_response = helper.send_http_request(
            url=auth_url,
            method="POST",
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth_string}"
            },
            payload="grant_type=client_credentials",
            verify=True,
            use_proxy=True,
            timeout=30
        )
        token_response.raise_for_status()
        token = token_response.json().get('access_token')
    except Exception as e:
        helper.log_error(f"Failed to get OAuth token: {str(e)}")
        raise
    
    # Query cases
    cases_url = "https://api.torq.io/public/v1alpha/cases/query"
    next_page = ""
    total_events = 0
    should_continue = True
    
    while should_continue:
        try:
            payload = {
                "order_by": "created_at",
                "page_size": "100"
            }
            if next_page:
                payload["page_token"] = next_page
                
            cases_response = helper.send_http_request(
                url=cases_url,
                method="POST",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                payload=json.dumps(payload),
                verify=True,
                use_proxy=True,
                timeout=30
            )
            cases_response.raise_for_status()
            response_data = cases_response.json()
            
            # Process each case in the current batch
            for case in response_data['cases']:
                # Check if case needs processing based on timestamps
                should_process = False
                
                last_run_epoch = datetime.datetime.fromisoformat(last_run.replace('Z', '+00:00')).timestamp()
                    
                # Check created_at and updated_at
                if case.get('created_at'):
                    created_epoch = datetime.datetime.fromisoformat(case['created_at'].replace('Z', '+00:00')).timestamp()
                    if created_epoch > last_run_epoch:
                        should_process = True
                        helper.log_debug(f"Case {case['id']} created_at {created_epoch} > last_run {last_run_epoch}")
                            
                if case.get('updated_at'):
                    updated_epoch = datetime.datetime.fromisoformat(case['updated_at'].replace('Z', '+00:00')).timestamp()
                    if updated_epoch > last_run_epoch:
                        should_process = True
                        helper.log_debug(f"Case {case['id']} updated_at {updated_epoch} > last_run {last_run_epoch}")
                            
                # If this case doesn't meet our initial filter
                if not should_process:
                    # Check if case is older than a month
                    one_month_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).timestamp()
                    
                    if created_epoch < one_month_ago and not backfill:
                        helper.log_debug(f"Found case older than a month, stopping pagination at id: {case['id']} (created: {created_epoch})")
                        should_continue = False
                        break
                    else:
                        # Case is newer than a month but doesn't meet our filter criteria
                        # Skip timeline query and continue to next case
                        helper.log_debug(f"Skipping timeline query for case {case['id']} - not in filter range")
                        continue
                
                if should_process:
                    # Get case timeline
                    try:
                        timeline_url = f"https://api.torq.io/public/v1alpha/cases/{case['id']}/timeline/query"
                        timeline_response = helper.send_http_request(
                            url=timeline_url,
                            method="POST",
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Content-Type": "application/json",
                                "Accept": "application/json"
                            },
                            verify=True,
                            use_proxy=True,
                            timeout=30
                        )
                        timeline_response.raise_for_status()
                        timeline_events = timeline_response.json()['events']
                        
                        # Find metrics in timeline
                        time_to_respond = None
                        time_to_close = None
                        orig_case_details = None
                        for event in timeline_events:
                            if event.get('sla_timer_updated'):
                                current = event['sla_timer_updated']['current']
                                if current['name'] == 'Time to Respond' and not time_to_respond:
                                    time_to_respond = current['elapsed_time']
                                elif current['name'] == 'Time to Close' and not time_to_close:
                                    time_to_close = current['elapsed_time']
                            # Find raw note content
                            if event.get('note_added'):
                                note = event['note_added'].get('note', {})
                                if note.get('title') == 'Raw' and note.get('content'):
                                    # Extract JSON content from within the triple backticks
                                    content = note['content']
                                    json_start = content.find('{')
                                    json_end = content.rfind('}') + 1
                                    if json_start != -1 and json_end != -1:
                                        try:
                                            json_content = content[json_start:json_end]
                                            orig_case_details = json.loads(json_content)
                                            break
                                        except json.JSONDecodeError as e:
                                            helper.log_error(f"Failed to parse Raw note content as JSON for case {case['id']}: {str(e)}")
                        # Create event data
                        event_data = {
                            'case_id': case['id'],
                            'pretty_id': case['pretty_id'],
                            'created_at': case.get('created_at'),
                            'updated_at': case.get('updated_at'),
                            'completed_at': case.get('completed_at'),
                            'resolution_summary': case.get('resolution_summary'),
                            'state': case.get('state'),
                            'severity': case.get('severity'),
                            'assignee': case.get('assignee'),
                            'tags': case.get('tags'),
                            'title': case.get('title'),
                            'time_to_respond': time_to_respond,
                            'time_to_close': time_to_close,
                            'orig_case_details': orig_case_details
                        }
                        
                        # Get event timestamp from created_at or current time
                        event_time = None
                        if case.get('created_at'):
                            event_time = datetime.datetime.fromisoformat(case['created_at'].replace('Z', '+00:00')).timestamp()
                        
                        # Create and write event
                        event = helper.new_event(
                            data=json.dumps(event_data),
                            time=event_time,
                            host=helper.get_input_type(),
                            index=helper.get_output_index(),
                            source=helper.get_input_type(),
                            sourcetype=helper.get_sourcetype(),
                            done=True,
                            unbroken=True
                        )
                        
                        ew.write_event(event)
                        total_events += 1
                        helper.log_debug(f"Written event for case {case['id']}")
                        
                    except Exception as e:
                        helper.log_error(f"Failed to process timeline for case {case['id']}: {str(e)}")
                        continue
            
            if should_continue:
                next_page = response_data.get('next_page_token')
                if not next_page:
                    break
            else:
                break
                
        except Exception as e:
            helper.log_error(f"Failed to process cases: {str(e)}")
            raise
    
    helper.log_info(f"Total events written: {total_events}")
    # Update checkpoint
    helper.save_check_point('last_run', datetime.datetime.now(datetime.timezone.utc).isoformat())