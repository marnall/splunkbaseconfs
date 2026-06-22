#!/usr/bin/env python3
"""
Splunk Native Embedder Modular Input (Native Embedding Mode)
This script acts as a placeholder to maintain configuration compatibility.
The actual embedding is now handled via native Splunk '?embed=1' functionality.
"""
__author__ = 'Sanjeev Kumar'
__version__ = '3.0.7'

import sys
import logging
import time
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s %(name)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger('splunk_native_embedder_input')

# Minimal Scheme for Compatibility
SCHEME = """<scheme>
    <title>Native Embedder (Placeholder Input)</title>
    <description>Legacy configuration placeholder. Native embedding uses Splunk '?embed=1'.</description>
    <use_external_validation>true</use_external_validation>
    <use_single_instance>false</use_single_instance>
    <streaming_mode>simple</streaming_mode>
    <endpoint>
        <args>
            <arg name="username"><title>Legacy Param (Ignored)</title><required_on_edit>false</required_on_edit><required_on_create>false</required_on_create></arg>
            <arg name="port"><title>Legacy Param (Ignored)</title><required_on_edit>false</required_on_edit><required_on_create>false</required_on_create></arg>
            <arg name="connect_from"><title>Legacy Param (Ignored)</title><required_on_edit>false</required_on_edit><required_on_create>false</required_on_create></arg>
            <arg name="ssl_cert"><title>Legacy Param (Ignored)</title><required_on_edit>false</required_on_edit><required_on_create>false</required_on_create></arg>
            <arg name="ssl_key"><title>Legacy Param (Ignored)</title><required_on_edit>false</required_on_edit><required_on_create>false</required_on_create></arg>
            <arg name="splunk_web_scheme"><title>Legacy Param (Ignored)</title><required_on_edit>false</required_on_edit><required_on_create>false</required_on_create></arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    print('<?xml version="1.0" encoding="UTF-8"?>')
    sys.stdout.write(SCHEME)
    sys.stdout.flush()

def validate_arguments():
    # Always pass validation
    print('<error><message></message></error>') # No error
    sys.exit(0)

def run_main():
    # Signal handling to exit gracefully
    def handler(signum, frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    logger.info("Native Embedder v3.0.7 started. Proxy is disabled.")
    logger.info("Use native Splunk embedding: /en-US/app/<app>/<dashboard>?embed=1")
    
    # Idle loop to keep the input 'running' so Splunk doesn't restart it repeatedly
    while True:
        time.sleep(600)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scheme':
            do_scheme()
        elif sys.argv[1] == '--validate-arguments':
            validate_arguments()
    else:
        run_main()
