import splunk.Intersplunk
import tldextract
import os
cache_path = os.path.join(os.environ.get("SPLUNK_HOME"), "etc", "apps", "TA-domaintools", "default", "data", "tld_cache.json")
tldextract_cached = tldextract.TLDExtract(cache_file=cache_path)

def main():
    args, kwargs = splunk.Intersplunk.getKeywordsAndOptions()
    output_events = []
    domain_field = kwargs.get("domain_field", None)
    if not domain_field:
        output_events = splunk.Intersplunk.generateErrorResults("No domain field specified")
        splunk.Intersplunk.outputResults(output_events)
        return

    (results, dummyresults, settings) = splunk.Intersplunk.getOrganizedResults()
    for result in results:
        new_event = result
        if not domain_field in result:
            output_events.append(new_event)
            continue
        try:
            domain_or_ip = result[domain_field]
            extracted = tldextract_cached(domain_or_ip)
            if extracted.suffix == '':
                domain = extracted.domain
            else:
                domain = "%s.%s" %(extracted.domain, extracted.suffix)
            new_event[domain_field] = domain
            output_events.append(new_event)
        except:
            pass
    splunk.Intersplunk.outputResults(output_events)

main()
