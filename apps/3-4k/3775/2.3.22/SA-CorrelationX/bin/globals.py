import splunk.entity
import ConfigParser

API_HOST = 'https://api.correlationx.com'
#API_HOST = 'http://api.correlationx.local'
#API_HOST = 'https://v3-api-correlationx.aspci.smartru.com'

def getProxies(settings):

    try:
        authString = settings.get("authString", None)
        if authString == None:
            return
        return getProxiesByAuthString(authString)
    except:
        return None

def getProxiesByAuthString(authString):

    try:

    	start = authString.find('<username>') + 10
    	stop = authString.find('</username>')
    	user = authString[start:stop]

    	start = authString.find('<authToken>') + 11
    	stop = authString.find('</authToken>')
    	authToken = authString[start:stop]

        config = ConfigParser.RawConfigParser()
        config.read('../local/proxy.conf')

        proxy_ip = config.get('corx', 'proxy_ip')
        proxy_port = config.get('corx', 'proxy_port')
        proxy_user = config.get('corx', 'proxy_user')
        proxy_password = ""

        try:
            password = splunk.entity.getEntity("storage/passwords", "proxy_password", namespace="SA-CorrelationX", owner=user, sessionKey=authToken)
            proxy_password = password["clear_password"]
        except:
			pass

        if proxy_ip is None or proxy_ip == '':
            return None
        elif proxy_user is None or proxy_user == '' or proxy_password is None or proxy_password == '':
            if proxy_port is None or proxy_port == '':
                return {
                    "https": "https://"+ proxy_ip + ":443",
                }
            else:
                return {
                    "https": "https://"+ proxy_ip + ":" + proxy_port,
                }
        else:
            if proxy_port is None or proxy_port == '':
                return {
                    "https": "https://"+ proxy_user + ":" + proxy_password + "@" + proxy_ip + ":443",
                }
            else:
                return {
                    "https": "https://"+ proxy_user + ":" + proxy_password + "@" + proxy_ip + ":" + proxy_port,
                }
    except:
        return None
