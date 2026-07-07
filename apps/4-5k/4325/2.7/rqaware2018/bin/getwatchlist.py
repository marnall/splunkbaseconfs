import os
import sys
import requests
import csv
import traceback
from ConfigParser import SafeConfigParser
from urlparse import urlparse

# Find the best implementation of StringIO available on this platform
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

# Try to import the Splunk SDK modules for better error reporting
try:
    import splunk.Intersplunk
    SPLUNKIMPORT = True
except:
    SPLUNKIMPORT = False

####################
# HELPER FUNCTIONS #
####################

def formatValue(value):
    """
    Some of the blacklists use bad characters such as ascii 160
    which messes up the display back in splunkweb
    """
    retVal = ''
    retVal = value.strip()
    retVal = retVal.replace(chr(160), '')
    return retVal

def getDefaultConfPath():
    """
    Returns the path to the default config file.
    """
    pathname = os.path.dirname(sys.argv[0])
    pathname = os.path.abspath(pathname)
    pathname = os.path.join(pathname, '../default/getwatchlist.conf')
    return os.path.normpath(pathname)

def getLocalConfPath():
    """
    Returns the path to the local config file.
    """
    pathname = os.path.dirname(sys.argv[0])
    pathname = os.path.abspath(pathname)
    pathname = os.path.join(pathname, '../local/getwatchlist.conf')
    return os.path.normpath(pathname)

def isSavedProfile(profileName):
    """
    Checks the getwatchlist.conf for the profile name given.
    Returns True if the profile is found.
    """
    profileList = getSavedProfileNames()
    if profileName in profileList:
        return True
    else:
        return False

def isDefaultProfile(profileName):
    """
    Checks if the profile is in the default file
    """
    profileNames = getDefaultSavedProfileNames()
    for profile in profileNames:
        if profile.lower() == profileName.lower():
            return True

    return False

def isLocalProfile(profileName):
    """
    Checks if the profile is in the local file
    """
    profileNames = getLocalSavedProfileNames()

    for profile in profileNames:
        if profile.lower() == profileName.lower():
            return True

    return False

def getDefaultSavedProfileNames():
    """
    Reads in the names of the DEFAULT saved profiles from the getwatchlist.conf
    files in default and local and returns them as a list.
    """
    parser = SafeConfigParser()
    parser.optionxform = str
    parser.read(getDefaultConfPath())
    profileNames = parser.sections()

    return profileNames

def getLocalSavedProfileNames():
    """
    Reads in the names of the LOCAL saved profiles from the getwatchlist.conf
    files in default and local and returns them as a list.
    """
    parser = SafeConfigParser()
    parser.optionxform = str
    parser.read(getLocalConfPath())
    profileNames = parser.sections()

    return profileNames

def getSavedProfileNames():
    """
    Reads in the names of the saved profiles from the getwatchlist.conf
    files in default and local and returns them as a list.
    """
    profileNames = []

    # First the defaults
    parser = SafeConfigParser()
    parser.optionxform = str
    parser.read(getDefaultConfPath())
    profileNames = parser.sections()

    # Now the locals
    parser = SafeConfigParser()
    parser.optionxform = str
    parser.read(getLocalConfPath())
    localProfileNames = parser.sections()

    # Now create one list
    for profile in localProfileNames:
        if not profile in profileNames:
            profileNames.append(profile)

    return profileNames

def getRealProfileName(givenProfileName, allProfiles, fromLocal=False):
    """
    To support case mixing, this function will return the case sensitive
    version of the given profile name. Returns None if the profile is
    not found.
    """
    if fromLocal:
        allProfiles = getLocalSavedProfileNames()
    else:
        allProfiles = getDefaultSavedProfileNames()
    lowProfileName = givenProfileName.lower()
    for profile in allProfiles:
        if profile.lower() == lowProfileName:
            return profile
    return None

def filterComments(fileBuffer, comment):
    """
    Iterates through the given file-like object and returns a version
    without commented lines (lines witht the comment character at the start).
    Also removes empty lines.
    """
    csvbuffer = ''
    for line in fileBuffer:
        if line.startswith(comment) or not line.strip():
            pass
        else:
            csvbuffer = csvbuffer + line
    return csvbuffer

