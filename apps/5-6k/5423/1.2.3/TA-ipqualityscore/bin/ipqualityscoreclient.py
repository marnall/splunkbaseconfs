# encoding = utf-8
from ipqualityscore_wrapper import IPQualityScoreWrapper


class IPQualityScoreClient(object):
    """
    Client for interacting with the IPQualityScore API to validate IPs, emails, URLs,
    phones, and check for dark web leaks.

    Methods:
        get_prefix(): Returns the prefix used for the API results.
        ip_detection_multithreaded(): Validates a list of IPs.
        email_validation_multithreaded(): Validates a list of emails.
        url_checker_multithreaded(): Checks a list of URLs.
        phone_validation_multithreaded(): Validates a list of phone numbers.
        dark_web_leak_multithreaded(): Checks for dark web leaks based on input.
    """

    def __init__(self, api_key, logger):
        self.logger = logger
        self.api_key = api_key
        self.base_url = "https://ipqualityscore.com/"
        self.ipqs_wrapper = IPQualityScoreWrapper(
            self.api_key, self.base_url, self.logger
        )

    def get_prefix(
        self,
    ):
        return "ipqualityscore"

    def ip_detection_multithreaded(
        self,
        ips,
        strictness=None,
        allow_public_access_points=None,
        fast=None,
        lighter_penalties=None,
        mobile=None,
        user_agent=None,
        user_language=None,
        transaction_strictness=None,
        ipv4_db_file = None,
        ipv6_db_file = None
    ):
        self.logger.info(
            "IPQualityscoreClient - Performing IP Validation on following: "
            + ",".join(ips)
        )
        return self.ipqs_wrapper.ip_detection_multithreaded(
            ips,
            strictness,
            allow_public_access_points,
            fast,
            lighter_penalties,
            mobile,
            user_agent,
            user_language,
            transaction_strictness,
            ipv4_db_file=ipv4_db_file,
            ipv6_db_file=ipv6_db_file
        )

    def email_validation_multithreaded(
        self,
        emails,
        fast=None,
        timeout=None,
        suggest_domain=None,
        strictness=None,
        abuse_strictness=None,
    ):
        self.logger.info(
            "IPQualityscoreClient - Performing Email Validation on following: "
            + ",".join(emails)
        )
        return self.ipqs_wrapper.email_validation_multithreaded(
            emails, fast, timeout, suggest_domain, strictness, abuse_strictness
        )

    def url_checker_multithreaded(self, urls, strictness=None, fast=None, timeout=None):
        self.logger.info(
            "IPQualityscoreClient - Performing URL Checking on following: "
            + ",".join(urls)
        )
        return self.ipqs_wrapper.url_checker_multithreaded(
            urls, strictness, fast, timeout
        )

    def phone_validation_multithreaded(
        self,
        phones,
        country=None,
        strictness=None,
        enhanced_line_check=None,
        enhanced_name_check=None,
    ):
        self.logger.info(
            "IPQualityscoreClient - Performing Phone Validation on following: "
            + ",".join(phones)
        )
        return self.ipqs_wrapper.phone_validation_multithreaded(
            phones, country, strictness, enhanced_line_check, enhanced_name_check
        )

    def dark_web_leak_multithreaded(self, inputs, input_type):
        self.logger.info(
            "IPQualityscoreClient - Performing Dark Web Leak on following: "
            + ",".join(inputs)
        )
        return self.ipqs_wrapper.dark_web_leak_multithreaded(inputs, input_type)
