'''
######################################################
#
# Splunk for Microsoft Exchange
# Email Reputation Check Data Definition
# 
# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# All Rights Reserved
#
######################################################
'''

'''
This data input is designed to check your reputation on-line.
'''
import os
import sys
import dns.resolver

try:
    from ConfigParser import ConfigParser
except:
    from configparser import ConfigParser

'''
List of DNSBL Servers to check
'''
dnsbl_list = [
        '0spam.fusionzero.com',
        'access.redhawk.org',
        'all.spamrats.com',
        'b.barracudacentral.org',
        'blackholes.five-ten-sg.com',
        'bl.blocklist.de',
        'bl.emailbasura.org',
        'bl.mailspike.org',
        'bl.score.senderscore.com',
        'bl.spamcannibal.org',
        'bl.spamcop.net',
        'bl.spameatingmonkey.net',
        'bogons.cymru.com',
        'cbl.abuseat.org',
        'cblplus.anti-spam.org.cn',
        'combined.njabl.org',
        'db.wpbl.info',
        'dnsbl-1.uceprotect.net',
        'dnsbl-2.uceprotect.net',
        'dnsbl-3.uceprotect.net',
        'dnsbl.ahbl.org',
        'dnsbl.dronebl.org',
        'dnsbl.inps.de',
        'dnsbl.justspam.org',
        'dnsbl.kempt.net',
        'dnsbl.solid.net',
        'dnsbl.sorbs.net',
        'dnsbl.tornevall.org',
        'dnsbl.webequipped.com',
        'dnsrbl.swinog.ch',
        'fnrbl.fast.net',
        'ips.backscatterer.org',
        'ix.dnsbl.manitu.net',
        'korea.services.net',
        'l2.apews.org',
        'list.blogspambl.com',
        'mail-abuse.blacklist.jippg.org',
        'psbl.surriel.com',
        'rbl.choon.net',
        'rbl.dns-servicios.com',
        'rbl.efnetrbl.org',
        'rbl.orbitrbl.com',
        'rbl.polarcomm.net',
        'singlebl.spamgrouper.com',
        'spam.abuse.ch',
        'spam.dnsbl.sorbs.net',
        'spam.pedantic.org',
        'spamguard.leadmon.net',
        'spamrbl.imp.ch',
        'spamsources.fabel.dk',
        'spamtrap.trblspam.com',
        'st.technovision.dk',
        'tor.dan.me.uk',
        'tor.dnsbl.sectoor.de',
        'truncate.gbudb.net',
        'ubl.unsubscore.com',
        'virbl.dnsbl.bit.nl' ]


'''
Read a configuration file from our area
'''
def readConf(confName):
    app_dir = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps')
    app_path = os.path.join(app_dir, 'TA-SMTP-Reputation')
    def_file = os.path.join(app_path, 'default', 'reputation.conf')
    loc_file = os.path.join(app_path, 'local', 'reputation.conf')

    cfg = ConfigParser()
    cfg.read(def_file)
    cfg.read(loc_file)

    return cfg

'''
Look up the reputation of a specific IP in Senderbase
'''
def reputation_lookup(ip, dnsbl):
    mrl = ip.split('.')
    mnm = '%s.%s.%s.%s.%s' % (mrl[3], mrl[2], mrl[1], mrl[0], dnsbl)
    try:
        answers = dns.resolver.resolve(mnm, 'A')
        print('ip=%s dnsbl=%s reputation=Poor error="Listed" response="%s"' % (ip, dnsbl, answers[0].address))
        return 'Poor'
    except dns.resolver.Timeout:
        print('ip=%s dnsbl=%s reputation=Neutral error="Timeout"' % (ip, dnsbl))
        return 'Neutral'
    except dns.resolver.NoAnswer:
        print('ip=%s dnsbl=%s reputation=Neutral error="NoAnswer"' % (ip, dnsbl))
        return 'Neutral'
    except dns.resolver.NoNameservers:
        print('ip=%s dnsbl=%s reputation=Neutral error="No Nameservers"' % (ip, dnsbl))
        return 'Neutral'
    except dns.resolver.NXDOMAIN:
        print('ip=%s dnsbl=%s reputation=Good' % (ip, dnsbl))
        return 'Good'
    return 'Neutral'

def main():
    confInfo = readConf("reputation")
    opt_iplist = confInfo.get("mailservers", "iplist").strip()
    ip_list = []
    
    # If there are no IP addresses, then quit
    if len(opt_iplist) == 0:
        return
    # If there is more than one IP address, add all of them, otherwise
    # just add whatever is there.
    if (opt_iplist.find(';') == -1):
        ip_list.append(opt_iplist)
    else:
        ip_list.extend(opt_iplist.split(';'))

    # Get the reputation of each IP in turn
    repDict = { "Poor":0, "Other":0, "Neutral":0, "Good":0 }
    for ip in ip_list:
        for dnsbl in dnsbl_list:
            rep = reputation_lookup(ip.strip(), dnsbl)
            if (rep == 'Good' or rep == 'Poor' or rep == 'Neutral'):
                repDict[rep] += 1
            else:
                repDict['Other'] += 1

    # Our overall reputation is as follows:
    #   Any individual Poor -> overall Poor
    #   All individual Neutral -> overall Neutral
    #   All individual Good -> overall Good
    #   Any other combination -> overall Mixed
    expected_cnt = len(ip_list) * len(dnsbl_list);
    if (repDict["Poor"] > 0):
        our_reputation = "Poor"
        our_rangemap = "critical"
    elif (repDict["Neutral"] == expected_cnt):
        our_reputation = "Neutral"
        our_rangemap = "elevated"
    elif (repDict["Good"] == expected_cnt):
        our_reputation = "Good"
        our_rangemap = "low"
    else:
        our_reputation = "Mixed"
        our_rangemap = "elevated"
            
    print("ip=overview reputation={0} rangemap={1}".format(our_reputation,our_rangemap))

if __name__ == '__main__':
    main()