######################
# SETTINGS FUNCTIONS #
######################

def getDefaultSettings():
    """
    Returns a dictionary with the default settings.
    """
    settings = {}

    # set some defaults
    settings['url']=''
    settings['delimiter']='\t'
    settings['comment']='#'
    settings['relevantFieldName']='ip_address'
    settings['relevantFieldCol']=0
    settings['categoryCol']=-1
    settings['referenceCol']=-1
    settings['dateCol']=-1
    settings['authUser'] = ''
    settings['authPass'] = ''
    settings['ignoreFirstLine'] = False
    settings['proxyHost'] = ''
    settings['proxyPort'] = '8080'
    settings['customFields'] = {}
    settings['addCols'] = {}

    return settings

def getSavedProfile(profileName):
    """
    Reads both the local and default profiles and resolves
    any differences before returning the profile settings dict.
    """
    defaultSettings = getDefaultSettings()
    settings = getExactSavedProfile(profileName)
    localSettings = getExactSavedProfile(profileName, True)

    for key in settings.keys():
        if key == 'customFields':
            if localSettings[key] != {}:
                settings[key] = localSettings[key]
        elif key == 'addCols':
            if localSettings[key] != {}:
                settings[key] = localSettings[key]
        else:
            if localSettings[key] != defaultSettings[key]:
                settings[key] = localSettings[key]

    if settings['url'] == '':
        settings['url'] = profileName

    return settings

def getExactSavedProfile(profileName, fromLocal=False):
    """
    Reads a single profile from the getwatchlist.conf in the default
    or local directories and returns them in a dictionary. If the profile
    is not found, it returns the default settings.
    """

    parser = SafeConfigParser()
    parser.optionxform = str
    if fromLocal:
        parser.read(getLocalConfPath())
    else:
        parser.read(getDefaultConfPath())

    sections = parser.sections()

    settings = getDefaultSettings()

    # We start with the globals. These can be overridden with local settings
    # in the config for the profile. The globals are just nice to have.
    realGlobalName = getRealProfileName('globals', sections, fromLocal)
    if realGlobalName is not None:
        for key,value in parser.items(realGlobalName):
            lowkey = key.lower()
            if lowkey == 'proxyhost':
                settings['proxyHost'] = value
            elif lowkey == 'proxyport':
                settings['proxyPort'] = str(value)

    # The profile name should be a URL if the profile doesn't exist
    # Otherwise, it will be overwritten by the url in the profile
    # THIS CHANGED after we have the local and default profiles
    # settings['url'] = profileName

    realProfileName = getRealProfileName(profileName, sections, fromLocal)
    # if the profile isn't in the file return defaults
    if not realProfileName:
        return settings

    # now grab all of the settings at once and assign
    for key,value in parser.items(realProfileName):
        lowKey = key.lower()
        # strip any quotes from our value
        value = value.replace('\'', '')
        value = value.replace('"', '')
        value = value.strip()
        if lowKey == 'url':
            settings['url'] = value
        elif lowKey == 'delimiter':
            settings['delimiter'] = value
        elif lowKey == 'comment':
            settings['comment'] = value
        elif lowKey == 'relevantfieldname':
            settings['relevantFieldName'] = value
        elif lowKey == 'relevantfieldcol':
            settings['relevantFieldCol'] = int(value) - 1
        elif lowKey == 'categorycol':
            settings['categoryCol'] = int(value) - 1
        elif lowKey == 'referencecol':
            settings['referenceCol'] = int(value) - 1
        elif lowKey == 'datecol':
            settings['dateCol'] = int(value) - 1
        elif lowKey == 'authuser':
            settings['authUser'] = value
        elif lowKey == 'authpass':
            settings['authPass'] = value
        elif lowKey == 'ignorefirstline':
            settings['ignoreFirstLine'] = bool(value)
        elif lowKey == 'proxyhost':
            settings['proxyHost'] = value
        elif lowKey == 'proxyport':
            settings['proxyPort'] = str(value)
        else:
            if lowKey.isdigit():
                settings['addCols'][int(key)] = value
            else:
                settings['customFields'][key] = value

    return settings

