#!/usr/bin/env python

import sys
import os
import subprocess
import platform

PING_COUNT = 1
LINUX_TIMEOUT_SECONDS = 2
WINDOWS_TIMEOUT_MILLISECONDS = 2000

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (dispatch, StreamingCommand, Configuration, Option, validators,)


def parse_ping_result(system_type, returncode, output):
    output = output.lower()

    if returncode == 0:
        return "success"

    if system_type == "windows":
        if "could not find host" in output:
            return "invalid_host"
        elif "destination host unreachable" in output:
            return "unreachable"
        elif "request timed out" in output:
            return "timeout"
        else:
            return "error"
    else:  # Linux/macOS
        if "name or service not known" in output or "unknown host" in output:
            return "invalid_host"
        elif "100% packet loss" in output:
            return "unreachable"
        elif "0 packets received" in output:
            return "timeout"
        else:
            return "error"

@Configuration()
class PingCommand(StreamingCommand):

    fieldname = Option(
        doc='''
        **Syntax:** **fieldname=***<fieldname>*
        **Description:** Name of the field that will hold ping results''',
        require=True, validate=validators.Fieldname())

    ping_target_field = Option(
        doc='''
        **Syntax:** **ping_target_field=***<fieldname>*
        **Description:** Name of the field that will contain hostname/ip ping target''',
        require=True, validate=validators.Fieldname())

    def stream(self, events):
        system_type = platform.system().lower()

        for event in events:
#            for host in self.ping_target_field:
            host=event.get(self.ping_target_field)
            try:
                if system_type == "windows":
                    cmd = ["ping", "-n", str(PING_COUNT), "-w", str(WINDOWS_TIMEOUT_MILLISECONDS), host]
                else:
                   cmd = ["ping", "-c", str(PING_COUNT), "-W", str(LINUX_TIMEOUT_SECONDS), host]

                result = subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

                full_output = result.stdout + result.stderr
                event[self.fieldname] = parse_ping_result(system_type, result.returncode, full_output)
            except Exception as e:
                # Unexpected errors
                event[self.fieldname] = 'command error'
            yield event

dispatch(PingCommand, sys.argv, sys.stdin, sys.stdout, __name__)
