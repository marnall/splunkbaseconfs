import re
#CONSTANTS FILE
#base url of HYAS Insight.

BASE_URL = 'https://apps.hyas.com'
WHOIS_CURRENT_BASE_URL = 'https://api.hyas.com'


#endpoints

PASSIVE = '/api/ext/passivedns'
DYNAMIC = '/api/ext/dynamicdns'
PASSIVEHASH = '/api/ext/passivehash'
SINKHOLE = '/api/ext/sinkhole'
C2ATTRIBUTION = '/api/ext/c2attribution'
DEVICE = '/api/ext/device_geo'
SSL = '/api/ext/ssl_certificate'
WHOIS = '/api/ext/whois'
WHOIS_CURRENT = '/whois/v1'
SAMPLE_INFORMATION = '/api/ext/sample/information'
SAMPLE = '/api/ext/sample'
OS_INDICATOR = '/api/ext/os_indicators'

#Dummy Values

TYPE = "domain"
VALUE = "www.glowtey.com"

#Validators

IP_REG="^((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])\.){3}(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[1-9]?[0-9])$"
IPv6_REG = r'\b(?:(?:[0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:(?:(:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))\b'
EMAIL_REG="[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
DOMAIN_REG = re.compile(
    r'^(?:[a-zA-Z0-9]'  # First character of the domain
    r'(?:[a-zA-Z0-9-_]{0,61}[A-Za-z0-9])?\.)'  # Sub domain + hostname
    r'+[A-Za-z0-9][A-Za-z0-9-_]{0,61}'  # First 61 characters of the gTLD
    r'[A-Za-z]$'  # Last character of the gTLD
)
PHONE_REG="^\+?[1-9]\d{1,14}$"
SHA_REG="[A-Fa-f0-9]{64}"
URL_REG = "((http|https)://)(www.)?[a-zA-Z0-9@:%._\\+~#?&//=]{2,256}\\.[a-z]{2,6}\\b([-a-zA-Z0-9@:%._\\+~#?&//=]*)"
MD5_REG = r"(^[a-fA-F0-9]{32}$)"
SHA1_REG = r'\b[0-9a-fA-F]{40}\b'
SHA512_REG = r'\b[0-9a-fA-F]{128}\b'

# Different names of IOC

IOC_VARIATIONS =  {"ip":['ipv4', 'ip_address', 'ipaddress', 'IP Address', "IP"], "domain":['url', 'domain_name', 'Domain'], "email":['email_id','email_address', 'Email Address','Email'], "phone":['phone_number', 'phone_no', 'Phone Number', 'Phone'] ,"sha256":['SHA256']}

IOC_NAME = {"ip": {"ipv4":IP_REG, "ipv6": IPv6_REG}, "domain": DOMAIN_REG,
            "email": EMAIL_REG, "phone": PHONE_REG, "hash":{"sha256":SHA_REG, "md5":MD5_REG, "sha1": SHA1_REG,'sha512':SHA512_REG}}


# IOC's for different endpoints

PASSIVE_IOC = {'ipv4_regex':'ipv4','domain_regex':'domain'}
DYNAMIC_IOC = {'ipv4_regex':'ip','ipv6_regex':'ip','email_regex':'email', 'domain_regex':'domain'}
PASSIVEHASH_IOC = {'ipv4_regex':'ipv4', 'domain_regex':'domain'}
C2ATTRIBUTION_IOC = {'ipv4_regex':'ip','ipv6_regex':'ip','email_regex':'email',
                     'domain_regex':'domain','sha256_regex':"sha256"}
WHOIS_IOC = {'phone_regex':'phone','email_regex':'email','domain_regex':'domain'}
WHOIS_CURRENT_NAMES = {'domain_regex':'domain'}
SINKHOLE_IOC = {'ipv4_regex':'ipv4'}
SSL_IOC = {'ipv4_regex':'ip','ipv6_regex':'ip', 'sha1_regex': 'hash', 'domain_regex':'domain'}
DEVICE_IOC = {'ipv4_regex':'ipv4', 'ipv6_regex':'ipv6'}
SAMPLE_INFORMATION_IOC = {"md5_regex": "hash", "sha256_regex": "hash",
                      "sha1_regex": "hash", "sha512_regex": "hash"}
SAMPLE_IOC = {"md5_regex": "md5", 'domain_regex':'domain', 'ipv4_regex':'ipv4'}
OS_INDICATOR_IOC = {"md5_regex": "md5", "sha256_regex": "sha256",
                      "sha1_regex": "sha1", 'domain_regex':'domain', 'ipv4_regex':'ipv4'}