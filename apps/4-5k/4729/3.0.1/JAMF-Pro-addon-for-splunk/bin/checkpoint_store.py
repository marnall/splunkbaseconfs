"""Last-seen-timestamp checkpoints per modular-input stanza.

Wraps splunktaucclib's ``helper.get_check_point`` / ``helper.save_check_point``
so the input modules can record "I've already emitted everything up to this
reportDate" and skip pre-checkpoint records on subsequent runs.

State lives in the framework's per-input checkpoint store at
``$SPLUNK_HOME/var/lib/splunk/modinputs/<input>/``.

Why a separate module: items 6 and 7 in the 3.0.0 implementation plan
(``skip_unchanged`` for computers + for mobile devices) both need this.
Sharing the key-naming convention and the float-serialization here means
the two inputs can't drift apart.

Failure mode contract: all functions degrade silently to "no checkpoint"
on any framework-side error. ``skip_unchanged`` is an optimization, not a
correctness requirement — a failed read means we scan everything, a failed
write means we'll scan everything again next time. Both are recoverable on
the next fire.
"""

import import_declare_test  # noqa: F401  pylint: disable=unused-import

import logging


_LOGGER = logging.getLogger("checkpoint_store")


def _key(input_type, stanza_name):
    """Build a stable per-stanza checkpoint key.

    The framework's checkpoint store is keyed by an arbitrary string; the
    composite key here lets multiple stanzas of the same input type each
    keep their own state without collision.
    """
    return "{}_{}_last_seen_epoch".format(input_type, stanza_name)


def read(helper, input_type, stanza_name):
    """Return the last-seen reportDate epoch (float) for this stanza, or None.

    None is returned on:
      - first run for this stanza (no checkpoint yet),
      - the stored value is missing or non-numeric (treat as no checkpoint),
      - the framework call raises (treat as no checkpoint, log a warning).

    Callers must treat None as "scan everything" — that's the safe default.
    """
    try:
        raw = helper.get_check_point(_key(input_type, stanza_name))
    except Exception as exc:  # pragma: no cover
        _LOGGER.warning(
            "checkpoint_store: read failed for %s/%s: %s",
            input_type, stanza_name, exc,
        )
        return None

    if raw is None:
        return None

    try:
        return float(raw)
    except (TypeError, ValueError):
        _LOGGER.warning(
            "checkpoint_store: discarding non-numeric checkpoint for %s/%s: %r",
            input_type, stanza_name, raw,
        )
        return None


def write(helper, input_type, stanza_name, epoch):
    """Persist the latest-seen reportDate epoch for this stanza.

    Stored as a string for portability across framework versions. A failed
    write logs a warning and returns; the caller does not need to handle the
    exception, but the next run will see a stale (or missing) checkpoint
    and scan more than necessary.
    """
    try:
        helper.save_check_point(
            _key(input_type, stanza_name),
            str(float(epoch)),
        )
    except (TypeError, ValueError) as exc:
        # Bad input — epoch isn't numeric. Log loudly; this is a caller bug.
        _LOGGER.warning(
            "checkpoint_store: refusing to write non-numeric epoch for %s/%s: %r (%s)",
            input_type, stanza_name, epoch, exc,
        )
    except Exception as exc:  # pragma: no cover
        _LOGGER.warning(
            "checkpoint_store: write failed for %s/%s: %s",
            input_type, stanza_name, exc,
        )


def delete(helper, input_type, stanza_name):
    """Drop the checkpoint for this stanza — forces a full scan on next run.

    Not used in the normal path; provided for explicit resets (e.g. an admin
    disables ``skip_unchanged`` and wants to re-baseline, or a manual conf
    change requires re-reading all records).
    """
    try:
        helper.delete_check_point(_key(input_type, stanza_name))
    except Exception as exc:  # pragma: no cover
        _LOGGER.warning(
            "checkpoint_store: delete failed for %s/%s: %s",
            input_type, stanza_name, exc,
        )
