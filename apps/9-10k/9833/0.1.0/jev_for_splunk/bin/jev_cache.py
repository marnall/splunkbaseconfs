"""Answer cache for the `jev` command, against an injected key-value interface.

A cancelled search loses its results but keeps its bill. The command therefore stores every
answer as soon as a slice of rows is done, keyed by everything that determines the answer: the
model, the questions and the state. A rerun finds the finished slices here and pays nothing for
them. Only the key (a hash) and the answers are stored, never the state.

The kv object needs three methods: query(dict) -> list of documents, batch_save(list of
documents), delete(dict). jev.py adapts a Splunk KV store collection to it; tests pass a fake.
"""
import hashlib
import json
import time

LOOKUP_BATCH = 40  # keys per query: the query travels in a URL


class CacheUnavailable(Exception):
    """The key-value store could not be read or written."""


def cache_key(model, questions, state):
    canonical = json.dumps([model, questions, state], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class Cache:
    def __init__(self, kv, lifetime_days=30, now=time.time):
        self.kv, self.lifetime, self.now = kv, float(lifetime_days) * 86400, now

    def get_many(self, keys):
        """{key: {"answers": ..., "model": ...}} for the keys that are stored and not expired."""
        keys, oldest, found = sorted(set(keys)), self.now() - self.lifetime, {}
        try:
            for i in range(0, len(keys), LOOKUP_BATCH):
                for doc in self.kv.query({"$or": [{"_key": k} for k in keys[i:i + LOOKUP_BATCH]]}):
                    if float(doc.get("created", 0)) >= oldest:
                        found[doc["_key"]] = {"answers": json.loads(doc["answers"]), "model": doc.get("model", "")}
        except Exception as e:
            raise CacheUnavailable(str(e))
        return found

    def put_many(self, replies):
        """replies: {key: API reply}. Answers are stored as a JSON string because option names
        may contain characters a KV store field name may not."""
        if not replies:
            return
        created = self.now()
        try:
            self.kv.batch_save([{"_key": k, "answers": json.dumps(r["answers"], sort_keys=True),
                                 "model": r.get("model", ""), "created": created} for k, r in replies.items()])
        except Exception as e:
            raise CacheUnavailable(str(e))

    def purge(self):
        """Delete expired entries. Housekeeping only: nothing leaves Splunk."""
        try:
            self.kv.delete({"created": {"$lt": self.now() - self.lifetime}})
        except Exception as e:
            raise CacheUnavailable(str(e))
