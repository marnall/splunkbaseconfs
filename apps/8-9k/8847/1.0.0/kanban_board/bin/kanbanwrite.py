#!/usr/bin/env python3
"""
kanbanwrite — Splunk streaming command for KV Store kanban writes.

Usage (in a search):
    | makeresults | kanbanwrite payload="<json-envelope-string>"

The payload is a JSON envelope:
    {
        "op":     "board.upsert" | "board.delete" | "card.upsert" | "card.delete" | "card.move",
        "key":    "<_key, empty or absent means create>",
        "record": { ...op-specific fields... },   (not required for delete ops)
        "nonce":  <integer, echoed back in the ack row>
    }

Emits exactly one ack row: {_time, status, op, nonce, key, detail}
"""

import os
import sys
import json
import time

# Vendor path — kanban_board/lib is sibling of bin
_LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
sys.path.insert(0, _LIB)

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option
import splunklib.client as client


# ---------------------------------------------------------------------------
# parse_envelope — standalone helper so tests can exercise it independently
# ---------------------------------------------------------------------------

def parse_envelope(payload_str):
    """
    Parse a JSON envelope string.

    Returns:
        (envelope_dict, None) on success
        (None, error_string)  on failure
    """
    if not payload_str:
        return None, 'payload is empty'
    try:
        env = json.loads(payload_str)
    except (ValueError, TypeError) as exc:
        return None, 'malformed JSON payload: {}'.format(exc)
    if not isinstance(env, dict):
        return None, 'payload must be a JSON object'
    return env, None


# ---------------------------------------------------------------------------
# KanbanOps — pure op logic, fully unit-testable without Splunk
# ---------------------------------------------------------------------------

class KanbanOps(object):
    """
    Executes kanban envelope ops against a KV-store-like interface.

    kv duck-type contract:
        get(collection, key)              -> dict | None
        insert(collection, data)          -> {'_key': str}
        update(collection, key, data)     -> None
        delete(collection, key)           -> None
        delete_by_query(collection, query_dict) -> None
    """

    _BOARD_COLLECTION = 'kanban_boards'
    _CARD_COLLECTION  = 'kanban_cards'

    # Ops that require a non-empty key
    _KEY_REQUIRED_OPS = frozenset({'card.move', 'board.delete', 'card.delete'})

    def __init__(self, kv, username, now_fn=None):
        self._kv       = kv
        self._username = username
        self._now      = now_fn if now_fn is not None else lambda: int(time.time())

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def execute(self, envelope):
        """
        Execute a single kanban envelope operation.

        Returns an ack dict: {status, op, nonce, key, detail}
        Never raises — errors are returned as status='error'.
        """
        op    = envelope.get('op', '')
        nonce = envelope.get('nonce')
        key   = envelope.get('key', '') or ''  # normalise None -> ''

        try:
            if not op:
                return self._error(op, nonce, key, 'envelope is missing "op" field')

            # Validate key requirement
            if op in self._KEY_REQUIRED_OPS and not key:
                return self._error(op, nonce, key,
                                   'op "{}" requires a non-empty "key"'.format(op))

            # Dispatch
            if op == 'board.upsert':
                result_key = self._board_upsert(key, envelope.get('record', {}))
            elif op == 'board.delete':
                result_key = self._board_delete(key)
            elif op == 'card.upsert':
                result_key = self._card_upsert(key, envelope.get('record', {}))
            elif op == 'card.delete':
                result_key = self._card_delete(key)
            elif op == 'card.move':
                result_key = self._card_move(key, envelope.get('record', {}))
            else:
                return self._error(op, nonce, key,
                                   'unknown op "{}"; expected one of board.upsert, '
                                   'board.delete, card.upsert, card.delete, '
                                   'card.move'.format(op))

        except _KanbanError as exc:
            return self._error(op, nonce, key, str(exc))
        except Exception as exc:
            return self._error(op, nonce, key,
                               'unexpected error: {}'.format(exc))

        return {
            'status': 'ok',
            'op':     op,
            'nonce':  nonce,
            'key':    result_key or key,
            'detail': 'ok',
        }

    # ------------------------------------------------------------------
    # Op implementations
    # ------------------------------------------------------------------

    def _board_upsert(self, key, record):
        record = self._clean_record(record)
        now    = self._now()

        if key:
            existing = self._kv.get(self._BOARD_COLLECTION, key)
            if existing is None:
                raise _KanbanError(
                    'board.upsert: key "{}" not found'.format(key))
            merged = dict(existing)
            merged.update(record)
            # Preserve immutable audit fields
            merged['created']    = existing.get('created', now)
            merged['created_by'] = existing.get('created_by', self._username)
            merged['modified']    = now
            merged['modified_by'] = self._username
            self._kv.update(self._BOARD_COLLECTION, key, merged)
            return key
        else:
            doc = dict(record)
            doc['created']    = now
            doc['created_by'] = self._username
            doc['modified']    = now
            doc['modified_by'] = self._username
            result = self._kv.insert(self._BOARD_COLLECTION, doc)
            return result['_key']

    def _board_delete(self, key):
        existing = self._kv.get(self._BOARD_COLLECTION, key)
        if existing is None:
            raise _KanbanError('board.delete: board key "{}" not found'.format(key))
        # Cascade: delete all cards belonging to this board
        self._kv.delete_by_query(self._CARD_COLLECTION, {'board_id': key})
        self._kv.delete(self._BOARD_COLLECTION, key)
        return key

    def _card_upsert(self, key, record):
        record = self._clean_record(record)
        # Coerce sort_order to float
        if 'sort_order' in record:
            try:
                record['sort_order'] = float(record['sort_order'])
            except (TypeError, ValueError):
                pass
        now = self._now()

        if key:
            existing = self._kv.get(self._CARD_COLLECTION, key)
            if existing is None:
                raise _KanbanError(
                    'card.upsert: key "{}" not found'.format(key))
            merged = dict(existing)
            merged.update(record)
            # Preserve immutable audit fields
            merged['created']    = existing.get('created', now)
            merged['created_by'] = existing.get('created_by', self._username)
            merged['modified']    = now
            merged['modified_by'] = self._username
            self._kv.update(self._CARD_COLLECTION, key, merged)
            return key
        else:
            doc = dict(record)
            doc['created']    = now
            doc['created_by'] = self._username
            doc['modified']    = now
            doc['modified_by'] = self._username
            result = self._kv.insert(self._CARD_COLLECTION, doc)
            return result['_key']

    def _card_delete(self, key):
        existing = self._kv.get(self._CARD_COLLECTION, key)
        if existing is None:
            raise _KanbanError('card.delete: card key "{}" not found'.format(key))
        self._kv.delete(self._CARD_COLLECTION, key)
        return key

    def _card_move(self, key, record):
        existing = self._kv.get(self._CARD_COLLECTION, key)
        if existing is None:
            raise _KanbanError('card.move: card key "{}" not found'.format(key))
        merged = dict(existing)
        # Only apply column_id and sort_order from record (partial merge)
        if 'column_id' in record:
            merged['column_id'] = record['column_id']
        if 'sort_order' in record:
            try:
                merged['sort_order'] = float(record['sort_order'])
            except (TypeError, ValueError):
                merged['sort_order'] = record['sort_order']
        now = self._now()
        merged['modified']    = now
        merged['modified_by'] = self._username
        self._kv.update(self._CARD_COLLECTION, key, merged)
        return key

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_record(record):
        """Remove internal KV Store fields that must not be set by callers."""
        cleaned = dict(record)
        for field in ('_key', '_user'):
            cleaned.pop(field, None)
        return cleaned

    @staticmethod
    def _error(op, nonce, key, detail):
        return {
            'status': 'error',
            'op':     op,
            'nonce':  nonce,
            'key':    key or '',
            'detail': detail,
        }


