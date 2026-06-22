"""Generating search command for Whisper Knowledge Graph schema introspection.

``| whisperschema [mode=labels|relationships|properties|schema|full]``

Queries the Whisper API for graph schema information including node labels,
relationship types, property keys, and rich schema metadata with descriptions,
examples, counts, fast/slow patterns, and best practices.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch  # noqa: E402
from whisper_query_command import WhisperSchemaCommand  # noqa: E402

if __name__ == "__main__":
    dispatch(WhisperSchemaCommand, sys.argv, sys.stdin, sys.stdout, __name__)
