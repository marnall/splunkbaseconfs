#!/usr/bin/env python3
import requests
import json
import sys

API_URL = "https://gtks.border-innovation.com/api/clicks"
ACK_URL = "https://gtks.border-innovation.com/api/clicks/received"

def main():
    r = requests.get(API_URL)
    rows = r.json()

    output = []
    ids = []

    for row in rows:
        output.append(json.dumps({
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "action": row["action"],
            "_time": row["timestamp"],
            "ip": row["ip"],
            "domain": row["domain"],
            "validated_at": row["validated_at"],
            "last_ingested_action": row["last_ingested_action"]
        }))
        ids.append(row["id"])

    for line in output:
        print(line)

    sys.stdout.flush()

if __name__ == "__main__":
    main()