def getSettings(args):
    """
    Parses the arguments passed from Splunk via the command line, then
    calls checks for a saved profile. Returns a dictionary with the settings
    Notice that the column numbers are decremented to resolve the difference
    between the human idea of starting at one, and the Python start at 0.
    """
    # the first arg should be the URL or profile name
    url = args.pop(0)

    # check for a saved profile. Function will return defaults if the
    # profile doesn't exist
    settings = getSavedProfile(url)
    # The rest should be in the key=value form
    for argset in args:
        key,value = argset.split('=')
        # strip any quotes from our value
        value = value.replace('\'', '')
        value = value.replace('"', '')
        value = value.strip()
        lowkey = key.lower()
        if lowkey == 'delimiter':
            settings['delimiter'] = value
        elif lowkey == 'url':
            settings['url'] = value
        elif lowkey == 'comment':
            settings['comment'] = value
        elif lowkey == 'relevantfieldname':
            settings['relevantFieldName'] = value
        elif lowkey == 'relevantfieldcol':
            settings['relevantFieldCol'] = int(value) - 1
        elif lowkey == 'categorycol':
            settings['categoryCol'] = int(value) - 1
        elif lowkey == 'referencecol':
            settings['referenceCol'] = int(value) - 1
        elif lowkey == 'datecol':
            settings['dateCol'] = int(value) - 1
        elif lowkey == 'authuser':
            settings['authUser'] = value
        elif lowkey == 'authpass':
            settings['authPass'] = value
        elif lowkey == 'ignorefirstline':
            settings['ignoreFirstLine'] = bool(value)
        elif lowkey == 'proxyhost':
            settings['proxyHost'] = value
        elif lowkey == 'proxyport':
            settings['proxyPort'] = str(value)
        else:
            if lowkey.isdigit():
                settings['addCols'][int(key)] = value
            else:
                settings['customFields'][key] = value

    return settings

###################
# FETCH FUNCTIONS #
###################



def fetchHTTP(settings):
    """
    Fetches the requested watchlist using HTTP or HTTPS and returns the
    contents, filtered using the settings.
    """
    url = settings['url']
    delimiter = settings['delimiter']
    comment = settings['comment']
    authUser = settings['authUser']
    authPass = settings['authPass']
    proxyHost = settings['proxyHost']
    proxyPort = settings['proxyPort']
    
    
    # if the username or password is not empty, we will use an auth handler
    if authUser != '' or authPass != '':
        request = requests.get(url, auth=(authUser, authPass))
    else:
    	request = requests.get(url)
    

    if proxyHost != '':
        proxyHost = proxyHost + ':' + proxyPort
        request.set_proxy(proxyHost, 'http')
        # request.set_proxy(proxyHost, urlparse(url).scheme)

    
    return filterComments(request, comment)

def fetchWatchList(settings):
    """
    Checks the protocol on the URL given in the settings and calls
    the correct fetch function to return the filtered contents.
    """
    urlScheme = urlparse(settings['url']).scheme
    if urlScheme == 'https':
        return fetchHTTP(settings)
    
    else:
        if urlScheme == '':
            raise ValueError('Invalid URL or profile name not found')
        else:
            raise ValueError('Unsupported protocol: %s' % urlScheme)

