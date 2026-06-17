import sys,splunk.Intersplunk
import re

class AdFilter():
    def __init__(self):
        self.blacklist_domains = []
        self.blacklist_url_snippets = []
        self.blacklist_patterns = []
        self.blacklist_found = []
        self.whitelist_domains = []
        self.shortset = set() #the first three unique characters of everything we're looking for, which we can look over first
#        with open('../local/easylist_adservers.txt', 'r') as f:
        with open('../local/easylist.txt', 'r') as f:
            for line in f:
                if line.startswith('||'):
                    tick = line.find('^')
                    s = line[2:tick]
                    self.blacklist_domains.append( s )
                    self.shortset.add( s[0:3] )
                elif not re.match( "^(\!|\[|\#\~|\@)", line ):
                    self.blacklist_url_snippets.append( line )
                    self.shortset.add( line[0:3] )
        self.blacklist_patterns.append( re.compile('ad[s]?\d*\.') )
        self.blacklist_patterns.append( re.compile('/ads/') )
        self.blacklist_patterns.append( re.compile('analytics') )

#        with open('../local/easylist_adservers.txt', 'r') as f:
#            for line in f:
#                if line.startswith('||'):
#                    tick = line.find('^')
#                    self.res.append( line[2:tick] )

# ||ad-delivery.net^$third-party

    def shouldKeep(self, event):
#        return True

        for r in self.blacklist_found:
            if event.find(r) > -1:
                return False

        for p in self.blacklist_patterns:
            m = p.search(event)
            if m is not None and m.group(0) is not None:
                return False

        for r in self.whitelist_domains:
            if event.find(r) > -1:
                return True

        #too lazy to build a whole tree, let's just try the first 3 unique characters of the test strings
        shortfound = False
        for ss in self.shortset:
            if event.find(ss) > -1:
                shortfound = True
                break
        if shortfound is False:
            return True

        for current_list in [self.blacklist_domains , self.blacklist_url_snippets]:
            for r in current_list:
                if event.find(r) > -1:
                    self.blacklist_found.append(r)
                    return False

        domain = re.findall('\w://(.*?)/',event)[0]
        self.whitelist_domains.append( domain )
        return True

try:
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()

    field = argvals.get("field", None)
    if field is None:
        field = '_raw'
#        raise Exception("Must supply name of field in field=fieldName")

    newResults = []

    adFilter = AdFilter()

    for r in results:
#        if r.has_key(field) and adFilter.shouldKeep(r[field]):
        if adFilter.shouldKeep(r[field]):
            newResults.append(r)
#testing output...
#        else:
#            r['die'] = 'die'
#            newResults.append(r)

except:
    import traceback
    stack =  traceback.format_exc()
    newResults = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( newResults )

