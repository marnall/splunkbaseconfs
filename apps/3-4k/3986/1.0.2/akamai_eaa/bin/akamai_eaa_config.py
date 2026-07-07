#Encode BubblewrApp access url

import base64
import sys
import string

def encode_akamai_eaa_config():
    outf = open('./akamai_eaa_etl_config_en', 'w')
    print "Akamai EAA Url:"
    url_in = raw_input()
    outf.write(base64.b64encode(url_in)+"\n")
    outf.close()
    print "Changed url:"
    print url_in
#    w = sys.stdin.readline().strip()

encode_akamai_eaa_config()
