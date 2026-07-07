import re
import sys
import urllib.error
import urllib.request


OUI_URL = "https://standards-oui.ieee.org"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Trailer/93.3.8652.5"


def main():
    req = urllib.request.Request(OUI_URL)
    req.add_header("User-agent", USER_AGENT)
    try:
        page = urllib.request.urlopen(req, timeout=15)
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"HTTP error {e.code} opening \"{OUI_URL}\"")
        exit(1)
    except urllib.error.URLError as e:
        sys.stderr.write(f"URL error with \"{OUI_URL}\": {e.reason}")
        exit(1)

    # parse OUI page
    oui_dict = {}
    for line in page:
        r = line.decode("utf-8").rstrip("\n\r ")
        if "(base 16)" in r:
            m = re.match("^([0-9a-fA-F]{6})\\s+\\(base\\s16\\)\\s+(.*)", r)
            if len(m.groups()) == 2:
                oui = m[1].lower()
                vendor = m[2]
                if oui in oui_dict:
                    sys.stderr.write(f"duplicate OUI {oui} ignored\n")
                else:
                    oui_dict[oui] = vendor

    # write OUI table
    sys.stdout.write("oui,vendor\n")
    for i in iter(sorted(oui_dict.items())):
        sys.stdout.write(f"{i[0]},\"{i[1]}\"\n")


if __name__ == '__main__':
    main()
