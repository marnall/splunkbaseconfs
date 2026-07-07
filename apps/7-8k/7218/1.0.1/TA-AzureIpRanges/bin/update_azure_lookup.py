"""
update_azure_lookup.py

Script for downloading MS's published Azure IP ranges and building them into a lookup table

"""

import csv
import os
import sys

import requests

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", "TA-AzureIpRanges", "lib"))
from bs4 import BeautifulSoup

ID = 56519


def main():
    """
    Main function
    """
    url = f"https://www.microsoft.com/en-us/download/details.aspx?id={ID}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"  # pylint: disable=line-too-long
    }
    resp = requests.get(url, headers=headers, timeout=120)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    download_link = soup.find(string="Download").parent.parent["href"]
    ranges_resp = requests.get(download_link, headers=headers, timeout=120)
    ranges_resp.raise_for_status()
    all_service_tags = ranges_resp.json()["values"]

    lookup_path = os.path.join(
        splunkhome,
        "etc",
        "apps",
        "TA-AzureIpRanges",
        "lookups",
        "azure_public_ip_ranges.csv",
    )

    with open(lookup_path, "w", encoding="utf-8") as csv_f:
        writer = csv.writer(csv_f)
        writer.writerow(["serviceTag", "region", "regionId", "systemService", "prefix"])

        for item in all_service_tags:
            service_tag = item["id"]
            region = item["properties"]["region"]
            region_id = item["properties"]["regionId"]
            system_service = item["properties"]["systemService"]
            address_prefixes = item["properties"]["addressPrefixes"]
            for prefix in address_prefixes:
                writer.writerow(
                    [service_tag, region, region_id, system_service, prefix]
                )


if __name__ == "__main__":
    main()
