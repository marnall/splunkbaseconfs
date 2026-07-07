#!$SPLUNK_HOME/bin/python

# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
import os
import sys
import time
import threading
from hydra.hydra_gateway import bootstrap_web_service, service_logger


def get_gateway_config(session_key):
    """
    Gets the hydra gateway config from splunk

    RETURNS tuple of port, service_log_level, access_log_level
    """
    from hydra.models import HydraGatewayStanza

    stanza = HydraGatewayStanza.from_name("gateway", "SA-Hydra", session_key=session_key)
    if not stanza:
        return 8008, "", ""
    else:
        return stanza.port, stanza.service_log_level, stanza.access_log_level


def parent_monitor(server, parent_pid):
    """
    Monitor the parent process. When Splunk stops, it terminates the parent
    shell process. This orphans the Python process (PPID becomes 1).
    Detecting this allows us to shut down gracefully.
    """
    try:
        service_logger.info("starting parent monitor, parent_pid=%s", parent_pid)
        while True:
            time.sleep(2)  # Check every 2 seconds
            current_ppid = os.getppid()
            if current_ppid != parent_pid:
                # Parent changed (orphaned, PPID is now 1 or different)
                service_logger.info("parent process changed (was %s, now %s), initiating shutdown", 
                                   parent_pid, current_ppid)
                try:
                    server.stop()
                except Exception as e:
                    service_logger.warning("error stopping server from parent monitor: %s", str(e))
                service_logger.info("exiting via parent monitor")
                os._exit(0)
    except Exception as e:
        service_logger.warning("parent monitor exception: %s", str(e))


if __name__ == "__main__":
    # Capture parent PID before any forking
    parent_pid = os.getppid()
    
    #Get Gateway Configuration
    session_key = sys.stdin.readline().strip("\r\n")
    port, service_log_level, access_log_level = get_gateway_config(session_key)

    #Build Gateway
    server = bootstrap_web_service(port, service_log_level, access_log_level)

    # Start parent monitor thread (daemon so it won't block shutdown)
    monitor_thread = threading.Thread(target=parent_monitor, args=(server, parent_pid), daemon=True)
    monitor_thread.start()

    # Start server (blocking)
    server.start()