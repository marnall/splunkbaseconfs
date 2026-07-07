import re
from constants import IOC_VARIATIONS, IOC_NAME


def validating_ioc(ioc, val):
    ioc_type = ioc
    if "ip" in ioc_type.lower():
        ioc_type = "ip"
    elif "url" in ioc_type.lower():
        ioc_type = "domain"
    elif "domain" in ioc_type.lower():
        ioc_type = "domain"
    elif "hash" in ioc_type.lower() or "sha256" in ioc_type.lower():
        ioc_type = "sha256"
    elif "host" in ioc_type.lower():
        ioc_type = "domain"
    elif "email" in ioc_type.lower():
        ioc_type = "email"
    elif "phome" in ioc_type.lower():
        ioc_type = "phone"

    if ioc_type in IOC_NAME.keys():
        regex = IOC_NAME[ioc_type]
        if re.fullmatch(regex, val):
            ioc_name = ioc_type + "_regex"
            return ioc_name

    elif ioc_type:
        for key, value in IOC_VARIATIONS.items():
            if ioc_type in value:
                ioc_type = key
        regex = IOC_NAME[ioc_type]
        if re.fullmatch(regex, val):
            ioc_name = ioc_type + "_regex"
            return ioc_name
