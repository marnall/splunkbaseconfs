from __future__ import absolute_import
import splunk.Intersplunk
import os, sys, json
from settings import APP_ID

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(
    os.path.join(splunkhome, "etc", "apps", APP_ID, "lib")
)
sys.path.append(
    os.path.join(splunkhome, "etc", "slave-apps", APP_ID, "lib")
)
import tldextract
import xml.etree.ElementTree as ET
from dt_logger import DTLogger
import dt_exception_messages



# Splunk doesn't allow hidden files (files that start w a .) in app packages. Our `TLDExtract` lib has one
# of these files in it, but we have removed it. We bypass the `TLDExtract` lib from accessing that file by
# passing in the `KWARG`: `fallback_to_snapshot=False`. We need to ensure to do this anytime we call
# `TLDExtract`. The only place we do this, currently, is in `DomainTools/bin/domain_extract.py`.
#
# The tldextract we use has been customized to not fail on the error:
# ValueError: unichr() arg not in range(0x10000) (narrow Python build)
# If upgrading tldextract please make sure, to add in our extra code line 407 in lib/tldextract/tldextract.py.
cache_path = os.path.join(
    splunkhome,
    "etc",
    "apps",
    APP_ID,
    "default",
    "bin",
)

if not os.path.exists(cache_path):
    cache_path = os.path.join(
        splunkhome,
        "etc",
        "slave-apps",
        APP_ID,
        "default",
        "bin",
    )

tldextract_cached = tldextract.TLDExtract(cache_dir=cache_path)


def main(arguments, records, settings):
    try:
        auth = ET.fromstring(settings["authString"])
        username = auth.find("username").text
    except Exception as e:
        username = "unknown"

    output_events = []
    field_in = arguments.get("field_in", None)
    field_out = arguments.get("field_out", None)
    include_subdomain = arguments.get("include_subdomain", False)
    feature = arguments.get("feature", "adhoc")

    if not field_in:
        output_events = splunk.Intersplunk.generateErrorResults(
            "error: No field_in field specified"
        )
        splunk.Intersplunk.outputResults(output_events)
        return

    if not field_out:
        output_events = splunk.Intersplunk.generateErrorResults(
            "error: No field_out field specified"
        )
        splunk.Intersplunk.outputResults(output_events)
        return

    dt_log = DTLogger("none", os.path.basename(__file__), username, feature)
    dt_log.debug("starting domain_extract_scp1.py")

    for record in records:

        if field_in not in record:
            output_events.append(record)
            continue
        try:
            url = record[field_in]
            extracted_domain = ""
            tld_obj = tldextract_cached(url)
            if tld_obj.domain and tld_obj.suffix:
                extracted_domain = "{}.{}".format(tld_obj.domain, tld_obj.suffix)
            elif tld_obj.suffix and "." in tld_obj.suffix:
                extracted_domain = "{}".format(tld_obj.suffix)

            record[field_out] = extracted_domain

            if include_subdomain:
                record["subdomain"] = tld_obj.subdomain

            output_events.append(record)
        except Exception as e:
            dt_log.error(
                "error extracting domain: {0}, exception type: {1}, exception message: {2} feature: {3}".format(
                    url, type(e).__name__, e, feature
                )
            )
            if feature.find("Saved Search") == -1:
                raise Exception(dt_exception_messages.generic.format(e))

    dt_log.debug("completed domain_extract_scp1.py")
    return output_events

if __name__ == "__main__":
    args, kwargs = splunk.Intersplunk.getKeywordsAndOptions()
    (records, dummyresults, settings) = splunk.Intersplunk.getOrganizedResults()

    output_events = main(kwargs, records, settings)

    splunk.Intersplunk.outputResults(output_events)
