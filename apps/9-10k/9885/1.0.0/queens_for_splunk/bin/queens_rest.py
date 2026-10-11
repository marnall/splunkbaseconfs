"""
REST endpoints for saving Queens scores (see default/restmap.conf and web.conf):

  POST /services/queens/start   {"game_id": "..."}
  POST /services/queens/finish  {"session": "...", "queens": [...], "clicks": n, "hints": n, "mistakes": n}

The player is the logged-in Splunk user. Scores are written to the KV store with the
app's system token, so users only need read access to the queens_scores collection.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import splunk.rest  # noqa: E402
from splunk.persistconn.application import PersistentServerConnectionApplication  # noqa: E402

from queens_core import Game, Puzzles, QueensError  # noqa: E402

APP = "queens_for_splunk"


class KvStore:
    """Minimal KV store client for the app's collections."""

    def __init__(self, session_key):
        self.session_key = session_key

    def _path(self, collection, key=None):
        path = "/servicesNS/nobody/%s/storage/collections/data/%s" % (APP, collection)
        return "%s/%s" % (path, key) if key else path

    def _request(self, path, method="GET", body=None, getargs=None):
        response, content = splunk.rest.simpleRequest(
            path,
            sessionKey=self.session_key,
            method=method,
            jsonargs=json.dumps(body) if body is not None else None,
            getargs=getargs,
            raiseAllErrors=False,
        )
        status = int(response.status)
        if status == 404:
            return None
        if status >= 300:
            raise QueensError(502, "The KV store returned an error (%s)" % status)
        return json.loads(content) if content else None

    def insert(self, collection, record):
        return self._request(self._path(collection), "POST", record)["_key"]

    def get(self, collection, key):
        return self._request(self._path(collection, key))

    def update(self, collection, key, record):
        self._request(self._path(collection, key), "POST", record)

    def query(self, collection, query):
        return self._request(self._path(collection), getargs={"query": json.dumps(query)}) or []


PUZZLES = None


def puzzles():
    global PUZZLES  # loaded once per handler process
    if PUZZLES is None:
        PUZZLES = Puzzles.load()
    return PUZZLES


def error(status, message):
    return {"status": status, "payload": {"messages": [{"type": "ERROR", "text": message}]}}


class QueensHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            if request.get("method") != "POST":
                return error(405, "Use POST")
            user = request["session"]["user"]
            body = json.loads(request.get("payload") or "{}")
            game = Game(KvStore(request["system_authtoken"]), puzzles())
            action = (request.get("path_info") or "").strip("/")
            if action == "start":
                return {"status": 200, "payload": game.start(user, body.get("game_id"))}
            if action == "finish":
                return {"status": 200, "payload": game.finish(user, body)}
            return error(404, "Unknown action %s" % action)
        except QueensError as e:
            return error(e.status, e.message)
        except (ValueError, KeyError) as e:
            return error(400, "Bad request: %s" % e)
