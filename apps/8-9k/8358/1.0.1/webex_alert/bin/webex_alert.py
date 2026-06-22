#!/usr/bin/env python3
"""
Splunk Alert Action for sending messages to Webex Teams rooms
"""

import sys
import json
import gzip
import csv
import requests

def get_room_id_by_name(bot_token, room_name):
    """
    Get room ID by room name
    Returns the first matching room ID or None if not found
    """
    url = "https://webexapis.com/v1/rooms"
    
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        rooms = response.json().get('items', [])
        
        # Search for room by name (case-insensitive)
        room_name_lower = room_name.lower().strip()
        for room in rooms:
            if room.get('title', '').lower().strip() == room_name_lower:
                return room.get('id')
        
        sys.stderr.write(f"ERROR: Room '{room_name}' not found\n")
        return None
    except Exception as e:
        sys.stderr.write(f"ERROR: Failed to get room ID: {str(e)}\n")
        return None


def send_webex_message(bot_token, room_id, message, message_type='text'):
    """
    Send a message to a Webex room
    """
    url = "https://webexapis.com/v1/messages"
    
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json"
    }
    
    payload = {"roomId": room_id}
    
    if message_type.lower() == 'markdown':
        payload["markdown"] = message
    else:
        payload["text"] = message
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        sys.stderr.write(f"ERROR: Failed to send Webex message: {str(e)}\n")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        # Read payload from stdin
        payload = json.loads(sys.stdin.read())
        
        # Get configuration
        config = payload.get('configuration', {})
        bot_token = config.get('bot_token', '')
        room_identifier = config.get('room_id', '')  # Can be ID or name
        message = config.get('message', 'Alert triggered from Splunk')
        message_type = config.get('message_type', 'text')
        
        # Determine if room_identifier is an ID or a name
        # Room IDs are alphanumeric strings, typically starting with specific patterns
        # If it doesn't look like an ID, treat it as a room name
        room_id = room_identifier
        
        # If the identifier doesn't look like a Webex Room ID, try to look it up by name
        # Webex Room IDs are base64-encoded and contain specific patterns
        if room_identifier and not room_identifier.startswith('Y2lzY29zcGFyazovL'):
            # Likely a room name, look up the ID
            sys.stderr.write(f"INFO: Looking up room ID for room name: {room_identifier}\n")
            room_id = get_room_id_by_name(bot_token, room_identifier)
            if not room_id:
                sys.stderr.write(f"ERROR: Could not find room '{room_identifier}'\n")
                sys.exit(1)
            sys.stderr.write(f"INFO: Found room ID: {room_id}\n")
        
        # Get search results for token replacement
        results_file = payload.get('results_file')
        if results_file:
            try:
                with gzip.open(results_file, 'rt') as f:
                    reader = csv.DictReader(f)
                    results = list(reader)
                    if results:
                        # Replace tokens in message
                        # Support both $field$ and $result.field$ formats
                        for key, value in results[0].items():
                            # Replace $field$ format
                            token1 = f"${key}$"
                            if token1 in message:
                                message = message.replace(token1, str(value))
                            # Replace $result.field$ format
                            token2 = f"$result.{key}$"
                            if token2 in message:
                                message = message.replace(token2, str(value))
            except:
                pass
        
        # Send message
        success = send_webex_message(bot_token, room_id, message, message_type)
        sys.exit(0 if success else 1)
    else:
        sys.stderr.write("This script should be executed by Splunk as an alert action\n")
        sys.exit(1)
