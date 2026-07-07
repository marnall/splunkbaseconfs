import urllib,csv,re,sys,os
from uasparser import UASparser

#
# Main routine - basically it's the standard python recipe for handling
# Splunk lookups
#
if __name__ == '__main__':
    # if our ua list cache dir doesn't exist, let's create it
    if not os.path.isdir('ua_cache'):
	os.makedirs('ua_cache')

    # init the ua parser
    uas = UASparser(cache_dir='ua_cache')
    uas.update_interval = (3600*24) *999 # 999 days.
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    have_header = False
    ver_parse = re.compile(r'(\s|:|")(?P<ua_version>(?P<ua_major_version>[\d]+)(.(?P<ua_minor_version>[r_ab0-9]+))?.?(?P<ua_build_version>[\d\._]*))$')

    
    header = []
    idx = -1
    for row in r:
        if (have_header == False):
            header = row
            have_header = True
            z = 0
            for h in row:
                if (h == "http_user_agent"):
                    idx = z
                z = z + 1
            w.writerow(row)
            continue
        
        # We only care about the cs_user_agent field - everything else is filled in
        http_user_agent = row[idx]
        useragent = urllib.unquote_plus(http_user_agent)
        # dict = parse_useragent(useragent)
	results = uas.parse(useragent)

	# "typ" is a bad field name, let's change that
	typ_temp = results['typ']
	results['ua_type'] = typ_temp

	# now let's get rid of fields we don't need
	del results['typ']
	del results['ua_url']
	del results['ua_company_url']
	del results['ua_icon']
	del results['os_url']
	del results['os_company_url']
	del results['os_icon']

	# let's get some version info:
	ua_major_version = ''
	ua_minor_version = ''
	ua_build_version = ''
	ver_match = ver_parse.search(results['ua_name'])
	if not ver_match is None:
		if not ver_match.group('ua_major_version') is None:
			ua_major_version = ver_match.group('ua_major_version')
		if not ver_match.group('ua_minor_version') is None:
			ua_minor_version = ver_match.group('ua_minor_version')
		if not ver_match.group('ua_build_version') is None:
			ua_build_version = ver_match.group('ua_build_version')

	# add it to the results
	results['ua_major_version'] = ua_major_version
	results['ua_minor_version'] = ua_minor_version
	results['ua_build_version'] = ua_build_version
        
        # Now write it out
        orow = []
        for header_name in header:
            if (header_name == "http_user_agent"):
                orow.append(http_user_agent)
            else:
                orow.append(results[header_name])
        w.writerow(orow)
            

