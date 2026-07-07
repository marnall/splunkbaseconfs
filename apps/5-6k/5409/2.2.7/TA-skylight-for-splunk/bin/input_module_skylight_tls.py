# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import json

TLS_VERSION = {
    48: 'SSL 3.0',
    49: 'TLS 1.1',
    50: 'TLS 1.2',
    51: 'TLS 1.3'
}

KEYTYPES = {
    0: 'RSA',
    1: 'EC'
}

cipher_id = {
0: 'null with null null',
1: 'RSA with null MD5',
2: 'RSA with null SHA',
3: 'RSA export with RC4 40 MD5',
4: 'RSA with RC4 128 MD5',
5: 'RSA with RC4 128 SHA',
6: 'RSA export with RC2 CBC 40 MD5',
7: 'RSA with IDEA CBC SHA',
8: 'RSA export with DES40 CBC SHA',
9: 'RSA with DES CBC SHA',
10: 'RSA with 3DES EDE CBC SHA',
11: 'DH DSS export with DES40 CBC SHA',
12: 'DH DSS with DES CBC SHA',
13: 'DH DSS with 3DES EDE CBC SHA',
14: 'DH RSA export with DES40 CBC SHA',
15: 'DH RSA with DES CBC SHA',
16: 'DH RSA with 3DES EDE CBC SHA',
17: 'DHE DSS export with DES40 CBC SHA',
18: 'DHE DSS with DES CBC SHA',
19: 'DHE DSS with 3DES EDE CBC SHA',
20: 'DHE RSA export with DES40 CBC SHA',
21: 'DHE RSA with DES CBC SHA',
22: 'DHE RSA with 3DES EDE CBC SHA',
23: 'DH anon export with RC4 40 MD5',
24: 'DH anon with RC4 128 MD5',
25: 'DH anon export with DES40 CBC SHA',
26: 'DH anon with DES CBC SHA',
27: 'DH anon with 3DES EDE CBC SHA',
49180: 'SRP SHA DSS with 3DES EDE CBC SHA',
49181: 'SRP SHA with AES 128 CBC SHA',
30: 'KRB5 with DES CBC SHA',
31: 'KRB5 with 3DES EDE CBC SHA',
32: 'KRB5 with RC4 128 SHA',
33: 'KRB5 with IDEA CBC SHA',
34: 'KRB5 with DES CBC MD5',
35: 'KRB5 with 3DES EDE CBC MD5',
36: 'KRB5 with RC4 128 MD5',
37: 'KRB5 with IDEA CBC MD5',
38: 'KRB5 export with DES CBC 40 SHA',
39: 'KRB5 export with RC2 CBC 40 SHA',
40: 'KRB5 export with RC4 40 SHA',
41: 'KRB5 export with DES CBC 40 MD5',
42: 'KRB5 export with RC2 CBC 40 MD5',
43: 'KRB5 export with RC4 40 MD5',
44: 'PSK with null SHA',
45: 'DHE PSK with null SHA',
46: 'RSA PSK with null SHA',
47: 'RSA with AES 128 CBC SHA',
48: 'DH DSS with AES 128 CBC SHA',
49: 'DH RSA with AES 128 CBC SHA',
50: 'DHE DSS with AES 128 CBC SHA',
51: 'DHE RSA with AES 128 CBC SHA',
52: 'DH anon with AES 128 CBC SHA',
53: 'RSA with AES 256 CBC SHA',
54: 'DH DSS with AES 256 CBC SHA',
55: 'DH RSA with AES 256 CBC SHA',
56: 'DHE DSS with AES 256 CBC SHA',
57: 'DHE RSA with AES 256 CBC SHA',
58: 'DH anon with AES 256 CBC SHA',
59: 'RSA with null SHA256',
60: 'RSA with AES 128 CBC SHA256',
61: 'RSA with AES 256 CBC SHA256',
62: 'DH DSS with AES 128 CBC SHA256',
63: 'DH RSA with AES 128 CBC SHA256',
64: 'DHE DSS with AES 128 CBC SHA256',
65: 'RSA with CAMELLIA 128 CBC SHA',
66: 'DH DSS with CAMELLIA 128 CBC SHA',
67: 'DH RSA with CAMELLIA 128 CBC SHA',
68: 'DHE DSS with CAMELLIA 128 CBC SHA',
69: 'DHE RSA with CAMELLIA 128 CBC SHA',
70: 'DH anon with CAMELLIA 128 CBC SHA',
49223: 'DH anon with ARIA 256 CBC SHA384',
49224: 'ECDHE ECDSA with ARIA 128 CBC SHA256',
73: 'ECDH ECDSA with DES CBC SHA',
49226: 'ECDH ECDSA with ARIA 128 CBC SHA256',
49227: 'ECDH ECDSA with ARIA 256 CBC SHA384',
49228: 'ECDHE RSA with ARIA 128 CBC SHA256',
49229: 'ECDHE RSA with ARIA 256 CBC SHA384',
49230: 'ECDH RSA with ARIA 128 CBC SHA256',
49165: 'ECDH RSA with 3DES EDE CBC SHA',
49232: 'RSA with ARIA 128 GCM SHA256',
49233: 'RSA with ARIA 256 GCM SHA384',
49234: 'DHE RSA with ARIA 128 GCM SHA256',
49235: 'DHE RSA with ARIA 256 GCM SHA384',
49236: 'DH RSA with ARIA 128 GCM SHA256',
49166: 'ECDH RSA with AES 128 CBC SHA',
49238: 'DHE DSS with ARIA 128 GCM SHA256',
49239: 'DHE DSS with ARIA 256 GCM SHA384',
49240: 'DH DSS with ARIA 128 GCM SHA256',
49241: 'DH DSS with ARIA 256 GCM SHA384',
49242: 'DH anon with ARIA 128 GCM SHA256',
49167: 'ECDH RSA with AES 256 CBC SHA',
49244: 'ECDHE ECDSA with ARIA 128 GCM SHA256',
49245: 'ECDHE ECDSA with ARIA 256 GCM SHA384',
49246: 'ECDH ECDSA with ARIA 128 GCM SHA256',
49247: 'ECDH ECDSA with ARIA 256 GCM SHA384',
96: 'RSA export1024 with RC4 56 MD5',
97: 'RSA export1024 with RC2 CBC 56 MD5',
98: 'RSA export1024 with DES CBC SHA',
99: 'DHE DSS export1024 with DES CBC SHA',
100: 'RSA export1024 with RC4 56 SHA',
101: 'DHE DSS export1024 with RC4 56 SHA',
102: 'DHE DSS with RC4 128 SHA',
103: 'DHE RSA with AES 128 CBC SHA256',
104: 'DH DSS with AES 256 CBC SHA256',
105: 'DH RSA with AES 256 CBC SHA256',
106: 'DHE DSS with AES 256 CBC SHA256',
107: 'DHE RSA with AES 256 CBC SHA256',
108: 'DH anon with AES 128 CBC SHA256',
109: 'DH anon with AES 256 CBC SHA256',
49262: 'RSA PSK with ARIA 128 GCM SHA256',
49263: 'RSA PSK with ARIA 256 GCM SHA384',
49264: 'ECDHE PSK with ARIA 128 CBC SHA256',
49265: 'ECDHE PSK with ARIA 256 CBC SHA384',
49266: 'ECDHE ECDSA with CAMELLIA 128 CBC SHA256',
49171: 'ECDHE RSA with AES 128 CBC SHA',
49268: 'ECDH ECDSA with CAMELLIA 128 CBC SHA256',
49269: 'ECDH ECDSA with CAMELLIA 256 CBC SHA384',
49270: 'ECDHE RSA with CAMELLIA 128 CBC SHA256',
49271: 'ECDHE RSA with CAMELLIA 256 CBC SHA384',
49272: 'ECDH RSA with CAMELLIA 128 CBC SHA256',
49172: 'ECDHE RSA with AES 256 CBC SHA',
49274: 'RSA with CAMELLIA 128 GCM SHA256',
49275: 'RSA with CAMELLIA 256 GCM SHA384',
49276: 'DHE RSA with CAMELLIA 128 GCM SHA256',
49277: 'DHE RSA with CAMELLIA 256 GCM SHA384',
49278: 'DH RSA with CAMELLIA 128 GCM SHA256',
49173: 'ECDH anon with null SHA',
128: 'GOSTR341094 with 28147 CNT IMIT',
129: 'GOSTR341001 with 28147 CNT IMIT',
130: 'GOSTR341094 with null GOSTR3411',
131: 'GOSTR341001 with null GOSTR3411',
132: 'RSA with CAMELLIA 256 CBC SHA',
133: 'DH DSS with CAMELLIA 256 CBC SHA',
134: 'DH RSA with CAMELLIA 256 CBC SHA',
135: 'DHE DSS with CAMELLIA 256 CBC SHA',
136: 'DHE RSA with CAMELLIA 256 CBC SHA',
137: 'DH anon with CAMELLIA 256 CBC SHA',
138: 'PSK with RC4 128 SHA',
139: 'PSK with 3DES EDE CBC SHA',
140: 'PSK with AES 128 CBC SHA',
141: 'PSK with AES 256 CBC SHA',
142: 'DHE PSK with RC4 128 SHA',
143: 'DHE PSK with 3DES EDE CBC SHA',
144: 'DHE PSK with AES 128 CBC SHA',
145: 'DHE PSK with AES 256 CBC SHA',
146: 'RSA PSK with RC4 128 SHA',
147: 'RSA PSK with 3DES EDE CBC SHA',
148: 'RSA PSK with AES 128 CBC SHA',
149: 'RSA PSK with AES 256 CBC SHA',
150: 'RSA with seed CBC SHA',
151: 'DH DSS with seed CBC SHA',
152: 'DH RSA with seed CBC SHA',
153: 'DHE DSS with seed CBC SHA',
154: 'DHE RSA with seed CBC SHA',
155: 'DH anon with seed CBC SHA',
156: 'RSA with AES 128 GCM SHA256',
157: 'RSA with AES 256 GCM SHA384',
158: 'DHE RSA with AES 128 GCM SHA256',
159: 'DHE RSA with AES 256 GCM SHA384',
160: 'DH RSA with AES 128 GCM SHA256',
161: 'DH RSA with AES',
256: 'GCM SHA384',
162: 'DHE DSS with AES 128 GCM SHA256',
163: 'DHE DSS with AES 256 GCM SHA384',
164: 'DH DSS with AES 128 GCM SHA256',
165: 'DH DSS with AES 256 GCM SHA384',
166: 'DH anon with AES 128 GCM SHA256',
167: 'DH anon with AES 256 GCM SHA384',
168: 'PSK with AES 128 GCM SHA256',
169: 'PSK with AES 256 GCM SHA384',
170: 'DHE PSK with AES 128 GCM SHA256',
171: 'DHE PSK with AES 256 GCM SHA384',
172: 'RSA PSK with AES 128 GCM SHA256',
173: 'RSA PSK with AES 256 GCM SHA384',
174: 'PSK with AES 128 CBC SHA256',
175: 'PSK with AES 256 CBC SHA384',
176: 'PSK with null SHA256',
177: 'PSK with null SHA384',
178: 'DHE PSK with AES 128 CBC SHA256',
179: 'DHE PSK with AES 256 CBC SHA384',
180: 'DHE PSK with null SHA256',
181: 'DHE PSK with null SHA384',
182: 'RSA PSK with AES 128 CBC SHA256',
183: 'RSA PSK with AES 256 CBC SHA384',
184: 'RSA PSK with null SHA256',
185: 'RSA PSK with null SHA384',
186: 'RSA with CAMELLIA 128 CBC SHA256',
187: 'DH DSS with CAMELLIA 128 CBC SHA256',
188: 'DH RSA with CAMELLIA 128 CBC SHA256',
189: 'DHE DSS with CAMELLIA 128 CBC SHA256',
190: 'DHE RSA with CAMELLIA 128 CBC SHA256',
191: 'DH anon with CAMELLIA 128 CBC SHA256',
192: 'RSA with CAMELLIA 256 CBC SHA256',
193: 'DH DSS with CAMELLIA 256 CBC SHA256',
194: 'DH RSA with CAMELLIA 256 CBC SHA256',
195: 'DHE DSS with CAMELLIA 256 CBC SHA256',
196: 'DHE RSA with CAMELLIA 256 CBC SHA256',
197: 'DH anon with CAMELLIA 256 CBC SHA256',
49185: 'SRP SHA RSA with AES 256 CBC SHA',
49186: 'SRP SHA DSS with AES 256 CBC SHA',
49187: 'ECDHE ECDSA with AES 128 CBC SHA256',
49176: 'ECDH anon with AES 128 CBC SHA',
49188: 'ECDHE ECDSA with AES 256 CBC SHA384',
49170: 'ECDHE RSA with 3DES EDE CBC SHA',
49189: 'ECDH ECDSA with AES 128 CBC SHA256',
49190: 'ECDH ECDSA with AES 256 CBC SHA384',
49191: 'ECDHE RSA with AES 128 CBC SHA256',
49192: 'ECDHE RSA with AES 256 CBC SHA384',
49177: 'ECDH anon with AES 256 CBC SHA',
49193: 'ECDH RSA with AES 128 CBC SHA256',
49194: 'ECDH RSA with AES 256 CBC SHA384',
255: 'empty renegotiation info SCSV',
49195: 'ECDHE ECDSA with AES 128 GCM SHA256',
49196: 'ECDHE ECDSA with AES 256 GCM SHA384',
49197: 'ECDH ECDSA with AES 128 GCM SHA256',
49178: 'SRP SHA with 3DES EDE CBC SHA',
49198: 'ECDH ECDSA with AES 256 GCM SHA384',
49199: 'ECDHE RSA with AES 128 GCM SHA256',
49200: 'ECDHE RSA with AES 256 GCM SHA384',
49201: 'ECDH RSA with AES 128 GCM SHA256',
49202: 'ECDH RSA with AES 256 GCM SHA384',
49179: 'SRP SHA RSA with 3DES EDE CBC SHA',
49203: 'ECDHE PSK with RC4 128 SHA',
49204: 'ECDHE PSK with 3DES EDE CBC SHA',
49205: 'ECDHE PSK with AES 128 CBC SHA',
49206: 'ECDHE PSK with AES 256 CBC SHA',
49207: 'ECDHE PSK with AES 128 CBC SHA256',
49208: 'ECDHE PSK with AES 256 CBC SHA384',
49209: 'ECDHE PSK with null SHA',
49169: 'ECDHE RSA with RC4 128 SHA',
49210: 'ECDHE PSK with null SHA256',
49211: 'ECDHE PSK with null SHA384',
49212: 'RSA with ARIA 128 CBC SHA256',
49213: 'RSA with ARIA 256 CBC SHA384',
49214: 'DH DSS with ARIA 128 CBC SHA256',
49215: 'DH DSS with ARIA 256 CBC SHA384',
49216: 'DH RSA with ARIA 128 CBC SHA256',
49217: 'DH RSA with ARIA 256 CBC SHA384',
49182: 'SRP SHA RSA with AES 128 CBC SHA',
49218: 'DHE DSS with ARIA 128 CBC SHA256',
49219: 'DHE DSS with ARIA 256 CBC SHA384',
49220: 'DHE RSA with ARIA 128 CBC SHA256',
58389: 'ECDHE ECDSA with SALSA20 SHA1',
49221: 'DHE RSA with ARIA 256 CBC SHA384',
49222: 'DH anon with ARIA 128 CBC SHA256',
49183: 'SRP SHA DSS with AES 128 CBC SHA',
49225: 'ECDHE ECDSA with ARIA 256 CBC SHA384',
49184: 'SRP SHA with AES 256 CBC SHA',
49231: 'ECDH RSA with ARIA 256 CBC SHA384',
49237: 'DH RSA with ARIA 256 GCM SHA384',
49243: 'DH anon with ARIA 256 GCM SHA384',
49248: 'ECDHE RSA with ARIA 128 GCM SHA256',
49249: 'ECDHE RSA with ARIA 256 GCM SHA384',
49250: 'ECDH RSA with ARIA 128 GCM SHA256',
58395: 'RSA PSK with SALSA20 SHA1',
49251: 'ECDH RSA with ARIA 256 GCM SHA384',
49252: 'PSK with ARIA 128 CBC SHA256',
49253: 'PSK with ARIA 256 CBC SHA384',
49254: 'DHE PSK with ARIA 128 CBC SHA256',
49255: 'DHE PSK with ARIA 256 CBC SHA384',
49256: 'RSA PSK with ARIA 128 CBC SHA256',
49257: 'RSA PSK with ARIA 256 CBC SHA384',
49258: 'PSK with ARIA 128 GCM SHA256',
49259: 'PSK with ARIA 256 GCM SHA384',
49260: 'DHE PSK with ARIA 128 GCM SHA256',
49261: 'DHE PSK with ARIA 256 GCM SHA384',
49267: 'ECDHE ECDSA with CAMELLIA 256 CBC SHA384',
49273: 'ECDH RSA with CAMELLIA 256 CBC SHA384',
49279: 'DH RSA with CAMELLIA 256 GCM SHA384',
4865: 'AES 128 GCM SHA256',
4866: 'AES 256 GCM SHA384',
4867: 'CHACHA20 POLY1305 SHA256',
4868: 'AES 128 CCM SHA256',
4869: 'AES 128 CCM 8 SHA256',
49281: 'DHE DSS with CAMELLIA 256 GCM SHA384',
49282: 'DH DSS with CAMELLIA 128 GCM SHA256',
49283: 'DH DSS with CAMELLIA 256 GCM SHA384',
49284: 'DH anon with CAMELLIA',
128: 'GCM SHA256',
49285: 'DH anon with CAMELLIA 256 GCM SHA384',
49286: 'ECDHE ECDSA with CAMELLIA 128 GCM SHA256',
49287: 'ECDHE ECDSA with CAMELLIA 256 GCM SHA384',
49288: 'ECDH ECDSA with CAMELLIA 128 GCM SHA256',
49174: 'ECDH anon with RC4 128 SHA',
49289: 'ECDH ECDSA with CAMELLIA 256 GCM SHA384',
49290: 'ECDHE RSA with CAMELLIA 128 GCM SHA256',
49291: 'ECDHE RSA with CAMELLIA 256 GCM SHA384',
49292: 'ECDH RSA with CAMELLIA 128 GCM SHA256',
49293: 'ECDH RSA with CAMELLIA 256 GCM SHA384',
49294: 'PSK with CAMELLIA 128 GCM SHA256',
49295: 'PSK with CAMELLIA 256 GCM SHA384',
49296: 'DHE PSK with CAMELLIA 128 GCM SHA256',
49297: 'DHE PSK with CAMELLIA 256 GCM SHA384',
49298: 'RSA PSK with CAMELLIA 128 GCM SHA256',
49299: 'RSA PSK with CAMELLIA 256 GCM SHA384',
49300: 'PSK with CAMELLIA 128 CBC SHA256',
49301: 'PSK with CAMELLIA 256 CBC SHA384',
49302: 'DHE PSK with CAMELLIA 128 CBC SHA256',
49303: 'DHE PSK with CAMELLIA 256 CBC SHA384',
49304: 'RSA PSK with CAMELLIA 128 CBC SHA256',
49305: 'RSA PSK with CAMELLIA 256 CBC SHA384',
49306: 'ECDHE PSK with CAMELLIA 128 CBC SHA256',
49307: 'ECDHE PSK with CAMELLIA 256 CBC SHA384',
49308: 'RSA with AES 128 CCM',
49309: 'RSA with AES 256 CCM',
49310: 'DHE RSA with AES 128 CCM',
49311: 'DHE RSA with AES 256 CCM',
49312: 'RSA with AES 128 CCM 8',
49313: 'RSA with AES 256 CCM 8',
49175: 'ECDH anon with 3DES EDE CBC SHA',
49314: 'DHE RSA with AES 128 CCM 8',
49315: 'DHE RSA with AES 256 CCM 8',
49316: 'PSK with AES 128 CCM',
49317: 'PSK with AES 256 CCM',
49318: 'DHE PSK with AES 128 CCM',
49319: 'DHE PSK with AES 256 CCM',
49320: 'PSK with AES 128 CCM 8',
49321: 'PSK with AES 256 CCM 8',
49322: 'PSK DHE with AES 128 CCM 8',
49323: 'PSK DHE with AES 256 CCM 8',
49324: 'ECDHE ECDSA with AES 128 CCM',
49325: 'ECDHE ECDSA with AES 256 CCM',
58384: 'RSA with ESTREAM SALSA20 SHA1',
58385: 'RSA with SALSA20 SHA1',
58386: 'ECDHE RSA with ESTREAM SALSA20 SHA1',
58387: 'ECDHE RSA with SALSA20 SHA1',
58388: 'ECDHE ECDSA with ESTREAM SALSA20 SHA1',
49326: 'ECDHE ECDSA with AES 128 CCM 8',
58390: 'PSK with ESTREAM SALSA20 SHA1',
58391: 'PSK with SALSA20 SHA1',
58392: 'ECDHE PSK with ESTREAM SALSA20 SHA1',
58393: 'ECDHE PSK with SALSA20 SHA1',
58394: 'RSA PSK with ESTREAM SALSA20 SHA1',
49327: 'ECDHE ECDSA with AES 256 CCM 8',
58396: 'DHE PSK with ESTREAM SALSA20 SHA1',
58397: 'DHE PSK with SALSA20 SHA1',
58398: 'DHE RSA with ESTREAM SALSA20 SHA1',
58399: 'DHE RSA with SALSA20 SHA1',
52392: 'ECDHE RSA with CHACHA20 POLY1305 SHA256',
52393: 'ECDHE ECDSA with CHACHA20 POLY1305 SHA256',
52394: 'DHE RSA with CHACHA20 POLY1305 SHA256',
52395: 'PSK with CHACHA20 POLY1305 SHA256',
52396: 'ECDHE PSK with CHACHA20 POLY1305 SHA256',
52397: 'DHE PSK with CHACHA20 POLY1305 SHA256',
52398: 'RSA PSK with CHACHA20 POLY1305 SHA256',
49280: 'DHE DSS with CAMELLIA 128 GCM SHA256',
49407: 'ECJPAKE with AES 128 CCM 8',
22016: 'fallback SCSV',
49153: 'ECDH ECDSA with null SHA',
49154: 'ECDH ECDSA with RC4 128 SHA',
49155: 'ECDH ECDSA with 3DES EDE CBC SHA',
49156: 'ECDH ECDSA with AES 128 CBC SHA',
49157: 'ECDH ECDSA with AES 256 CBC SHA',
53249: 'ECDHE PSK with AES 128 GCM SHA256',
49158: 'ECDHE ECDSA with null SHA',
53250: 'ECDHE PSK with AES 256 GCM SHA384',
49159: 'ECDHE ECDSA with RC4 128 SHA',
53251: 'ECDHE PSK with AES 128 CCM 8 SHA256',
49160: 'ECDHE ECDSA with 3DES EDE CBC SHA',
49161: 'ECDHE ECDSA with AES 128 CBC SHA',
53253: 'ECDHE PSK with AES 128 CCM SHA256',
49162: 'ECDHE ECDSA with AES 256 CBC SHA',
49163: 'ECDH RSA with null SHA',
49164: 'ECDH RSA with RC4 128 SHA',
49168: 'ECDHE RSA with null SHA'
}

