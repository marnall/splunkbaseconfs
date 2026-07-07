import requests
import re
import HTMLParser
import urllib, htmlentitydefs, csv
import sys
import json
import urllib2


# http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


writer = csv.writer(sys.stdout)
data = list()
iterate = 0
writer.writerow(["title","description","url","img","location","date"])

request_headers = {
"Accept-Language": "en-US,en;q=0.5",
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
"Referer": "http://thewebsite.com",
"Connection": "keep-alive" 
}

request = urllib2.Request("http://www.splunk.com/en_us/about-us/events.html", headers=request_headers)
response = urllib2.urlopen(request)
page = response.read()
#r = requests.get("https://www.splunk.com/en_us/about-us/events.html")
h = HTMLParser.HTMLParser()

#page = r.content
#print page
#print "********************"

articles = re.findall('<section class="event.*?</section>', page, re.DOTALL)
for article in articles:
	#print article + "\n\n\n\n*****************\n\n"
	img = ""
	url = ""
	title = ""
	description = ""
	location = ""
	date = ""
	match = re.search(r"src=.(?P<img>[^\"]*)", article) 
	if match:
		#print "Got a match!"
		img = "https://www.splunk.com" + match.group('img')

	match = re.search(r"a href=\"(?P<url>[^\"]*).*?><h2>(?P<title>[^<]*)", article) 
	if match:
		#print "Got a match!"
		url = match.group('url')
		#print "URL: " + url + "\n"
		title = match.group('title')
		#print "Title: " + title + "\n"
	
	#match = re.search(r"h3>(?P<location>[^<]*)", article) 
	#if match:
	#	location = match.group('location')
	#	print "Location: " + location + "\n"

	match = re.search(r"<h3>\s*(?P<date>.*?201[5-9]).*?<h3>\s*(?P<location>.*?)\s*</h3>", article, re.DOTALL) 
	if match:
		location = match.group('location')
		#print "Location: " + location + "\n"
		date = match.group('date')
		#print "Date: " + date + "\n"
		
	#match = re.search(r":\s+(?P<date>[^:]*)\s+$", unicode(unescape(title)).encode("utf8")) 
	#if match:
	#	date = match.group('date')
	#	print "Date: " + date + "\n"
		
		
	#match = re.search(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)+,+(?P<date>.*?)$", date) 
	#if match:
	#	date = match.group('date')
	#	print "Date: " + date + "\n"

		
	match = re.search(r"<p>\s*<p>(?P<description>.*?)</p>\s*</p>", article) 
	if match:
		description = match.group('description')
		#print "Description: " + description + "\n"
		

	writer.writerow([unicode(unescape(title)).encode("utf8"), description, unicode(unescape(url)).encode("utf8"), unicode(unescape(img)).encode("utf8"), unicode(unescape(location)).encode("utf8"), date])
	
#	data.append(dict())
	#data[iterate]['title'] = unicode(unescape(title)).encode("utf8")
	#data[iterate]['description'] = description
	#data[iterate]['url'] = unicode(unescape(url)).encode("utf8")
	#data[iterate]['img'] = unicode(unescape(img)).encode("utf8")
	#data[iterate]['location'] = unicode(unescape(location)).encode("utf8")
	
	#data[iterate]['title'] = "Random Title Will be This Long" + str(iterate + 1)
	#data[iterate]['description'] = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. " + str(iterate + 1)
	#data[iterate]['url'] = "http://www.abc123.com/Ihaveplaces" + str(iterate + 1)
	#data[iterate]['img'] = "/content/images/ihaveimages"+ str(iterate + 1)
	#data[iterate]['location'] = "San Francisco, US"
#	iterate = iterate + 1

#print json.dumps(data)

