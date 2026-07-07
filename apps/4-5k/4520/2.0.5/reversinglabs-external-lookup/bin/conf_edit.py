import sys
import os


def get_lookup_file():
    location_string = os.path.join(os.path.dirname(os.getcwd()), "lookups", "ticloud_configuration.csv")
    return location_string


def format_url(host):
    """Returns a formatted host URL including the protocol statement.
        :param host: URL string
        :type host: str
        :returns: formatted URL string
        :rtype: str
    """
    if host.startswith("http://"):
        host = "https://{host}".format(host=host[len("http://"):])
    elif host.startswith("https://"):
        pass
    else:
        host = "https://{host}".format(host=host)
    return host


def main():
    address = format_url(str(sys.argv[1]))
    username = str(sys.argv[2])
    password = str(sys.argv[3])
    http_proxy_address = str(sys.argv[4])
    http_proxy_port = str(sys.argv[5])
    http_proxy_username = str(sys.argv[6])
    http_proxy_password = str(sys.argv[7])
    https_proxy_address = str(sys.argv[8])
    https_proxy_port = str(sys.argv[9])
    https_proxy_username = str(sys.argv[10])
    https_proxy_password = str(sys.argv[11])

    with open(get_lookup_file(), "w") as lookup:
        lookup.write(
            "TitaniumCloudAddress,Username,Password,"
            + "HttpProxyAddress,HttpProxyPort,HttpProxyUsername,HttpProxyPassword,"
            + "HttpsProxyAddress,HttpsProxyPort,HttpsProxyUsername,HttpsProxyPassword\n"
            + address + "," + username + "," + password + ","
            + http_proxy_address + "," + http_proxy_port + "," + http_proxy_username + "," + http_proxy_password + ","
            + https_proxy_address + "," + https_proxy_port + "," + https_proxy_username + "," + https_proxy_password
        )
        lookup.close()


if __name__ == "__main__":
    main()