input_name = "tls"
def checkExceptions(host, application, server_port):
    json_path = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','exceptions.json')
    with open(json_path, "r") as f:
        json_data = json.loads(f.read())['filter']

        if len(json_data) > 0:
            for captures in json_data:
                if captures['capture'] == host:
                    for inputs in captures['inputs']:
                        if inputs['name'] == input_name:
                            capture_filter = inputs['exceptions']
                            if len(capture_filter) > 0:
                                for app in capture_filter:
                                    try:
                                        if int(app) == int(server_port):
                                            return False
                                    except:
                                        if str(app) == str(application):
                                            return False
                            else:
                                return True
        else:
            return True
    return True

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    def get_api_version(ip, api_key):
        import re

        headers = {'PVX-Authorization': api_key}
        response = helper.send_http_request('https://{}/api/get-api-version'.format(ip), 'GET', headers=headers, verify=False, timeout=60, use_proxy=True)
        version = response.json()["result"]["version"]

        return float(re.match("...", version).group(0))

    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    pvx_address = helper.get_global_setting("ip_address")
    verify = helper.get_arg('verify')

    if pvx_address == "none":
        return None

    pvx_api_key = ""
    try:
        cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
        with open(cwd, 'r') as file:
            pvx_api_key = file.read().splitlines()[0]
    except:
        return None

    if verify == 'false':
        verify = False
    elif verify == 'true':
        verify = True
    
    api_version = get_api_version(pvx_address, pvx_api_key)
    if api_version == 0.7:
        url = 'https://{}/api/query?expr=client.traffic, server.traffic, server.expiration, alert_types, client.ja3, server.ja3, begin, end from tls by time(), server.ip, client.ip, server.port, client.port, cipher, cipher.is_weak, server.common_name, tls.version, tls.version.is_weak, protostack, application.name, layer, server.key.type, server.signature, server_name, capture.id, capture.hostname, uuid, domain.primary SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    elif api_version >= 0.5:
        url = 'https://{}/api/query?expr=client.traffic, server.traffic, server.expiration, alert_types, client.ja3, server.ja3 from tls by time(), server.ip, client.ip, server.port, client.port, cipher, cipher.is_weak, server.common_name, tls.version, tls.version.is_weak, protostack, application.name, layer, server.key.type, server.signature, server_name, capture.id, capture.hostname, uuid, domain.primary, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
    else:
        url = 'https://{}/api/query?expr=client.traffic, server.traffic, server.expiration, alert_types from tls by time(), server.ip, client.ip, server.port, client.port, cipher, cipher.is_weak, server.common_name, tls.version, tls.version.is_weak, protostack, application, layer, server.key.type, server.signature, server_name, capture.id, capture.hostname, uuid, begin, end SINCE @now-{} UNTIL @now-{}'.format(pvx_address, 420, 360)
        
    headers = {'PVX-Authorization': pvx_api_key}
    method = 'GET'
    timeout = 45.0
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=False,
                                        timeout=timeout, use_proxy=True)
    r_json = response.json()

    if 'data' in r_json['result']:
        for res in r_json['result']['data']:
            timestamp = int(float(res['key'][0]['value']))
            dest_ip = res['key'][1].get('value')
            src_ip = res['key'][2].get('value')
            dest_port = res['key'][3].get('value')
            src_port = res['key'][4].get('value')
            cipher = res['key'][5].get('value')
            cipher_is_weak = res['key'][6].get('value')
            ssl_subject_common_name = res['key'][7].get('value')
            tls_version = TLS_VERSION.get(int(res['key'][8].get('value', -1)))
            tls_version_is_weak = res['key'][9].get('value')
            app = res['key'][11].get('value', -1)
            layer = res['key'][12].get('value')
            ssl_publickey_algorithm = KEYTYPES.get(int(res['key'][13].get('value', -1)))
            ssl_signature_algorithm = res['key'][14].get('value')
            cipher_name = cipher_id.get(int(res['key'][5].get('value', -1)))
            bytes_out = int(res['values'][0].get('value'))
            bytes_in = int(res['values'][1].get('value'))
            bytes_total = bytes_out + bytes_in
            ssl_end_time = res['values'][2].get('value')
            alert_types = res['values'][3].get('value')
            client_ja3 = res['values'][4].get('value')
            server_ja3 = res['values'][5].get('value')
            server_name = res['key'][15].get('value')
            capture = res['key'][16].get('value')
            capture_hostname = res['key'][17].get('value')
            uuid = res['key'][18].get('value')

            data = {
                'action': 'allowed',
                'time': timestamp,
                'dest_ip': dest_ip,
                'src_ip': src_ip,
                'dest_port': dest_port,
                'src_port': src_port,
                'cipher': cipher,
                'cipher_name': cipher_name,
                'cipher_is_weak': cipher_is_weak,
                'ssl_subject_common_name': ssl_subject_common_name,
                'tls_version': tls_version,
                'tls_version_is_weak': tls_version_is_weak,
                'client_ja3': client_ja3,
                'server_ja3': server_ja3,
                'app': app,
                'layer': layer,
                'ssl_publickey_algorithm': ssl_publickey_algorithm,
                'ssl_signature_algorithm': ssl_signature_algorithm,
                'bytes': bytes_total,
                'bytes_out': bytes_out,
                'bytes_in': bytes_in,
                'ssl_end_time': int(float(ssl_end_time)) if ssl_end_time else None,
                'alert_types': alert_types if alert_types else None,
                'sni': server_name,
                'capture': capture,
                'uuid' : uuid
            }

            if api_version == 0.5 or api_version == 0.6:
                data['domain_primary'] = res['key'][19].get('value')
                data['begin'] = res['key'][20].get('value')
                data['end'] = res['key'][21].get('value')
            elif api_version == 0.5:
                data['domain_primary'] = res['key'][19].get('value')
                data['begin'] = res['values'][6].get('value')
                data['end'] = res['values'][7].get('value')

            if checkExceptions(capture_hostname, app, dest_port):
                event = helper.new_event(time=timestamp,
                                data=json.dumps(data),
                                index=helper.get_output_index(),
                                source=helper.get_input_type(),
                                sourcetype=helper.get_sourcetype(),
                                done=True,
                                unbroken=True)
                ew.write_event(event)
