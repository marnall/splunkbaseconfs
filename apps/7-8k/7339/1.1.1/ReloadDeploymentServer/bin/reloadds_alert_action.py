import sys
import json
import requests
from splunk.rest import simpleRequest


def log(msg, *args):
    sys.stderr.write(msg + " ".join([str(a) for a in args]) + "\n")


if __name__ == "__main__":
    log("INFO Running python %s" % (sys.version_info[0]))
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        session_key = payload["session_key"]
        log("POSTing to reload endpoint")
        simpleRequest(
            "/services/deployment/server/config/_reload",
            sessionKey=session_key,
            method="POST",
            timeout=30,
        )
        log("Success!")
