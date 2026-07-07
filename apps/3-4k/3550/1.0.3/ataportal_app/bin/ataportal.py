import sys
from json import dumps, loads
from requests import post


def extract(inp):
    """Extract only what we need from input"""
    for k, v in inp["result"].items():
        # flatten, there is no reason to send a nested dict
        inp[k] = v

    return inp


def send_to_ata(arg):
    """ Send the entire argument passed"""
    configuration = arg.pop("configuration")
    dest = configuration["base_url"]
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Splunk/ataportal_app"
    }

    body = extract(arg)
    body["psa_id"] = configuration["psa_id"]
    body["auth_token"] = configuration["auth_token"]
    body["search_query"] = configuration["search_query"]
    body["search_earliest"] = configuration["search_earliest"]
    body["search_latest"] = configuration["search_latest"]

    # Optional fields that we ask the user during alert setup
    if configuration.get("title"):
        body["ata_incident_title_override"] = configuration["title"]
    if configuration.get("group_by"):
        body["ata_event_nuance_override"] = configuration["group_by"]
    if configuration.get("event_type"):
        body["event_type"] = configuration["event_type"]
    if configuration.get("priority"):
        body["event_priority"] = configuration["priority"]
    if configuration.get("category"):
        body["event_category"] = configuration["category"]

    response = post(dest, data=dumps(body), headers=headers, verify=False)
    if not response.ok:
        response.raise_for_status()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        msg = "FATAL Unsupported execution mode (expected --execute flag)"
        sys.stderr.write(msg + '\n')
        sys.exit(1)
    try:
        send_to_ata(loads(sys.stdin.read()))
    except Exception as e:
        sys.stderr.write("ERROR Unexpected error: %s" % e + '\n')
        sys.exit(3)
