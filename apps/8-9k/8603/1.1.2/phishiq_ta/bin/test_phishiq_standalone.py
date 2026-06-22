#!/usr/bin/env python3
"""
Standalone test for PhishIQ API client (no Splunk required).
Usage:
  export PHISHIQ_BASE_URL="https://phishiq-api-xxx.run.app"
  export PHISHIQ_API_KEY="your-api-key"
  python test_phishiq_standalone.py
"""

from __future__ import print_function

import os
import sys

# Ensure bin/ is on path for phishiq_client
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from phishiq_client import PhishIQClient
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)


def main():
    base_url = os.environ.get("PHISHIQ_BASE_URL", "").strip()
    api_key = os.environ.get("PHISHIQ_API_KEY", "").strip()

    if not base_url or not api_key:
        print("Set PHISHIQ_BASE_URL and PHISHIQ_API_KEY environment variables.")
        print("Example:")
        print('  export PHISHIQ_BASE_URL="https://phishiq-api-xxx.run.app"')
        print('  export PHISHIQ_API_KEY="your-api-key"')
        sys.exit(1)

    client = PhishIQClient(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=30,
        ssl_verify=True,
        cache_enabled=True,
        cache_ttl_seconds=300,
        cache_max_entries=100,
    )

    print("1. Test connection...")
    ok, msg = client.test_connection()
    if not ok:
        print("   FAIL:", msg)
        sys.exit(1)
    print("   OK:", msg)

    print("\n2. Single URL predict...")
    url = "https://www.google.com"
    single = client.predict_single(url)
    if single:
        print("   URL:", url)
        print("   prediction:", single.get("prediction"), "source:", single.get("source"))
        print("   confidence:", single.get("confidence"), "risk_level:", single.get("risk_level"))
    else:
        print("   No response")

    print("\n3. Batch predict...")
    urls = ["https://www.google.com", "https://example.com"]
    batch = client.predict_batch(urls)
    for i, (u, p) in enumerate(zip(urls, batch)):
        if p:
            print("   [%d] %s -> prediction=%s risk=%s" % (i, u[:50], p.get("prediction"), p.get("risk_level")))
        else:
            print("   [%d] %s -> (no response)" % (i, u[:50]))

    print("\nDone. Enriched fields you would see in Splunk: phishiq_prediction, phishiq_source, phishiq_confidence, phishiq_risk_level, phishiq_cached, phishiq_domain, phishiq_analysis_time.")


if __name__ == "__main__":
    main()
