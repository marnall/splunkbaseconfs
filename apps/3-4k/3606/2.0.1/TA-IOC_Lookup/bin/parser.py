#
# Splunk integration, data parser: nick 2017
#
import logging


class parser:
        """
        Munge Json results from single api request.

        :param json data
        :param searchtype
        :param searchvalue
        :returns parsed dict of useful data
        """

        def __init__(self):
            """initialize a bunch of stuff."""
            self.log = logging.getLogger("securitylookup")

        def threatcrowd_parser(self, searchtype, searchvalue, json_data):
            """Parse TC data for valuable stuff."""
            parsed_result = {}
            parsed_result["SearchType"] = searchtype
            parsed_result["SearchValue"] = searchvalue
            if json_data["response_code"] == "0":
                self.log.info("Not in ThreatCrowd database...")
                parsed_result["Response"] = "No result in ThreatCrowd Database."

            elif json_data["response_code"] == "1":
                self.log.debug("Found in ThreatCrowd database...")
                parsed_result["Permalink"] = json_data["permalink"]
                if searchtype == "file_hash":
                    parsed_result["AV_Results"] = json_data["scans"][:20]
                    parsed_result["IPs"] = json_data["ips"][:20]
                    parsed_result["Domains"] = json_data["domains"][:20]
                    parsed_result["References"] = json_data["references"]

                    parsed_result["md5"] = json_data["md5"]
                    parsed_result["sha1"] = json_data["sha1"]

                elif searchtype == "domain":
                    hash_list = json_data["hashes"][:20]
                    parsed_result["Hashes"] = hash_list[:20]
                    parsed_result["Emails"] = json_data["emails"][:20]
                    parsed_result["Subdomains"] = json_data["subdomains"][:20]

                    ip_list = []
                    for d in json_data["resolutions"]:
                        ip_list.append(d["ip_address"])
                    parsed_result["IPs"] = ip_list[:20]

                elif searchtype == "ip":
                    parsed_result["Hashes"] = json_data["hashes"][:20]

                    domain_list = []
                    for d in json_data["resolutions"]:
                        domain_list.append(d["domain"])
                    parsed_result["Domains"] = domain_list[:20]

            return parsed_result

        def virustotal_parser(self, searchtype, searchvalue, json_data):
            """Parse VT data for valuable stuff."""
            parsed_result = {}
            parsed_result["SearchType"] = searchtype
            parsed_result["SearchValue"] = searchvalue
            if json_data["response_code"] == 0:
                # Virustotal did not have a result
                self.log.info("Not in VirusTotal Database...")
                parsed_result["Response"] = json_data["verbose_msg"]
            elif json_data["response_code"] == -1:
                # VirusTotal returned an error
                self.log.info("Response: {}".format(json_data["verbose_msg"]))
                parsed_result["Response"] = json_data["verbose_msg"]
            elif json_data["response_code"] == 1:
                self.log.debug("Found in VirusTotal Database...")

                # parse vt hash result
                if searchtype == "file_hash":
                    if json_data["positives"] < 1:
                        self.log.info("In Virustotal, but no AV Hits")
                        parsed_result["Response"] = "In Virustotal, but no AV Hits"
                    else:
                        self.log.debug("There were AV Hits...")
                        parsed_result["Scan_Date"] = json_data["scan_date"]
                        parsed_result["Permalink"] = json_data["permalink"]
                        parsed_result["AV_Positives"] = json_data["positives"]

                        AV_Results = []
                        for k, v in json_data.items():
                            if k == "scans":
                                for subkey, subvalue in v.items():
                                    if subvalue["detected"] == True:
                                        AV_Results.append(subvalue["result"])
                        AV_Results = list(set(AV_Results))
                        parsed_result["AV_Results"] = AV_Results[:20]

                        parsed_result["md5"] = json_data["md5"]
                        parsed_result["sha1"] = json_data["sha1"]
                        parsed_result["sha256"] = json_data["sha256"]

                # parse vt domain result
                elif searchtype == "domain":
                    detected_urls_list = []
                    for d in json_data["detected_urls"]:
                        detected_urls_list.append(d["url"])
                    if detected_urls_list:
                        parsed_result["Detected_URLs"] = detected_urls_list[:20]

                    if json_data["domain_siblings"]:
                        parsed_result["Domain_Siblings"] = json_data["domain_siblings"][:20]

                    resolutions_list = []
                    for d in json_data["resolutions"]:
                        resolutions_list.append(d["ip_address"])
                    if resolutions_list:
                        resolutions_list = list(set(resolutions_list))
                        parsed_result["Resolutions"] = resolutions_list[:20]

                    # Whois is a long string, delimited by \\n, split into list
                    if json_data["whois"]:
                        whois_list = [s.strip() for s in json_data["whois"].splitlines()]
                        parsed_result["Whois"] = whois_list[:20]

                    # these may not exist in the json
                    try:
                        parsed_result["Categories"] = json_data["categories"]
                    except Exception:
                        pass
                    try:
                        parsed_result["Websense ThreatSeeker category"] = json_data["Websense ThreatSeeker category"]
                    except Exception:
                        pass
                    try:
                        parsed_result["BitDefender category"] = json_data["BitDefender category"]
                    except Exception:
                        pass
                    try:
                        parsed_result["Subdomains"] = json_data["subdomains"][:20]
                    except Exception:
                        pass
                    try:
                        if json_data["undetected_referrer_samples"]:
                            undetected_ref_list = []
                            for d in json_data["undetected_referrer_samples"]:
                                undetected_ref_list.append(d["sha256"])
                            parsed_result["undetected_referrer_samples"] = undetected_ref_list[:20]
                    except Exception:
                        pass
                    try:
                        if json_data["detected_downloaded_samples"]:
                            detected_downloaded_samples = []
                            for d in json_data["detected_downloaded_samples"]:
                                detected_downloaded_samples.append(d["sha256"])
                            parsed_result["detected_downloaded_samples"] = detected_downloaded_samples[:20]
                    except Exception:
                        pass
                    try:
                        parsed_result["Webutation"] = json_data["Webutation domain info"]["Verdict"]
                    except Exception:
                        pass
                    try:
                        parsed_result["Dr.Web"] = json_data["Dr.Web category"]
                    except Exception:
                        pass

                # parse vt ip result
                elif searchtype == "ip":
                    try:
                        parsed_result["ASN"] = json_data["asn"]
                    except KeyError:
                        pass
                    try:
                        parsed_result["Country"] = json_data["country"]
                    except KeyError:
                        pass
                    try:
                        parsed_result["AS_Owner"] = json_data["as_owner"]
                    except KeyError:
                        pass

                    try:
                        resolutions_list = []
                        for d in json_data["resolutions"]:
                            resolutions_list.append(d["hostname"])
                        if resolutions_list:
                            parsed_result["Resolutions"] = resolutions_list[:20]
                    except Exception:
                        pass

                    try:
                        detected_urls_list = []
                        for d in json_data["detected_urls"]:
                            detected_urls_list.append(d["url"])
                        if detected_urls_list:
                            parsed_result["Detected URLs"] = detected_urls_list[:20]
                    except Exception:
                        pass

                    # these may not exist in the json
                    try:
                        if json_data["undetected_downloaded_samples"]:
                            undetected_downloaded_samples = []
                            for d in json_data["undetected_downloaded_samples"]:
                                undetected_downloaded_samples.append(d["sha256"])
                            parsed_result["undetected_downloaded_samples"] = undetected_downloaded_samples[:20]
                    except Exception:
                        pass
                    try:
                        if json_data["detected_downloaded_samples"]:
                            detected_downloaded_samples = []
                            for d in json_data["detected_downloaded_samples"]:
                                detected_downloaded_samples.append(d["sha256"])
                            parsed_result["detected_downloaded_samples"] = detected_downloaded_samples[:20]
                    except Exception:
                        pass
                    try:
                        if json_data["detected_communicating_samples"]:
                            detected_communicating_samples = []
                            for d in json_data["detected_communicating_samples"]:
                                detected_communicating_samples.append(d["sha256"])
                            parsed_result["detected_communicating_samples"] = detected_communicating_samples[:20]
                    except Exception:
                        pass

            return parsed_result

        def totalhash_parser(self, searchtype, searchvalue, json_data):
            """Parse TH data for valuable stuff."""
            parsed_result = {}
            parsed_result["SearchType"] = searchtype
            parsed_result["SearchValue"] = searchvalue
            if searchtype == "file_hash":
                parsed_result["Magic"] = json_data["analysis"]["static"]["magic"]["@value"]
                parsed_result["Scan_Date"] = json_data["analysis"]["@time"]

                # begin the munge
                av_results_list = []
                dns_list = []
                dest_ip_list = []
                http_list = []
                for k, v in json_data.items():
                    if type(v) == dict:
                        for subkey, subvalue in v.items():
                            if type(subvalue) == dict:
                                for subkey2, subvalue2 in subvalue.items():
                                    if type(subvalue2) == dict:
                                        if subkey2 == "av":
                                            if subvalue2["@signature"]:
                                                av_results_list.append(subvalue2["@signature"])
                                        elif subkey2 == "dns":
                                            dns_list.append(subvalue2["@rr"])
                                        elif subkey2 == "flows":
                                            dest_ip_list.append(subvalue2["@dst_ip"])
                                        elif subkey2 == "http":
                                            http_list.append(subvalue2["#text"])
                                    if type(subvalue2) == list:
                                        for d in subvalue2:
                                            if subkey2 == "av":
                                                if d["@signature"]:
                                                    av_results_list.append(d["@signature"])
                                            elif subkey2 == "dns":
                                                if "@rr" in d:
                                                    dns_list.append(d["@rr"])
                                                else:
                                                    pass
                                            elif subkey2 == 'flows':
                                                dest_ip_list.append(d['@dst_ip'])
                                            elif subkey2 == 'http':
                                                http_list.append(d['#text'])

                if av_results_list:
                    parsed_result["AV_Results"] = av_results_list[:20]
                if dns_list:
                    parsed_result["DNS_Results"] = dns_list[:20]
                if dest_ip_list:
                    parsed_result["Dest_IPs"] = dest_ip_list[:20]
                if http_list:
                    parsed_result["HTTP_Requests"] = http_list[:20]

            elif (searchtype == "domain" or searchtype == "ip"):
                if int(json_data["response"]["result"]["@numFound"]) > 0:
                    parsed_result["Number of Results"] = int(json_data["response"]["result"]["@numFound"])
                    sample_list = []
                    for k, v in json_data.items():
                        if type(v) == dict:
                            for subkey, subvalue in v.items():
                                for subkey2, subvalue2 in subvalue.items():
                                    if type(subvalue2) == list:
                                        for d in subvalue2:
                                            if subkey2 == 'doc':
                                                sample_list.append(d['str']['#text'])
                                    elif type(subvalue2) == dict:
                                        if subkey2 == 'doc':
                                            sample_list.append(subvalue2['str']['#text'])
                    parsed_result["Matching_Samples"] = sample_list[:20]
                else:
                    self.log.info("No results found for the {} in TotalHash".format(searchtype))
                    parsed_result['Response'] = "No results found for the {} in TotalHash".format(searchtype)
            return parsed_result

        def passivetotal_parser(self, searchtype, searchvalue, json_data):
            """Parse PT data for valuable stuff."""
            parsed_result = {}
            parsed_result["SearchType"] = searchtype
            parsed_result["SearchValue"] = searchvalue
            if json_data["totalRecords"] == 0:
                self.log.info("No results found for the {} in PassiveTotal".format(searchtype))
                parsed_result["Response"] = "No results found for the {} in PassiveTotal".format(searchtype)
            elif json_data["totalRecords"] > 0:
                self.log.debug("Found in PassiveTotal Database...")
                parsed_result["Total Records"] = json_data["totalRecords"]
                value_list = []
                resolve_list = []
                source_list = []
                for d in json_data["results"]:
                    value_list.append(d["value"])
                    resolve_list.append(d["resolve"])
                    for ref in d["source"]:
                        source_list.append(ref)
                if value_list:
                    value_list2 = list(set(value_list))
                    parsed_result["Values"] = value_list2[:20]
                if resolve_list:
                    resolve_list2 = list(set(resolve_list))
                    parsed_result["Resolutions"] = resolve_list2[:20]
                if source_list:
                    source_list2 = list(set(source_list))
                    parsed_result["Sources"] = source_list2[:20]
            return parsed_result

        def censys_parser(self, searchtype, searchvalue, json_data):
            """Parse Censys.io data for valuable stuff."""
            parsed_result = {}
            parsed_result["SearchType"] = searchtype
            parsed_result["SearchValue"] = searchvalue

            location_list = []
            location_list.append("Province: {}".format(json_data['location']['province']))
            location_list.append("City: {}".format(json_data['location']['city']))
            location_list.append("Country: {}".format(json_data['location']['country']))
            location_list.append("Registered Country: {}".format(json_data['location']['registered_country_code']))
            location_list.append("ASN: {}".format(json_data['autonomous_system']['name']))
            location_list.append("Route Prefix: {}".format(json_data['autonomous_system']['routed_prefix']))
            location_list.append("Organization: {}".format(json_data['autonomous_system']['organization']))
            parsed_result["Location"] = location_list

            asn_number_list = []
            for d in json_data['autonomous_system']['path']:
                asn_number_list.append(str(d))
            if asn_number_list:
                parsed_result["ASNs"] = asn_number_list[:20]

            protocols_list = []
            for d in json_data['protocols']:
                protocols_list.append(d)
            if protocols_list:
                parsed_result["Protocols"] = protocols_list[:20]

            dns_resolves_list = []
            try:
                for d in json_data['443']['https']['tls']['certificate']['parsed']['extensions']['subject_alt_name']['dns_names']:
                    dns_resolves_list.append(d)
            except KeyError:
                pass
            if dns_resolves_list:
                parsed_result["DNS Resolutions"] = dns_resolves_list[:20]

            return parsed_result

