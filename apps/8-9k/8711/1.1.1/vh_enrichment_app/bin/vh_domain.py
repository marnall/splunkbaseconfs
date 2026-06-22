#!/usr/bin/env python3
"""Placeholder for the future vh_domain streaming enrichment command.

Planned shape (NOT yet wired into commands.conf):
    ... | vh_domain domain_field=<field>

Will mirror vh_ip but key the KV lookup on a domain field. Implementing this
also requires adding a domain-keyed KV collection and modular-input ingestion
path; until that exists, this file is intentionally inert.
"""

raise NotImplementedError("vh_domain is not implemented yet")
