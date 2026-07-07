import re

from constants import IOC_NAME, IOC_VARIATIONS


class Validation:
    def validating_ioc(ioc, val):
        """
        Validates an Indicator of Compromise (IOC) against predefined regular expressions.
        """
        val = val.strip()
        ioc_type = ioc
        list_of_ioc = IOC_VARIATIONS
        ioc_names_list = IOC_NAME
        if "ip" in ioc_type.lower():
            ioc_type = "ip"
        elif "domain_and_url" in ioc_type.lower():
            ioc_type = "domain_and_url"
        elif "url" in ioc_type.lower():
            ioc_type = "url"
        elif "domain" in ioc_type.lower():
            ioc_type = "domain"
        elif "hash" in ioc_type.lower() or ioc_type.lower() in [
            "sha256",
            "sha1",
            "md5",
            "sha512",
        ]:
            ioc_type = "hash"
        elif "host" in ioc_type.lower():
            ioc_type = "domain"
        elif "email" in ioc_type.lower():
            ioc_type = "email"
        elif "phone" in ioc_type.lower():
            ioc_type = "phone"

        if ioc_type in ioc_names_list.keys():
            if ioc_type == "ip":
                ip_dict = ioc_names_list[ioc_type]
                for key, value in ip_dict.items():
                    regex = value
                    if re.fullmatch(regex, val):
                        ioc_name = key + "_regex"
                        return ioc_name

            elif ioc_type == "hash":
                hash_dict = ioc_names_list["hash"]
                for key, value in hash_dict.items():
                    regex = value
                    if re.fullmatch(regex, val):
                        ioc_name = key + "_regex"
                        return ioc_name
            elif ioc_type == "domain_and_url":
                regex_dict = ioc_names_list[ioc_type]
                for key, value in regex_dict.items():
                    regex = value
                    if re.fullmatch(regex, val):
                        ioc_name = key + "_regex"
                        return ioc_name

            else:
                regex = ioc_names_list[ioc_type]
                if re.fullmatch(regex, val):
                    ioc_name = ioc_type + "_regex"
                    return ioc_name

        elif ioc_type != "":
            for key, value in list_of_ioc.items():
                if ioc_type in value:
                    ioc = key
            regex = ioc_names_list[ioc_type]
            if re.fullmatch(regex, val):
                ioc_name = ioc_type + "_regex"
                return ioc_name

        else:
            ioc_name = None
            return ioc_name
