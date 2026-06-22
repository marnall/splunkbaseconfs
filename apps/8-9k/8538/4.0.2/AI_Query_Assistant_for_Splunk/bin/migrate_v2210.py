"""
One-shot KV cleanup for the 2.2.9 -> 3.0.x upgrade path (audit issue #14).

The filename retains its 2210 suffix because that is when the migration was
introduced; it remains the correct script for any upgrade originating from a
2.2.x install (including direct jumps to 3.0.x).

WHEN TO RUN
-----------
Run this once after upgrading the AI Query Assistant for Splunk app from
any 2.2.x release to 3.0.x. It scrubs any leftover plaintext `api_key` values
out of the `mcp_ai_providers` KV collection.

Two scenarios are handled:

1. Post-migration leftover: a record has BOTH `api_key` and `credential_key`.
   The plaintext `api_key` is just stripped (the secret is already in
   storage/passwords under `credential_key`).

2. Pre-migration record: a record has `api_key` but no `credential_key`.
   The script first writes the secret to storage/passwords using a key of
   the form `mcp_provider_<provider_id>` (matching the runtime handler in
   `mcp_providers_handler.py`), THEN strips `api_key` from the KV record.
   If writing to storage/passwords fails, the record is logged and skipped
   so we never lose the secret without a safe replacement.

The script is idempotent: re-running it on a fully-migrated dataset
reports `migrated=0 stripped=0 errors=0` and exits 0.

This script is intentionally NOT registered as a Splunk script input or
on-restart hook — that would re-run it every boot, which is wasteful and
surprising. It is also intentionally NOT scheduled via savedsearches.conf
for the same reason. Run it manually exactly once.

HOW TO RUN
----------
The standard Splunk pattern is to feed the session key on stdin:

    echo "$SPLUNK_SESSION_KEY" | \\
        $SPLUNK_HOME/bin/splunk cmd python \\
        $SPLUNK_HOME/etc/apps/AI_Query_Assistant_for_Splunk/bin/migrate_v2210.py

Where `$SPLUNK_SESSION_KEY` is a session key for an admin-capable user
(obtain via `splunk login`/REST `auth/login`). The script prints a
single-line summary `migrated=N stripped=M errors=K` and exits 0 on
success or 1 on failure.
"""
import sys
import os
import logging

# Add lib directory to path (matches history_cleanup.py).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from splunklib import client  # noqa: E402
from kv_store import KVStoreClient, KVStoreError  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

APP_NAME = 'AI_Query_Assistant_for_Splunk'
PROVIDERS_COLLECTION = 'mcp_ai_providers'


def _credential_key_for(provider_id):
    """Mirror the naming used by mcp_providers_handler.py."""
    pid = (provider_id or '').replace('-', '_')
    return 'mcp_provider_%s' % pid


def _store_password(service, key, value):
    """Create or overwrite a storage/passwords entry in the app context.

    Returns True on success, False on failure.
    """
    try:
        passwords = service.storage_passwords
        # If an entry already exists, delete it first so we can rewrite
        # cleanly (storage/passwords does not support in-place value update
        # via the create() endpoint).
        existing_name = ':%s:' % key
        for p in passwords:
            try:
                if p.name == existing_name and p.username == key:
                    p.delete()
                    break
            except Exception:
                # Best-effort cleanup; keep going.
                continue
        passwords.create(password=value, username=key, realm='')
        return True
    except Exception as e:
        logger.error("Failed to store password '%s': %s", key, e)
        return False


def migrate_providers(session_key):
    """Walk mcp_ai_providers and scrub stray api_key fields.

    Returns a tuple (migrated, stripped, errors).
    """
    migrated = 0
    stripped = 0
    errors = 0

    try:
        service = client.connect(
            token=session_key,
            owner='nobody',
            app=APP_NAME,
        )
    except Exception as e:
        logger.error("Failed to connect to splunkd: %s", e)
        return migrated, stripped, errors + 1

    try:
        kv = KVStoreClient(service, PROVIDERS_COLLECTION)
    except Exception as e:
        # Collection may not exist yet on a brand-new install. That's fine —
        # nothing to migrate.
        logger.info("Collection '%s' not available (%s); nothing to do.",
                    PROVIDERS_COLLECTION, e)
        return migrated, stripped, errors

    # Page through everything. KVStoreClient.query enforces a 10k cap per
    # call, so loop until we get a short page.
    PAGE = 1000
    skip = 0
    while True:
        try:
            records = kv.query(query={}, limit=PAGE, skip=skip)
        except KVStoreError as e:
            logger.error("Query failed at skip=%d: %s", skip, e)
            errors += 1
            break

        if not records:
            break

        for record in records:
            record_id = record.get('_key')
            api_key = record.get('api_key') or ''
            credential_key = record.get('credential_key') or ''

            if not api_key:
                # Already clean.
                continue

            try:
                if credential_key:
                    # Case 1: post-migration leftover. Just strip api_key.
                    record.pop('api_key', None)
                    kv.update(record_id, record)
                    stripped += 1
                    logger.info(
                        "Stripped leftover api_key from record %s "
                        "(credential_key=%s)", record_id, credential_key,
                    )
                else:
                    # Case 2: pre-migration record. Move api_key into
                    # storage/passwords first, THEN strip.
                    provider_id = record.get('provider_id') or record_id
                    new_key = _credential_key_for(provider_id)
                    if not _store_password(service, new_key, api_key):
                        logger.warning(
                            "Skipping record %s: could not store password "
                            "under '%s'", record_id, new_key,
                        )
                        errors += 1
                        continue
                    record['credential_key'] = new_key
                    record.pop('api_key', None)
                    kv.update(record_id, record)
                    migrated += 1
                    logger.info(
                        "Migrated record %s -> credential_key=%s",
                        record_id, new_key,
                    )
            except Exception as e:
                logger.error("Failed to process record %s: %s", record_id, e)
                errors += 1

        if len(records) < PAGE:
            break
        skip += len(records)

    return migrated, stripped, errors


if __name__ == '__main__':
    # Standard Splunk pattern: session key arrives on stdin.
    session_key = sys.stdin.readline().strip()

    if not session_key:
        logger.error("No session key provided on stdin")
        sys.exit(1)

    try:
        migrated, stripped, errors = migrate_providers(session_key)
        # Single-line, machine-parseable summary.
        print("migrated=%d stripped=%d errors=%d" % (migrated, stripped, errors))
        logger.info(
            "migrate_v2210 complete: migrated=%d stripped=%d errors=%d",
            migrated, stripped, errors,
        )
        sys.exit(0 if errors == 0 else 1)
    except Exception:
        logger.exception("migrate_v2210 failed")
        sys.exit(1)
