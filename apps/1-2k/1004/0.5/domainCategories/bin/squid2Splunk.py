import os
import os.path
import sys
import urllib2
import tempfile
import csv
import re
import tarfile

# URL for URL Blacklist is:
# http://urlblacklist.com/
# Download URL is:
# http://urlblacklist.com/cgi-bin/commercialdownload.pl?type=download&file=bigblacklist

def downloadBlacklist(downloadURL, targetFile):
    """
    Download the .gz file from the given URL. Returns the path to the downloaded file.
    """
    req = urllib2.Request(downloadURL)
    try:
        urlHandle = urllib2.urlopen(req)
        print "Downloading from " + downloadURL
        # contents = urlHandle.read()
        #print contents
        #targetFile.write(contents)
        targetFile.write(urlHandle.read())
        print "File written to " + targetFile.name
    except urllib2.HTTPError, e:
        print "HTTP Error:",e.code , url
    except urllib2.URLError, e:
        print "URL Error:",e.reason , url

def getDomainFiles(tarballPath, outputFile, vendorName):
    """
    Reads the domain files from the .tar.gz file and creates the lookup file.
    """
    blackListArch = tarfile.open(fileobj=tarballPath, mode='r:gz')
    fileMembers = blackListArch.getmembers()
    # for item in fileMembers:
    #    print item.name
    totalDomains = 0
    csvFile = csv.writer(open(outputFile, 'w'))
    csvFile.writerow(['category_domain','category', 'vendor'])
    for member in fileMembers:
        if member.name.endswith('/domains'):
            print 'Reading ' + member.name + "... ",
            domains = blackListArch.extractfile(member)
            thisDomains = 0
            curCat = os.path.split(os.path.split(member.name)[0])[1]
            for domain in domains:
                thisDomains = thisDomains + 1
                csvFile.writerow([domain.strip(),curCat,vendorName])
            domains.close()
            print 'Read', thisDomains, 'domains.'
            totalDomains = totalDomains + thisDomains
    print 'Read', totalDomains, 'total.'

def getLookupDirectory():
    """
    Returns the path to the lookup directory.
    """
    pathname = os.path.dirname(sys.argv[0])
    pathname = os.path.abspath(pathname)
    pathname = os.path.join(pathname, '../lookups/')
    return os.path.normpath(pathname)

def createCategories(tarballPath, outputFile):
    """
    Creates a categories CSV based on the contents of CATEGORIES file in the tarball.
    """
    blackListArch = tarfile.open(fileobj=tarballPath, mode='r:gz')
    print 'Creating category description lookup at ' + outputFile
    # Make sure it exists
    catFileName = 'blacklists/CATEGORIES'
    if catFileName in blackListArch.getnames():
        catDesc = re.compile(r"^(?P<category>[\w_-]+\s)-\s(?P<description>.*)$")
        catFile = blackListArch.extractfile(catFileName)
        csvFile = csv.writer(open(outputFile, 'w'))
        csvFile.writerow(['category','category_description'])
        for line in catFile:
            match = catDesc.search(line)
            if match:
                curCat = match.group('category')
                curDesc = match.group('description')
                csvFile.writerow([curCat,curDesc])
        catFile.close()
    print 'Category description lookup written.'

if __name__ == '__main__':
    # The real thing (isn't that a Pepsi slogan?)
    blackListURL = 'http://urlblacklist.com/cgi-bin/commercialdownload.pl?type=download&file=bigblacklist'

    # Small copy for testing parsing. NOTE: does not include CATEGORIES file
    # blackListURL = 'http://urlblacklist.com/cgi-bin/commercialdownload.pl?type=download&file=smalltestlist'

    # Local copy for testing
    # blackListURL = 'http://localhost/bigblacklist.tar.gz'
    targetLookupDir = getLookupDirectory()
    targetBlacklistFile = os.path.join(targetLookupDir, 'domaincategories.csv')
    targetCategoryFile = os.path.join(targetLookupDir, 'categorydescriptions.csv')

    targetFile = tempfile.NamedTemporaryFile(mode='w+b')
    downloadBlacklist(blackListURL, targetFile)
    targetFile.seek(0)
    getDomainFiles(targetFile, targetBlacklistFile, 'URLBlacklist')
    targetFile.seek(0)
    createCategories(targetFile, targetCategoryFile)
    targetFile.close()
