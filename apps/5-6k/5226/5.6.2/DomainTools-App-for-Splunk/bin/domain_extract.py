from __future__ import absolute_import
import os, sys
from settings import APP_ID
import pathlib

splunkhome = os.environ["SPLUNK_HOME"]

app_path = str(pathlib.Path(__file__).parents[1])
lib_path = os.path.join(app_path, "lib")
cache_path = os.path.join(app_path, "bin", "data")
sys.path.append(lib_path)
import tldextract
from dt_logger import DTLogger
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)
import dt_exception_messages

tldextract_cached = tldextract.TLDExtract(
    include_psl_private_domains=True,
    suffix_list_urls=(),
)


@Configuration(local=True)
class DomainExtractCommand(StreamingCommand):
    """This custom search command extracts the domain from a url.

    Inherits from the StreamingCommand custom search type. Override the `stream` method as the entrypoint to this script

    Attributes:
        field_in (str): Field to extract domains from
        field_out (str): Field to output domain in
        feature (str): Where this file was called from in the app

    Example:
        | makeresults | eval url="https://domaintools.com/apidocs" | dtdomainextract field_in=url field_out=domain
    """

    field_in = Option(
        doc="""
            **Syntax:** **field_in=***<in>*
            **Description:** Field to extract domains from""",
        require=True,
    )

    field_out = Option(
        doc="""
                **Syntax:** **field_out=***<out>*
                **Description:** Field to output domain in""",
        require=True,
    )

    include_subdomain = Option(
        doc="""
                    **Syntax:** **include_subdomain=***<include_subdomain>*
                    **Description:** Include subdomain field in results""",
        default=False,
        require=False,
    )

    debug = Option(
        doc="""
                        **Syntax:** **debug=***<debug>*
                        **Description:** Turn on debug logging in domaintools.log""",
        default=False,
        require=False,
    )

    feature = Option(
        doc="""
                **Syntax:** **feature=***<feature>*
                **Description:** Feature in the app where this was called""",
        default="adhoc",
        require=False,
    )

    def get_user(self):
        """get current logged in user"""
        return self.metadata.searchinfo.username

    def extract_domain(self, url):
        domain = ""
        tld_obj = tldextract_cached(url)

        if tld_obj.domain and tld_obj.suffix:
            domain = "{}.{}".format(tld_obj.domain, tld_obj.suffix)
        elif tld_obj.suffix and "." in tld_obj.suffix:
            domain = "{}".format(tld_obj.suffix)

        subdomain = tld_obj.subdomain

        return domain, subdomain

    def stream(self, records):
        """This is the entry point to a StreamingCommand subclass. You must override this method

        :param records: generator iterator of rows from previous command of SPL search
        :return: generator rows to pass on to next command of SPL search after transform
        """
        if self.debug:
            self.dt_log = DTLogger(
                "none", os.path.basename(__file__), self.get_user(), self.feature
            )
            self.dt_log.debug("starting domain_extract.py")

        for record in records:
            if self.field_in not in record:
                yield record
                continue

            url = record[self.field_in]
            try:
                if isinstance(url, list):
                    extracted_domains = []
                    for url_value in url:
                        extracted_domain, subdomain = self.extract_domain(url_value)
                        extracted_domains.append(extracted_domain)
                    record[self.field_out] = extracted_domains
                else:
                    extracted_domain, subdomain = self.extract_domain(url)
                    record[self.field_out] = extracted_domain

                if self.include_subdomain:
                    record["subdomain"] = subdomain

                yield record
            except Exception as e:
                if self.debug:
                    try:
                        self.dt_log.error(
                            "error extracting domain: {0}, exception type: {1}, exception message: {2} feature: {3}".format(
                                url[:500], type(e).__name__, e, self.feature
                            )
                        )
                    except Exception as e:
                        self.dt_log.error(
                            "unable to log url causing exception: {0}".format(e)
                        )

                if self.feature.find("Saved Search") == -1:
                    raise Exception(dt_exception_messages.generic.format(e))

        if self.debug:
            self.dt_log.debug("completed domain_extract.py")


dispatch(DomainExtractCommand, sys.argv, sys.stdin, sys.stdout, __name__)
