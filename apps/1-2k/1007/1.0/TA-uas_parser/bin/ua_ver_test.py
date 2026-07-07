import re

testvals = [
"IE 7.0",
"Firefox 3.6.3",
"Firefox 3.6.24",
"Firefox 8.0.1",
"Firefox 6.0",
"Firefox 9.0.1",
"Firefox 3.6.25",
"Firefox 3.0.19",
"Safari 5.1",
"Safari 5.1.1",
"Netscape Navigator 4.0",
"Chrome 16.0.912.63",
"Firefox 4.0.1",
"Wget 1.10.2",
"Firefox 3.6.13",
"Safari Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.52.7 (KHTML, like Gecko)",
"IE 8.0",
"Firefox 8.0",
"urlgrabber 3.1.0",
"Firefox 2.0.0.19",
"Safari 5.1.2",
"Firefox 3.6.23",
"Java 1.5.0_15",
"Firefox 3.6.9",
"Safari Mozilla/5.0 (Macintosh; Intel Mac OS X 10_5_8) AppleWebKit/534.50.2 (KHTML, like Gecko)",
"Apple-PubSub 65.28",
"Java 1.5.0_09",
"Mozilla rv:7.0.1",
"Adobe AIR runtime 3.1",
"IE 4.0",
"Safari Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.50 (KHTML, like Gecko)",
"Firefox 3.6.22",
"Python-urllib 2.6",
"Safari 5.0.6",
"WinHTTP winhttp",
"Chrome 14.0.835.202",
"Firefox 11.0a1",
"Safari Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/534.51.22 (KHTML, like Gecko)",
"Firefox 9.0",
"Firefox 2.0.0.21",
"Outlook 2007 Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.1; WOW64; Trident/4.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; MSOffice 12",
"Chrome 15.0.874.121",
"Firefox 12.0a1",
]

ver_parse = re.compile(r'(\s|:|")(?P<ua_version>(?P<ua_major_version>[\d]+)(.(?P<ua_minor_version>[r_ab0-9]+))?.?(?P<ua_build_version>[\d\._]*))$')

for ua_version in testvals:
	ver_match = ver_parse.search(ua_version)
	print '=' * 25
	print 'Version:', ua_version
	major_ver = 'unknown'
	sub_ver = 'unknown'
	build_ver = 'unknown'
	if not ver_match is None:
		print 'major:',ver_match.group('ua_major_version')
		print 'minor',ver_match.group('ua_minor_version')
		print 'build',ver_match.group('ua_build_version')
		groups = ver_match.groups()
		print groups
