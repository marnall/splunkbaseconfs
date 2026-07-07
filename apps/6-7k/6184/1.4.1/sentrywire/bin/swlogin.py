import csv
import os
import time

from sentrywire.client import Sentrywire
import sys

if os.getenv("DEBUG"):
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
except ImportError as e:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
    
AUTHFOLDER= os.getenv("SPLUNK_HOME") + "/etc/apps/sentrywire/auth"
os.makedirs(AUTHFOLDER, exist_ok=True)
AUTHFILE= os.getenv("SPLUNK_HOME") + "/etc/apps/sentrywire/auth/auth.csv"

@Configuration()
class SentrywireLoginCommand(StreamingCommand):
    ip = Option(require=True, validate=validators.Match("ip", ".*"))
    username = Option(require=True, validate=validators.Match("username", ".*"))
    password = Option(require=True, validate=validators.Match("password", ".*"))

    def stream(self, events):
        outcome = storecreds(self._metadata.searchinfo.username, self.ip, self.username, self.password)
        yield {'_time': time.time(), 'event_no': 0, '_raw': outcome}


def storecreds(splunkUser, ip, username, password):
    """
    Store rest token for use with search funciton
    :param splunkUser: Currently logged in user as a string
    :param ip: IP address of Sentrywire unit as a string
    :param username: String
    :param password: String
    :return: String, error or success
    """
    try:
        # Create instance of a handler for our server
        if os.getenv("DEBUG"):
            sw = Sentrywire(ip, ssl_verify=False)
        else:
            sw = Sentrywire(ip)
        # Authenticate, as a user capable of performing a search, to the server
        token = sw.login(username, password)
    except Exception as e:
        return str(e)

    all_creds = []
    with open(AUTHFILE, 'r+') as csvfile:
        reader = csv.reader(csvfile)
        found = False
        for row in reader:
            try:
                # Wipe previous version file format
                if "pw" in row:
                    break
                if row == ["splunkuser", "ip", "token"] or len(row) == 0:
                    continue
                if row[0] == splunkUser and row[1] == ip:
                    found = True
                    row[2] = token
                all_creds.append(row)
            except IndexError:
                pass

        if not found:
            row = [splunkUser, ip, token]
            all_creds.append(row)

        csvfile.seek(0)
        writer = csv.writer(csvfile)
        writer.writerow(["splunkuser", "ip", "token"])
        writer.writerows(all_creds)
        csvfile.truncate()
    return "Username \"" + username + "\" accepted."


def getcreds(splunkUser, ip):
    with open(AUTHFILE) as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if not row:
                continue
            if row[0] == splunkUser and row[1] == ip:
                token = row[2]
                return token
    return None


if __name__ == "__main__":
    dispatch(SentrywireLoginCommand, sys.argv, sys.stdin, sys.stdout, __name__)
