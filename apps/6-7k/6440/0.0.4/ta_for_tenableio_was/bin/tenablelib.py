import sys
import argparse
import os
import json
import requests
from loguru import logger
from datetime import datetime, timedelta
import time


class tenablelib:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def get_results(self, max_hours_ago: int):
        results = []

        # Get a list of web application scan configurations.
        # If a scan has been run using the configuration, the list also contains information about the last scan that was run.
        # NOTE - no support for pagination currently; if you have more then 200 scan configurations, not all will be retrieved
        # Ref: https://developer.tenable.com/reference/was-v2-config-search
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        headers["X-ApiKeys"] = self._api_key
        url = "https://cloud.tenable.com/was/v2/configs/search?limit=200&offset=0"

        response = requests.post(url, headers=headers, verify=True)

        if response.json()["pagination"]["total"] > 0:
            for item in response.json()["items"]:
                if not item["last_scan"]:
                    continue

                # ignore scans that haven't completed
                if item["last_scan"]["status"] != "completed":
                    continue

                # ignore scans finalize more than x hours ago
                finalized_at = item["last_scan"]["finalized_at"]
                dt = datetime.strptime(finalized_at, "%Y-%m-%dT%H:%M:%S.%fZ")

                now = datetime.now()
                if not now - timedelta(hours=max_hours_ago) <= dt <= now:
                    continue

                scan_id = item["last_scan"]["scan_id"]
                logger.info(f"Working with scan_id: {scan_id}")
                logger.debug(f'last_scan: {item["last_scan"]}')

                # Get full scan report
                # Ref: https://developer.tenable.com/reference/was-v2-scans-export
                url = f"https://cloud.tenable.com/was/v2/scans/{scan_id}/report"

                # request an export be prepared
                response = requests.put(url, headers=headers, verify=True)

                # download it
                # Note: A 404 Not Found is returned if the requested report is not yet ready for download
                time.sleep(2)
                response = requests.get(url, headers=headers, verify=True)
                if response.status_code == 404:
                    time.sleep(5)
                response = requests.get(url, headers=headers, verify=True)
                if response.status_code != 200:
                    logger.error(f"Problem retrieving {url}")
                else:
                    logger.debug(
                        f"Adding full report to results[] with length {len(json.dumps(response.json()))}"
                    )
                    results.append(response.json())

        return results


#################################################


def main() -> int:
    parser = argparse.ArgumentParser(description="Query tenable.io for WAS results")
    parser.add_argument("--max_hours_ago", nargs=1, required=False)
    args = parser.parse_args()

    if args.max_hours_ago:
        max_hours_ago = args.max_hours_ago[0]
    else:
        max_hours_ago = 24

    if "TENABLEIO_API_KEY" in os.environ:
        api_key = os.environ["TENABLEIO_API_KEY"]
    else:
        logger.error("Store API key in env var for testing: TENABLEIO_API_KEY")
        logger.error("e.g. export TENABLEIO_API_KEY=your_api_key_here")
        return 1

    tlib = tenablelib(api_key=api_key)
    results = tlib.get_results(max_hours_ago=max_hours_ago)
    logger.debug(results)


if __name__ == "__main__":
    sys.exit(main())
