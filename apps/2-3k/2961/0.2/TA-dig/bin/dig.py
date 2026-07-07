#import subprocess
#p = subprocess.Popen(['dig', 'axfr \| tr [:blank:] \',\'  \| grep \",A,\"'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#out, err = p.communicate()
#print out
# Dominique Vocat, 10.9.2015
# uses dnspython.org - http://www.dnspython.org/docs/1.12.0/
# Version 0.1: Basic gathering of zone transfer infos
# Version 0.2: resolve required information
# Version 0.3: split the results and prepend a header

import splunk.Intersplunk #,ConfigParser
#from ConfigParser import SafeConfigParser
from optparse import OptionParser
import re 
import dns.query
import dns.resolver
import dns.zone

#domain = 'helvetia.fr'

#named options
try:
    #logger.info( "getting Splunk options..." )
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    domain = options.get('domain','helvetia.fr')

except Exception as e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

soa_answer = dns.resolver.query(domain, 'SOA')
master_answer = dns.resolver.query(soa_answer[0].mname, 'A')

z = dns.zone.from_xfr(dns.query.xfr(master_answer[0].address, domain))
names = z.nodes.keys()
names.sort()
print ("dnsname,dnsttl,direction,dnsrecordtype,value")
for n in names:
#        print z[n].to_text(n)
        print (re.sub('\s+', ',', z[n].to_text(n)))