class _KanbanError(Exception):
    """Internal error raised within op implementations to produce an error ack."""
    pass


# ---------------------------------------------------------------------------
# SplunkKv — adapts splunklib KV Store data API to KanbanOps duck-type
# ---------------------------------------------------------------------------

class SplunkKv(object):
    """
    KV duck-type backed by splunklib.client, using app=kanban_board, owner=nobody.
    """

    def __init__(self, service):
        self._service = service

    def _collection(self, name):
        return self._service.kvstore[name].data

    def get(self, collection, key):
        try:
            return self._collection(collection).query_by_id(key)
        except Exception:
            # 404 (not found) or any other error → treat as missing
            return None

    def insert(self, collection, data):
        result_str = self._collection(collection).insert(json.dumps(data))
        if isinstance(result_str, str):
            return json.loads(result_str)
        return result_str

    def update(self, collection, key, data):
        self._collection(collection).update(key, json.dumps(data))

    def delete(self, collection, key):
        self._collection(collection).delete_by_id(key)

    def delete_by_query(self, collection, query_dict):
        self._collection(collection).delete(query=json.dumps(query_dict))


# ---------------------------------------------------------------------------
# KanbanWriteCommand — thin Splunk streaming command wrapper
# ---------------------------------------------------------------------------

@Configuration()
class KanbanWriteCommand(StreamingCommand):
    """Apply a kanban board write operation to the app's KV Store collections."""

    payload = Option(require=True,
                     doc='JSON envelope string describing the write operation.')

    def stream(self, records):
        # Consume all input records (typically one makeresults row)
        for _ in records:
            pass

        op    = ''
        nonce = None
        key   = ''

        try:
            envelope, parse_err = parse_envelope(self.payload)
            if parse_err:
                yield self._ack_row(
                    status='error', op=op, nonce=nonce,
                    key=key, detail=parse_err)
                return

            op    = envelope.get('op', '')
            nonce = envelope.get('nonce')
            key   = envelope.get('key', '') or ''

            # Connect to Splunk via the searchinfo metadata
            si      = self._metadata.searchinfo
            uri     = si.splunkd_uri          # e.g. "https://127.0.0.1:8089"
            token   = si.session_key
            username = si.username

            # Parse scheme/host/port from splunkd_uri
            from urllib.parse import urlparse
            parsed = urlparse(uri)
            scheme = parsed.scheme or 'https'
            host   = parsed.hostname or '127.0.0.1'
            port   = parsed.port or 8089

            service = client.connect(
                scheme=scheme,
                host=host,
                port=port,
                splunkToken=token,
                app='kanban_board',
                owner='nobody',
            )

            kv   = SplunkKv(service)
            ops  = KanbanOps(kv, username)
            ack  = ops.execute(envelope)

        except Exception as exc:
            yield self._ack_row(
                status='error', op=op, nonce=nonce,
                key=key, detail='command error: {}'.format(exc))
            return

        yield self._ack_row(
            status=ack['status'],
            op=ack['op'],
            nonce=ack['nonce'],
            key=ack.get('key', key),
            detail=ack.get('detail', ''),
        )

    @staticmethod
    def _ack_row(status, op, nonce, key, detail):
        return {
            '_time':  int(time.time()),
            'status': status,
            'op':     op or '',
            'nonce':  nonce,
            'key':    key or '',
            'detail': detail or '',
        }


# ---------------------------------------------------------------------------
# Entry point — guarded so plain import does NOT execute dispatch()
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    dispatch(KanbanWriteCommand, sys.argv, sys.stdin, sys.stdout, __name__)