######################
#  OUTPUT FUNCTIONS  #
######################
def outputWatchlist(csvbuffer, settings):
    """
    Prints the fetched watchlist to stdout as a CSV (comma delimited).
    Uses the passed settings for formatting and column names.
    """
    delimiter = settings['delimiter']
    ignoreFirstLine = settings['ignoreFirstLine']
    relevantFieldName = settings['relevantFieldName']
    relevantFieldCol = settings['relevantFieldCol']
    categoryCol = settings['categoryCol']
    referenceCol = settings['referenceCol']
    dateCol = settings['dateCol']
    customFields = settings['customFields']
    addCols = settings['addCols']

    # StringIO buffer to fake a file-like object
    csvFileObject = StringIO(csvbuffer)

    # using the passed parameters, a new csv dialect is created
    # and then a reader is created using the new dialect
    csv.register_dialect('passed_params', delimiter=delimiter, skipinitialspace=1)
    csvReader = csv.reader(csvFileObject, csv.get_dialect('passed_params'))

    # create a fieldname list if the fields exist
    fieldList = []
    fieldList.append(relevantFieldName)
    if categoryCol >= 0:
        fieldList.append('category')
    if referenceCol >= 0:
        fieldList.append('reference')
    if dateCol >= 0:
        fieldList.append('date')

    # add any custom fields, keep the keys in a list, to remember the order
    customKeys = []
    for k,v in customFields.iteritems():
        customKeys.append(k)
        fieldList.append(k)

    # add any additional cols
    addKeys = []
    for k,v in addCols.iteritems():
        addKeys.append(k)
        fieldList.append(v)

    # create a csv writer to write to a StringIO file handle
    csvOutput = csv.writer(sys.stdout)

    # write out the header
    csvOutput.writerow(tuple(fieldList))

    # use our reader to go through the downloaded content
    allResults = []
    rowCount = 0
    for row in csvReader:
        if rowCount == 0 and ignoreFirstLine:
            pass
        else:
            rowHolder = []
            rowHolder.append(formatValue(row[relevantFieldCol]))

            if categoryCol >= 0:
                rowHolder.append(formatValue(row[categoryCol]))
            if referenceCol >= 0:
                rowHolder.append(formatValue(row[referenceCol]))
            if dateCol >= 0:
                rowHolder.append(formatValue(row[dateCol]))

            # Now for custom fields
            for cust in customKeys:
                rowHolder.append(formatValue(customFields[cust]))

            # and additional cols
            for addCol in addKeys:
                rowHolder.append(formatValue(row[int(addCol)]))

            # output to the CSV writer, which is using sysout
            csvOutput.writerow(tuple(rowHolder))
        rowCount = rowCount + 1

##############
# MAIN ENTRY #
##############

if __name__ == '__main__':
    # this is the start of execution. A quick check of the arg count is performed
    # then the stripped sys.argv is passed to parseArgsAndRun
    if len(sys.argv) < 2:
        errorString = "Not enough arguments passed. At least a URL or profile name is required."
        if SPLUNKIMPORT:
            results = splunk.Intersplunk.generateErrorResults(errorString)
            splunk.Intersplunk.outputResults(results)
            sys.exit()
        else:
            print errorString
            sys.exit()

    # Get the settings
    try:
        settings = getSettings(sys.argv[1:])
    except Exception, err:
        errorString = "Error getting settings: " + str(err)
        if SPLUNKIMPORT:
            results = splunk.Intersplunk.generateErrorResults(errorString)
            splunk.Intersplunk.outputResults(results)
            sys.exit()
        else:
            print errorString
            traceback.print_tb(sys.exc_info()[2])
            sys.exit()

    # Now that we have our settings, let's get the watchlist
    try:
        watchlistContent = fetchWatchList(settings)
    except Exception, err:
        errorString = "Error fetching watch list: " + str(err)
        if SPLUNKIMPORT:
            results = splunk.Intersplunk.generateErrorResults(errorString)
            splunk.Intersplunk.outputResults(results)
            sys.exit()
        else:
            print errorString
            traceback.print_tb(sys.exc_info()[2])
            sys.exit()

    # Now that we have the content, print it out in CSV
    try:
        outputWatchlist(watchlistContent, settings)
    except Exception, err:
        errorString = "Error outputting watch list:" + str(err)
        if SPLUNKIMPORT:
            results = splunk.Intersplunk.generateErrorResults(errorString)
            splunk.Intersplunk.outputResults(results)
            sys.exit()
        else:
            print errorString
            traceback.print_tb(sys.exc_info()[2])
            sys.exit()
