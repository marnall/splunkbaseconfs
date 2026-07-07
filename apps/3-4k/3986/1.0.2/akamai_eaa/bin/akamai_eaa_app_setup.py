#Encode Akamai Enterprise Access access keys

import base64
import string
import time

datef = "%Y-%m-%d %H:%M"

def encode_akamai_ea_keys():
    outf = open('./akamai_eaa_access_keys_en', 'w')
    api_in = raw_input('Akamai EAA Api Key: ')
    secret_in = raw_input('Akamai EAA Secret Key: ')
    outf.write(base64.b64encode(api_in)+"\n")
    outf.write(base64.b64encode(secret_in))
    outf.close()

encode_akamai_ea_keys()


def encode_splunk_config():
    outf = open('./splunk_akamai_eaa_config_en', 'w')
    user_in = raw_input('Splunk User: ')
    passwd_in = raw_input('Splunk Password: ')
    outf.write(base64.b64encode(user_in)+"\n")
    outf.write(base64.b64encode(passwd_in))
    outf.close()


#encode_splunk_config()

def save_start_time():
    try:
        outf = open('./akamai_eaa_etl_time.txt', 'w')
        date = raw_input('Start date time yyyy-mm-dd hh:mm like 2018-01-12 13:00: ')
        ts = long(time.mktime(time.strptime(date, datef)) * 1000)
        #print ts
        outf.write(date)
        outf.close()
    except Exception, e:
        print e
        save_start_time()
        
save_start_time()

