import urllib,csv,re,sys,os
from pybrowscap.loader.csv import load_file

def get_browser_info(browscap, ua):
        useragent = urllib.unquote_plus(http_user_agent)
	browser = browscap.search(http_user_agent)

	ua_info = {}
	if not browser is None:
		ua_info['ua_name'] = browser.category()
		ua_info['ua_category'] = browser.name()
		ua_info['ua_platform'] = browser.platform()
		ua_info['ua_version'] = browser.version()
		ua_info['ua_version_major'] = browser.version_major()
		ua_info['ua_version_minor'] = browser.version_minor()
		ua_info['ua_aol_version'] = browser.aol_version()
		ua_info['ua_is_crawler'] = browser.is_crawler()
		ua_info['ua_is_mobile'] = browser.is_mobile()
		ua_info['ua_is_syndication_reader'] = browser.is_syndication_reader()
		ua_info['ua_supports_tables'] = browser.supports_tables()
		ua_info['ua_supports_frames'] = browser.supports_frames()
		ua_info['ua_supports_iframes'] = browser.supports_iframes()
		ua_info['ua_supports_java'] = browser.supports_java()
		ua_info['ua_supports_javascript'] = browser.supports_javascript()
		ua_info['ua_supports_vbscript'] = browser.supports_vbscript()
		ua_info['ua_supports_activex'] = browser.supports_activex()
		ua_info['ua_supports_cookies'] = browser.supports_cookies()
		ua_info['ua_supports_css'] = browser.supports_css()
		ua_info['ua_is_alpha'] = browser.is_alpha()
		ua_info['ua_is_beta'] = browser.is_beta()
	else:
		ua_info['ua_name'] = 'unknown'
		ua_info['ua_category'] = 'unknown'
		ua_info['ua_platform'] = 'unknown'
		ua_info['ua_version'] = 'unknown'
		ua_info['ua_version_major'] = 'unknown'
		ua_info['ua_version_minor'] = 'unknown'
		ua_info['ua_aol_version'] = 'unknown'
		ua_info['ua_is_crawler'] = 'unknown'
		ua_info['ua_is_mobile'] = 'unknown'
		ua_info['ua_is_syndication_reader'] = 'unknown'
		ua_info['ua_supports_tables'] = 'unknown'
		ua_info['ua_supports_frames'] = 'unknown'
		ua_info['ua_supports_iframes'] = 'unknown'
		ua_info['ua_supports_java'] = 'unknown'
		ua_info['ua_supports_javascript'] = 'unknown'
		ua_info['ua_supports_vbscript'] = 'unknown'
		ua_info['ua_supports_activex'] = 'unknown'
		ua_info['ua_supports_cookies'] = 'unknown'
		ua_info['ua_supports_css'] = 'unknown'
		ua_info['ua_is_alpha'] = 'unknown'
		ua_info['ua_is_beta'] = 'unknown'

	return ua_info	

#
# Main routine - basically it's the standard python recipe for handling
# Splunk lookups
#
if __name__ == '__main__':

    # init the browscap class
    browscap = load_file('browscap.csv')
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    have_header = False
    
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
        
        # We only care about the user-agent field - everything else is filled in
        http_user_agent = row[idx]

	results = get_browser_info(browscap, http_user_agent)
	
        # Now write it out
        orow = []
        for header_name in header:
            if (header_name == "http_user_agent"):
                orow.append(http_user_agent)
            else:
                orow.append(results[header_name])
        w.writerow(orow)
            
