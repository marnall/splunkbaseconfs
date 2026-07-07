import os
import sys
import json
from work_queue import WorkQueue

# Add the "lib" directory to the Python path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# Add the directory where this script resides to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import splunklib.client as client
from util.context_logging import set_current_request_id, set_current_summarization_id


def main():
    summarization_id = sys.argv[1]
    priority = int(sys.argv[2])
    session_key = sys.argv[3]
    request_id = sys.argv[4] if len(sys.argv) > 4 else "unknown"
    
    # Set context for logging
    set_current_summarization_id(summarization_id)
    set_current_request_id(request_id)
    
    # You may need to pass more args, e.g., port, owner, etc.

    # Set up the Splunk service and WorkQueue as in the main code
    service = client.Service(token=session_key, owner="nobody")
    work_queue = WorkQueue(service)
    work_item = work_queue.enqueue(summarization_id, priority=priority, request_id=request_id)
    if work_item:
        print(json.dumps({"success": True}))
    else:
        print(json.dumps({"success": False}))

if __name__ == "__main__":
    main()