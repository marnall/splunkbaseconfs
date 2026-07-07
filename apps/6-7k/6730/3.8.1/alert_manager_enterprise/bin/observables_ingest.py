#!/usr/bin/env python3.9
#
# File: observables_ingest.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from ame.modalerts.ObservablesIngest import ObservablesIngest
from dpshared.modularalert.ModularAlert import EXECUTE_FLAG

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            modular_alert = ObservablesIngest.create_from_stdin()
            sys.exit(modular_alert.execute())
        except Exception:
            print("EXCEPTION: Observable Ingest modular alert execution failed")  # noqa: T201
    else:
        print(f"FAILED: Unsupported execution mode (expected {EXECUTE_FLAG} flag)")  # noqa: T201

    sys.exit(1)
