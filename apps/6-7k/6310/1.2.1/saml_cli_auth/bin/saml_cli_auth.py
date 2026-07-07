import argparse
import json
import os
import socket
import sys
import time
import uuid

import splunk
from future.moves.urllib.parse import urlparse, urlunparse
from splunk.clilib import cli_common
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


# Add app lib directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from defusedxml import minidom  # pylint: disable=wrong-import-position


ap = argparse.ArgumentParser()
ap.add_argument("--hostname", default=None)
ap.add_argument("--port", default=None)
args = ap.parse_args()


def find_usable_tmpfile():
    # Generate a UUID to use as the temporary file, making sure to not overwrite an existing file
    while True:
        tmpfile = str(uuid.uuid4())
        filepath = make_splunkhome_path(["tmp", "saml_cli_auth", tmpfile])

        # Make sure the temporary
        if not os.path.exists(filepath):
            break

    return (tmpfile, filepath)


def get_authToken_filename():
    mgmtUri = urlparse(cli_common.getMgmtUri())

    return os.path.join(
        os.path.expanduser("~"),
        ".splunk",
        "authToken_%s_%s" % (socket.gethostname(), mgmtUri.port)
    )


def get_hostname():
    # args > config > email alert_action > serverName > socket.gethostname

    if args.hostname:
        return args.hostname

    saml_cli_auth_config = cli_common.getMergedConf("saml_cli_auth")
    base_url = saml_cli_auth_config.get("cli", {}).get("base_url", None)
    if base_url:
        return base_url

    alert_actions_config = cli_common.getMergedConf("alert_actions")
    alert_actions_hostname = alert_actions_config.get("email", {}).get("hostname", None)
    if alert_actions_hostname:
        return alert_actions_hostname

    server_config = cli_common.getMergedConf("server")
    serverName = server_config.get("general", {}).get("serverName", None)
    if serverName:
        return serverName

    return socket.gethostname()


def get_port(webUri):
    if args.port:
        return args.port
    return webUri.port


def get_saml_cli_auth_url(target_uuid):
    webUri = urlparse(cli_common.getWebUri())

    hostname = get_hostname()

    if hostname.startswith("http://") or hostname.startswith("https://"):
        webUri = urlparse(hostname)
        hostname = webUri.hostname

    port = get_port(webUri)

    # If the port doesn't match the scheme, add it to the URL
    ports = {"http": 80, "https": 443}
    if port is None or ports[webUri.scheme] == port:
        netloc = hostname
    else:
        netloc = "%s:%s" % (hostname, port)

    return urlunparse((
        webUri.scheme,
        netloc,
        "/en-US/custom/saml_cli_auth/saml/login",
        "",
        "uuid=%s" % target_uuid,
        ""
    ))


filename = get_authToken_filename()


# Create directories as necessary
try:
    os.makedirs(os.path.dirname(filename))
except OSError:
    pass

if os.path.exists(filename):
    with open(filename, "r") as f:
        content = f.read()
    xml = minidom.parseString(content)

    data = {"username": None, "sessionkey": None}
    for k in data:
        tags = xml.getElementsByTagName(k)
        if not tags:
            continue
        data[k] = tags[0].childNodes[0].nodeValue

    if data["username"] and data["sessionkey"]:
        authenticated = False
        try:
            _, content = splunk.rest.simpleRequest(
                "/services/authentication/current-context",
                sessionKey=data["sessionkey"],
                method="GET",
                raiseAllErrors=True,
                getargs={"output_mode": "json"}
            )
        except Exception as e:  # pylint: disable=broad-except
            authenticated = False
        else:
            content = json.loads(content)
            username = content["entry"][0]["content"]["username"]
            if username == data["username"]:
                print("Already authenticated as %s. If you need to reauthenticate, " \
                      "remove %s and try again." % (username, filename))

                sys.exit()


target, targetfn = find_usable_tmpfile()
url = get_saml_cli_auth_url(target)


print("Open the URL below in your browser. This script will automatically exit once you "
      "have logged in.")
print("")
print("%s%s" % (" " * 8, url))
print("")
sys.stdout.write("Waiting...")

try:
    while True:
        try:
            serverResponse, content = splunk.rest.simpleRequest(
                "/services/saml_cli_auth/retrieve",
                method="GET",
                getargs={"output_mode": "json", "uuid": target}
            )
        except splunk.ResourceNotFound:
            time.sleep(1)
            sys.stdout.write(".")
        else:
            break
except KeyboardInterrupt:
    print("")
    print("Cancelled!")
else:
    if serverResponse.status != 200:
        print("There was an error authenticating you. Output from Splunk is below")
        print("-" * 80)
        print(content)
    else:
        data = {}
        for entry in json.loads(content)["entry"]:
            data.update({entry["title"]: entry["content"]})

        output = "<auth>" \
                 "<username>{username}</username>" \
                 "<sessionkey>{sessionkey}</sessionkey>" \
                 "<cookie>{cookie}</cookie>" \
                 "</auth>".format(**data)

        with open(filename, "w") as f:
            f.write(output)

        print("")
        print("You are now authenticated as %s" % data["username"])
