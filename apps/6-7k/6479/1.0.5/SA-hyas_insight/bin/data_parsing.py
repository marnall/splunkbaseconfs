# Parsing of json response and validation of userinputs are done using these
# fucntions.

class Data_Parsing:

    # Flattening of json response for parsing the data and breaking the
    # nested json objects.
    def flatten_data(raw_data):

        out = {}

        def flatten(parse_data, name=''):
            if type(parse_data) is dict:
                for a in parse_data:
                    flatten(parse_data[a], name + a + '_')
            else:
                out[name[:-1]] = parse_data

        flatten(raw_data)
        return out

    # Parsing json response for passive dns endpoint.
    def passive_parse_data(final_dict):
        final_result = {}
        final_result_list = []
        for ckey, rkey, f in (
                ('Count', 'count', str),
                ('Domain', 'domain', str),
                ('First Seen', 'first_seen', str),
                ('City Name', 'ip_geo_city_name', str),
                ('Country Iso Code', 'ip_geo_country_iso_code', str),
                ('Country Name', 'ip_geo_country_name', str),
                ('Location Latitude', 'ip_geo_location_latitude', str),
                ('Location Longitude', 'ip_geo_location_longitude', str),
                ('Postal Code', 'ip_geo_postal_code', str),
                ('Ip', 'ip_ip', str),
                ('Autonomous System Number', 'ip_isp_autonomous_system_number',
                 str),
                ('Autonomous System Organization',
                 'ip_isp_autonomous_system_organization', str),
                ('Isp Ip Address', 'ip_isp_ip_address', str),
                ('Isp', 'ip_isp_isp', str),
                ('Isp Organization', 'ip_isp_organization', str),
                ('Ipv4', 'ipv4', str),
                ('Last Seen', 'last_seen', str),
                ('Sources', 'sources', list),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for dynamic dns endpoint.
    def dynamic_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('A Record', 'a_record', str),
                ('Account', 'account', str),
                ('Created Date', 'created', str),
                ('Account Holder IP Address', 'created_ip', str),
                ('Domain', 'domain', str),
                ('Domain Creator IP Address', 'domain_creator_ip', str),
                ('Email Address', 'email', str),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for c2attribution dns endpoint.
    def cattribution_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Actor IPv4', 'actor_ipv4', str),
                ('C2 Domain', 'c2_domain', str),
                ('C2 IP', 'c2_ip', str),
                ('C2 URL', 'c2_url', str),
                ('Datetime', 'datetime', str),
                ('Email', 'email', str),
                ('Email Domain', 'email_domain', str),
                ('Referrer Domain', 'referrer_domain', str),
                ('Referrer IPv4', 'referrer_ipv4', str),
                ('Referrer URL', 'referrer_url', str),
                ('SHA256', 'sha256', str)

        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for device endpoint.
    def device_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Date Time', 'datetime', str),
                ('Device Geo ID', 'device_geo_id', str),
                ('Device User Agent', 'device_user_agent', str),
                ('Geo Country Alpha 2', 'geo_country_alpha_2', str),
                (
                'Geo Horizontal Accuracy IPV4', 'geo_horizontal_accuracy', str),
                ('IPV4', 'ipv4', str),
                ('IPV6', 'ipv6', str),
                ('Latitude', 'latitude', str),
                ('Longitude', 'longitude', str),
                ('Wifi Bssid', 'wifi_bssid', str),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for ssl certificate endpoint.
    def ssl_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Geo City Name', 'geo_geo_city_name', str),
                ('Geo Country ISO code', 'geo_geo_country_iso_code', str),
                ('Geo Country Name', 'geo_geo_country_name', str),
                ('Latitude', 'geo_geo_location_latitude', str),
                ('Longitude', 'geo_geo_location_longitude', str),
                ('Postal Code', 'geo_geo_postal_code', str),
                ('ISP Autonomous System Number',
                 'geo_isp_autonomous_system_number', str),
                ('ISP Autonomous System Organization',
                 'geo_isp_autonomous_system_organization', str),
                ('Geo ISP', 'geo_isp_isp', str),
                ('Geo ISP Organization', 'geo_isp_organization', str),
                ('IP', 'ip', str),
                ('SSL Certificate Key', 'ssl_cert_cert_key', str),
                ('Expire Date', 'ssl_cert_expire_date', str),
                ('Issue Date', 'ssl_cert_issue_date', str),
                ('Issuer Common Name', 'ssl_cert_issuer_commonName', str),
                ('Issuer Country Name', 'ssl_cert_issuer_countryName', str),
                ('Issuer Locality Name', 'ssl_cert_issuer_localityName', str),
                ('Issuer Organization Name', 'ssl_cert_issuer_organizationName',
                 str),
                ('Issuer Organizational UnitName',
                 'ssl_cert_issuer_organizationalUnitName', str),
                ('Issuer State/Province Name',
                 'ssl_cert_issuer_stateOrProvinceName', str),
                ('Certificate MD5', 'ssl_cert_md5', str),
                ('Certificate Serial Number', 'ssl_cert_serial_number', str),
                ('Certificate SHA1', 'ssl_cert_sha1', str),
                ('Certificate SHA256', 'ssl_cert_sha_256', str),
                ('Certificate Signature Algo', 'ssl_cert_sig_algo', str),
                ('Certificate SSL Version', 'ssl_cert_ssl_version', str),
                ('Certificate Subject Common Name',
                 'ssl_cert_subject_commonName', str),
                ('Certificate Subject Country Name',
                 'ssl_cert_subject_countryName', str),
                ('Certificate Subject Locality Name',
                 'ssl_cert_subject_localityName', str),
                ('Certificate Subject Organization Name',
                 'ssl_cert_subject_organizationName', str),
                ('Certificate Subject Organizational Unit Name',
                 'ssl_cert_subject_organizationalUnitName', str),
                ('Certificate Subject State/Province Name',
                 'ssl_cert_subject_stateOrProvinceName', str),
                ('Certificate Timestamp', 'ssl_cert_timestamp', str)

        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for passivehash endpoint.
    def passivehash_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Domain', 'domain', str),
                ('MD5 Count', 'md5_count', str),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for sinkhole endpoint.
    def sinkhole_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Count', 'count', str),
                ('Country Name', 'country_name', str),
                ('Data Port', 'data_port', str),
                ('Date Time', 'datetime', str),
                ('IPV4', 'ipv4', str),
                ('Last Seen', 'last_seen', str),
                ('Organization Name', 'organization_name', str),
                ('Sink Source', 'sink_source', str),

        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for whois endpoint.
    def whois_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Address', 'address', list),
                ('City', 'city', list),
                ('Country', 'country', list),
                ('Domain', 'domain', str),
                ('Domain_2tld', 'domain_2tld', str),
                ('Domain Created Time', 'domain_created_datetime', str),
                ('Domain Expires Time', 'domain_expires_datetime', str),
                ('Domain Updated Time', 'domain_updated_datetime', str),
                ('Email Address', 'email', list),
                ('IDN Name', 'idn_name', str),
                ('Nameserver', 'nameserver', list),
                ('Phone Info', 'phone', list),
                ('Privacy_punch', 'privacy_punch', bool),
                ('Registrar', 'registrar', str),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    # Parsing json response for whois current endpoint.
    def whoiscurrent_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Abuse Emails', 'abuse_emails', list),
                ('Address', 'address', list),
                ('City', 'city', list),
                ('Country', 'country', list),
                ('Domain', 'domain', str),
                ('Domain_2tld', 'domain_2tld', str),
                ('Domain Created Time', 'domain_created_datetime', str),
                ('Domain Expires Time', 'domain_expires_datetime', str),
                ('Domain Updated Time', 'domain_updated_datetime', str),
                ('Email Address', 'email', list),
                ('IDN Name', 'idn_name', str),
                ('Nameserver', 'nameserver', list),
                ('Organization', 'organization', list),
                ('Phone Info', 'phone', list),
                ('Registrar', 'registrar', str),
                ('State', 'state', list),
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    def sample_information_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Scan Result AV Name', 'av_name', str),
                ('Scan Result AV Time', 'def_time', str),
                ('Scan Result Source', 'threat_found', str)
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    def sample_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Datetime', 'datetime', str),
                ('Domain','domain', str),
                ('IPv4', 'ipv4', str),
                ('IPv6', 'ipv6', str),
                ('MD5', 'md5', str),
                ('SHA1', 'sha1', str),
                ('SHA256', 'sha256', str)
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result

    def os_indicator_parse_data(final_dict):
        final_result = {}
        for ckey, rkey, f in (
                ('Correlation Score', 'map_correlation_score', float),
                ('Host IP', 'map_host_ips_myArrayList', list),
                ('Nameserver', 'map_nameservers_myArrayList', list),
                ('Stub Count', 'map_stub_count', int),
                ('Type', 'map_type', str),
                ('Context', 'context', str),
                ('Description', 'data_description', str),
                ('Datetime', 'datetime', str),
                ('Domain', 'domain', str),
                ('Domain 2tld', 'domain_2tld', str),
                ('First Seen', 'first_seen', str),
                ('IPv4', 'ipv4', str),
                ('IPv6', 'ipv6', str),
                ('Last Seen', 'last_seen', str),
                ('MD5', 'md5', str),
                ('OS Indicators ID', 'os_indicators_id', str),
                ('OS Indicators Source ID', 'os_indicators_source_id', str),
                ('SHA1', 'sha1', str),
                ('SHA256', 'sha256', str),
                ('Source Name', 'source_name', str),
                ('Source Url', 'source_url', str),
                ('URI', 'uri', str)
        ):
            if rkey in final_dict:
                final_result[ckey] = f(final_dict[rkey])

        return final_result