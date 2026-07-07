import csv
import json
import re
import splunk.rest as rest

from splunk import AuthenticationFailed
from splunk.clilib.bundle_paths import make_splunkhome_path

# Python 2+3 basestring
try:
    basestring
except NameError:
    basestring = str

# set the maximum allowable CSV field size
#
# The default of the csv module is 128KB; upping to 10MB. See SPL-12117 for
# the background on issues surrounding field sizes.
# (this method is new in python 2.5)
csv.field_size_limit(10485760)


class CEFSearchException(Exception):
    """Custom exception for CEF Search REST handler"""
    pass


class CEFSearchGenerator(object):
    # Globals
    CEF_INVENTORY_PATH = make_splunkhome_path(['etc', 'apps', 'splunk_app_cef', 'lookups', 'cef_inventory.csv'])
    # CEF Value Types
    CEF_VALUE_TYPES = ['fieldmap', 'userdefined']  
    # CEF Prefix Template
    CEF_PREFIX_TEMPLATE = '"CEF:".%s."|".%s."|".%s."|".%s."|".%s."|".%s."|".%s'
    # Splunk Subject Keys
    # These fields can take on a number of value types (ipv4, ipv6, nt_host, dns, mac, etc.)
    # These will need special treatment when generating the CEF Extension
    # Should not affect Syslog Header or CEF Prefix
    SPLUNK_SUBJECT_KEYS = ['host', 'orig_host', 'src', 'dest', 'dvc']
    SPLUNK_SUBJECT_KEYS_RE = re.compile('^.*(?:' + '|'.join([re.escape(x) for x in SPLUNK_SUBJECT_KEYS]) + ')$')
    # CEF Extension Subjects
    CEF_EXTENSION_SOURCES = ['src', 'smac', 'shost']
    CEF_EXTENSION_DESTINATIONS = ['dst', 'dmac' ,'dhost']
    CEF_EXTENSION_DEVICES = ['dvc', 'deviceMacAddress', 'dvchost']
    # CEF Subject Keys
    CEF_SUBJECT_KEYS = []
    CEF_SUBJECT_KEYS.extend(CEF_EXTENSION_SOURCES)
    CEF_SUBJECT_KEYS.extend(CEF_EXTENSION_DESTINATIONS)
    CEF_SUBJECT_KEYS.extend(CEF_EXTENSION_DEVICES)
        
    CEF_EXTENSION_IPS = ['src','dst','dvc']
    CEF_EXTENSION_MACS = ['smac', 'dmac','deviceMacAddress']
    CEF_EXTENSION_HOSTS = ['shost','dhost','dvchost']
    # CEF Subject Templates    
    CEF_IP_TEMPLATE = '`get_cef_ip(%s,%s)`'
    CEF_MAC_TEMPLATE = '`get_cef_mac(%s,%s)`'
    CEF_HOST_TEMPLATE = '`get_cef_host(%s,%s)`'

    @staticmethod
    def get_cef_search(spec, session_key=None, preview_mode=False):
        """Generate a CEF search from JSON specification.

        @param spec:        The specification of the CEF search to generate
                            in JSON.
        @param session_key: A splunkd session key

        @return srch:       The search that was generated in string form.
        @return parses:     A boolean representing whether or not the search parsed.
        """
        # CEF Search Templates
        # cef_search{0} - datamodel
        # cef_search{1} - object
        # cef_search{2} - cef_eval
        # cef_search{3} - cef_routing
        cef_search_template = '| datamodel %s %s search %s %s'
        # cef_eval{0} - syslog header
        # cef_eval{1} - cef prefix
        # cef_eval{2} - cef_extension
        cef_eval = ''
        cef_eval_template = '| eval _raw=%s." ".%s%s | fields + _time,_raw'
        # cef_extension{0} - cef_extension
        cef_extension_template = '."|".%s'
        # cef_routing{0} - routing group
        cef_routing = ''
        cef_routing_template = '| cefout routing=%s'

        # Step 0: Validate sessionKey   
        if not session_key:
            raise AuthenticationFailed

        # Step 1: Load and validate spec
        try:
            spec = json.loads(spec)
        except Exception:
            raise CEFSearchException('Error loading spec parameter')

        if not isinstance(spec, dict):
            raise CEFSearchException('Error loading spec parameter')

        # Step 2: Load and validate datamodel/object
        datasource = spec.get('datasource', {})
        if (isinstance(datasource, dict)
           and datasource.get('datamodel')
           and datasource.get('object')):
            datamodel = datasource.get('datamodel')
            object = datasource.get('object')
        else:
            raise CEFSearchException('Invalid datasource specification')

        # Step 3: Load and validate routing
        if not preview_mode:
            routing = spec.get('routing')
            if not (routing and re.match(r'[\w-]+', routing)):
                raise CEFSearchException('Invalid routing specification')
            cef_routing = cef_routing_template % routing

        # Step 4: Load and validate fieldmap
        fieldmap = spec.get('fieldmap')
        if isinstance(fieldmap, dict):
            header = CEFSearchGenerator.get_cef_header(fieldmap)
            prefix = CEFSearchGenerator.get_cef_prefix(fieldmap)
            extension = CEFSearchGenerator.get_cef_extension(fieldmap)
            if extension:
                extension = cef_extension_template % (extension)
            else:
                extension = ''
            cef_eval = cef_eval_template % (header, prefix, extension)
        else:
            if not preview_mode:
                raise CEFSearchException('Invalid fieldmap specification')

        # Step 5: Build search
        srch = cef_search_template % (
            datamodel,
            object,
            cef_eval,
            cef_routing)
        srch = srch.rstrip()

        # Step 6:  Parsing
        parses = False
        if srch:
            r, c = rest.simpleRequest(
                'search/parser',
                sessionKey=session_key,
                getargs={
                    'q': srch,
                    'parse_only':  't',
                    'output_mode': 'json'
                }
            )
            parses = (r.status == 200)

        return srch, parses

    @staticmethod
    def get_cef_mapping(fieldmap, cef_key, default='', quote_int=True):
        """ The following method returns properly quoted field or value mappings
         * If cef_value_type is fieldmap then we single quote the value
         * If cef_value_type is userdefined string then we double quote the value
         * If cef_value_type is userdefined number then we double quote the value
           depending on the quote_int parameter

        @param fieldmap:  The field mapping dictionary
        @param cef_key:   The key (string) of the mapping we're after
        @param default:   The value to return if cef_key is not available
                          or if cef_value_type is invalid
        @param quote_int: Whether or not to quote the userdefined value if
                          it is a number

        @return mapping:  cef_mapping (string) based on the requested key
        """
        if cef_key in fieldmap:
            cef_value_type = fieldmap[cef_key].get('cef_value_type', 'fieldmap')
            if (cef_value_type == 'fieldmap'
               and 'splunk_key' in fieldmap[cef_key]
               and isinstance(fieldmap[cef_key]['splunk_key'], basestring)):
                return "'%s'" % fieldmap[cef_key]['splunk_key']
            elif (cef_value_type == 'userdefined'
                    and 'cef_value' in fieldmap[cef_key]
                    and isinstance(fieldmap[cef_key]['cef_value'], basestring)):
                try:
                    float(fieldmap[cef_key]['cef_value'])
                    if quote_int:
                        return '"%s"' % fieldmap[cef_key]['cef_value']
                    else:
                        return fieldmap[cef_key]['cef_value']
                except Exception:
                    return '"%s"' % fieldmap[cef_key]['cef_value']
            else:
                return default
        else:
            return default

    @staticmethod
    def get_cef_header(fieldmap):
        """The following method generates the syslog header for a CEF message using eval
           This method uses cef_key=syslog_time and cef_key=syslog_host
           syslog_time must be a fieldmap to one of [_time,_indextime]

           @param fieldmap:    A dictionary representation of the fields to map

           @return cef_header: A string representing the header portion of
                               the CEF generating search
        """
        # syslog header template
        header_template = '%s." ".%s'

        # syslog_time is single quoted here because we only allow fieldmap
        # MV handling is done via isnotnull(strftime('%s',"%s"))
        syslog_time_template = '''if(isnotnull(strftime('%s',"%s")),strftime('%s',"%s"),strftime(time(),"%s"))'''
        syslog_time = '_time'
        syslog_time_format = '%b %d %H:%M:%S'

        if ('syslog_time' in fieldmap
           and fieldmap['syslog_time'].get('cef_value_type', 'fieldmap')=='fieldmap'
           and fieldmap['syslog_time'].get('splunk_key')
           and fieldmap['syslog_time']['splunk_key'] in ['_time','_indextime']):
            syslog_time = fieldmap['syslog_time']['splunk_key']

            if fieldmap['syslog_time'].get('time_format'):
                syslog_time_format = fieldmap['syslog_time']['time_format']

        syslog_time = syslog_time_template % (syslog_time,syslog_time_format,syslog_time,syslog_time_format,syslog_time_format)

        # syslog_host template
        # syslog_host is not escaped here because it is handled by get_cef_mapping
        # MV handling w/ mvcount/mvindex
        syslog_host_template = '''case(mvcount(%s)>=1,mvindex(%s,0),mvcount('host')>=1,mvindex('host',0),1=1,"unknown")'''
        syslog_host = CEFSearchGenerator.get_cef_mapping(fieldmap, 'syslog_host', "'host'")
        syslog_host = syslog_host_template % (syslog_host,syslog_host)

        return header_template % (syslog_time,syslog_host)    

    @staticmethod
    def get_cef_prefix(fieldmap):
        """The following method generates the CEF prefix for a CEF message using eval
           This method uses the following cef keys: version,dvc_vendor,dvc_product,dvc_version,signature_id,name,severity

           @param fieldmap:       A dictionary representation of the fields to map
           
           @return cef_prefix: A string representing the header portion of
                                  the CEF generating search
        """
        # CEF Version Template
        # version is not escaped because we use get_cef_mapping(quoteMap=True, quoteInt=False)
        # MV handling w/ isnum
        # WARNING: isnum("1") evaluates to false
        version_template = 'if(isnum(%s),%s,0)'
        version = CEFSearchGenerator.get_cef_mapping(fieldmap, 'version', default='0', quote_int=False)         
        version = version_template % (version, version)        

        # CEF Vendor and Product Template
        # vendor/product are not escaped because we use get_cef_mapping
        # MV handling w/ mvcount/mvindex
        device_vp_template  = '''case(mvcount(%s)>=1 AND mvindex(%s,0)!="unknown",mvindex(%s,0),mvcount('sourcetype')>=1,mvindex('sourcetype',0),1=1,"unknown")'''
        default_dvc_vendor  = "'vendor'"
        default_dvc_product = "'product'"
        # This gets special treatment when splunk_key ends with "vendor_product"
        dvc_vendor = CEFSearchGenerator.get_cef_mapping(fieldmap, 'dvc_vendor', default=default_dvc_vendor)
        if dvc_vendor.endswith("vendor_product'"):
            dvc_vendor = default_dvc_vendor
        dvc_vendor          = device_vp_template % (dvc_vendor,dvc_vendor,dvc_vendor)        
        # This gets special treatment when splunk_key ends with "vendor_product"
        dvc_product = CEFSearchGenerator.get_cef_mapping(fieldmap, 'dvc_product', default=default_dvc_product)
        if dvc_product.endswith("vendor_product'"):
            dvc_product = default_dvc_product     
        dvc_product = device_vp_template % (dvc_product,dvc_product,dvc_product)
        
        # CEF Device Version Template
        # dvc_version is not escaped because we use get_cef_mapping
        # MV handling w/ mvcount/mvindex
        device_version_template = '''if(mvcount(%s)>=1,mvindex(%s,0),"unknown")'''
        dvc_version = CEFSearchGenerator.get_cef_mapping(fieldmap, 'dvc_version', default="'product_version'")
        dvc_version = device_version_template % (dvc_version,dvc_version)
        
        # CEF Signature ID Template
        # signature_id is not excaped because we use get_cef_mapping
        # MV handling w/ mvcount/mvindex
        signature_id_template = '''if(mvcount(%s)>=1,mvindex(%s,0),"unknown")'''
        signature_id = CEFSearchGenerator.get_cef_mapping(fieldmap, 'signature_id', default="'signature_id'")
        signature_id = signature_id_template % (signature_id,signature_id)
        
        # CEF Name Template
        # name is not escaped because we use get_cef_mapping
        # MV handling w/ mvcount/mvindex
        name_template = '''case(mvcount(%s)>=1,mvindex(%s,0),mvcount('name')>=1,mvindex('name',0),1=1,"unknown")'''
        name = CEFSearchGenerator.get_cef_mapping(fieldmap, 'name', default="'signature'")
        name = name_template % (name, name)

        # CEF Severity Template
        # severity is not escaped because it is used in a macro call
        # MV handling w/ direct string comparisons
        severity_template_fieldmap = '`get_cef_severity_fieldmap(%s)`'
        severity_template_userdefined = '`get_cef_severity_userdefined(%s)`'

        default_severity = severity_template_userdefined % 5
        if 'severity' in fieldmap:
            cef_value_type = fieldmap['severity'].get('cef_value_type', 'fieldmap')
            if (cef_value_type=='fieldmap'
               and isinstance(fieldmap['severity']['splunk_key'], basestring)):
                severity = severity_template_fieldmap % fieldmap['severity']['splunk_key']
            elif (cef_value_type=='userdefined'
               and isinstance(fieldmap['severity']['cef_value'], basestring)):
                severity = severity_template_userdefined % fieldmap['severity']['cef_value']
            else:
                severity = default_severity
        else:
            severity = default_severity

        return CEFSearchGenerator.CEF_PREFIX_TEMPLATE % (
            version,
            dvc_vendor,
            dvc_product,
            dvc_version,
            signature_id,
            name,
            severity)

    @staticmethod
    def get_extension_keys():
        """ The following method returns a list
        of cef_key values where location=extension 

        @return A list of CEF extension keys
        """
        with open(CEFSearchGenerator.CEF_INVENTORY_PATH, 'rU') as fh:
            cef_inventory = csv.DictReader(fh)
            keys = [
                x['cef_key']
                for x in cef_inventory
                if x.get('cef_key') and x.get('location','')=='extension'
            ]
        
        return keys    

    @staticmethod
    def get_cef_extension(fieldmap):
        """The following method generates the CEF extension for a CEF message using eval
           This method uses the cef_key values returned by getExtensionKeys()

           @param fieldmap:   A dictionary representation of the fields to map

           @return extension: A string representing the extension portion of
                              the CEF generating search
        """
        # Internal get_cef_extension method for code simplification purposes
        def add_subject_to_extension(cef_subject_list, splunk_key, extension):
            # iterate over each subject field in the list provided
            for cef_subject in cef_subject_list:
                # if subject is an IP
                if cef_subject in CEFSearchGenerator.CEF_EXTENSION_IPS:
                    extension += (CEFSearchGenerator.CEF_IP_TEMPLATE % (splunk_key, cef_subject) + '.')
                # if subject is a MAC
                elif cef_subject in CEFSearchGenerator.CEF_EXTENSION_MACS:
                    extension += (CEFSearchGenerator.CEF_MAC_TEMPLATE % (splunk_key, cef_subject) + '.')
                # if subject is a Host
                elif cef_subject in CEFSearchGenerator.CEF_EXTENSION_HOSTS:
                    extension += (CEFSearchGenerator.CEF_HOST_TEMPLATE % (splunk_key, cef_subject) + '.')

            return extension

        extension = ''
        # CEF Extension Templates
        # MV handling w/ mvcount/mvindex
        extension_template = '''if(mvcount(%s)>=1,"%s=".mvjoin(%s,"\\n")." ","")'''

        # Step 1: Find available extension keys in the fieldmap
        #         Also call out extension keys which are subject fields
        # extension_keys
        extension_keys = list(set(fieldmap) & set(CEFSearchGenerator.get_extension_keys()))
        # handle subject extensions
        cef_subject_keys = list(set(fieldmap) & set(CEFSearchGenerator.CEF_SUBJECT_KEYS))
        # Determine if the fieldmap has any mappings to a splunk_key ending in CEFSearchGenerator.SPLUNK_SUBJECT_KEYS
        extension_subjects = [
            x for x in cef_subject_keys
            if (
                fieldmap[x].get('cef_value_type', 'fieldmap') == 'fieldmap'
                and CEFSearchGenerator.SPLUNK_SUBJECT_KEYS_RE.match(fieldmap[x].get('splunk_key', ''))
            )
        ]

        # Step 2: Add 1 extension per src/dest/dvc set
        processed_keys = []
        src_found = False
        dest_found = False
        dvc_found = False
        # iterate over each of the extension subject fields we've discovered     
        for cef_subject_key in sorted(extension_subjects):
            splunk_key = fieldmap[cef_subject_key].get('splunk_key')
            # if cef_subject_key is a source subject field
            if not src_found and cef_subject_key in CEFSearchGenerator.CEF_EXTENSION_SOURCES:
                extension = add_subject_to_extension(
                    CEFSearchGenerator.CEF_EXTENSION_SOURCES,
                    splunk_key,
                    extension)
                processed_keys.extend(CEFSearchGenerator.CEF_EXTENSION_SOURCES)
                src_found = True
            # if cef_subject_key is a destination field
            elif not dest_found and cef_subject_key in CEFSearchGenerator.CEF_EXTENSION_DESTINATIONS:
                extension = add_subject_to_extension(
                    CEFSearchGenerator.CEF_EXTENSION_DESTINATIONS,
                    splunk_key,
                    extension)
                processed_keys.extend(CEFSearchGenerator.CEF_EXTENSION_DESTINATIONS)
                dest_found = True
            # if cef_subject_key is a device field
            elif not dvc_found and cef_subject_key in CEFSearchGenerator.CEF_EXTENSION_DEVICES:
                extension = add_subject_to_extension(
                    CEFSearchGenerator.CEF_EXTENSION_DEVICES,
                    splunk_key,
                    extension)
                processed_keys.extend(CEFSearchGenerator.CEF_EXTENSION_DEVICES)
                dvc_found = True

        # Step 3. Remove extension keys already processed
        extension_keys = [x for x in extension_keys if x not in processed_keys]

        # Step 4. Iterate the rest of the extension keys
        for cef_key in sorted(extension_keys):
            mapping = CEFSearchGenerator.get_cef_mapping(fieldmap, cef_key)
            extension += (extension_template % (mapping, cef_key,mapping) + '.')

        # rstrip period     
        return extension.rstrip('.')
