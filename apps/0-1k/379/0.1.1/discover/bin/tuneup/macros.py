import re,time
import splunk.searchhelp.next as next
import splunk.searchhelp.utils as utils
import splunk.mining.FieldLearning as fl


knownSearchLanguageTerms = set([
'abs', 'abstract', 'accum', 'action', 'add', 'addinfo', 'addtime', 'addtotals', 'af', 'agg', 'allnum', 'allowempty', 'allrequired', 'and', 'annotate', 'anomalies', 'anomalousvalue', 'append', 'appendcols', 'as', 'associate', 'attr', 'attribute', 'attrn', 'audit', 'auto', 'autoregress', 'avg', 'bcc', 'bins', 'blacklist', 'blacklistthreshold', 'bottom', 'bucket', 'buffer_span', 'by', 'c', 'case', 'cb', 'cc', 'cfield', 'chart', 'cidrmatch', 'cityblock', 'classfield', 'clean_keys', 'cluster', 'coalesce', 'cocur', 'col', 'collapse', 'collect', 'commands', 'concurrency', 'connected', 'consecutive', 'cont', 'context', 'contingency', 'convert', 'copyattrs', 'correlate', 'cos', 'cosine', 'count', 'counterexamples', 'countfield', 'crawl', 'createinapp', 'cs', 'csv', 'ctime', 'current', 'd', 'day', 'days', 'daysago', 'dbinspect', 'dc', 'dd', 'dedup', 'default', 'delete', 'delim', 'delims', 'delta', 'desc', 'dest', 'dictionary', 'diff', 'discard', 'distinct-count', 'distinct_count', 'ds', 'dt', 'dur2sec', 'duration', 'earlier', 'ema', 'end', 'enddaysago', 'endhoursago', 'endminutesago', 'endmonthsago', 'endswith', 'endtime', 'erex', 'eval', 'eventcount', 'events', 'eventstats', 'eventtype', 'eventtypetag', 'exact', 'examples', 'exp', 'extract', 'false', 'field', 'fieldname', 'fields', 'file', 'fillnull', 'filter', 'findtypes', 'first', 'floor', 'folderize', 'forceheader', 'form', 'format', 'from', 'fromfield', 'gentimes', 'global', 'graceful', 'h', 'head', 'header', 'hh', 'high', 'highest', 'highlight', 'hilite', 'host', 'hosts', 'hosttag', 'hour', 'hours', 'hoursago', 'hr', 'hrs', 'html', 'iconify', 'if', 'ifnull', 'improv', 'in', 'increment', 'index', 'inline', 'inner', 'input', 'inputcsv', 'inputlookup', 'intersect', 'ip', 'iplocation', 'iqr', 'isbool', 'isint', 'isnotnull', 'isnull', 'isnum', 'isstr', 'join', 'k', 'keepempty', 'keepevents', 'keepevicted', 'keeplast', 'keepsingle', 'kmeans', 'kvform', 'l1', 'l1norm', 'l2', 'l2norm', 'label', 'labelfield', 'labelonly', 'last', 'left', 'len', 'like', 'limit', 'list', 'ln', 'loadjob', 'local', 'localize', 'localop', 'log', 'logchange', 'lookup', 'low', 'lower', 'lowest', 'ltrim', 'm', 'makecontinuous', 'makemv', 'map', 'marker', 'match', 'max', 'max_buffer_size', 'max_match', 'max_time', 'maxchars', 'maxcols', 'maxevents', 'maxfolders', 'maxinputs', 'maxiters', 'maxlen', 'maxlines', 'maxopenevents', 'maxopentxn', 'maxout', 'maxpause', 'maxresolution', 'maxrows', 'maxsearches', 'maxspan', 'maxterms', 'maxtime', 'maxtrainers', 'maxvalues', 'md5', 'mean', 'median', 'memk', 'metadata', 'min', 'mincolcover', 'minfolders', 'minrowcover', 'mins', 'minute', 'minutes', 'minutesago', 'mktime', 'mm', 'mode', 'mon', 'month', 'months', 'monthsago', 'ms', 'mstime', 'multikv', 'multitable', 'mv_add', 'mvappend', 'mvcombine', 'mvcount', 'mvexpand', 'mvfilter', 'mvindex', 'mvjoin', 'mvlist', 'name', 'name-terms', 'ngramset', 'noheader', 'nomv', 'none', 'normalize', 'nosubstitution', 'not', 'notcovered', 'notin', 'now', 'null', 'nullif', 'nullstr', 'num', 'optimize', 'or', 'otherstr', 'outer', 'outfield', 'outlier', 'output', 'outputcsv', 'outputlookup', 'outputtext', 'overlap', 'override', 'overwrite', 'p', 'param', 'partial', 'perc', 'percentfield', 'percint', 'perl', 'pi', 'position1', 'position2', 'pow', 'prefix', 'priority', 'private-terms', 'pthresh', 'public-terms', 'python', 'random', 'range', 'rangemap', 'rare', 'raw', 'regex', 'relative_time', 'relevancy', 'reload', 'remove', 'rename', 'replace', 'reps', 'rescan', 'reverse', 'rex', 'rm', 'rmcomma', 'rmorig', 'rmunit', 'roll', 'round', 'row', 'rtorder', 'rtrim', 's', 'savedsearch', 'savedsplunk', 'script', 'scrub', 'search', 'searchmatch', 'searchtimespandays', 'searchtimespanhours', 'searchtimespanminutes', 'searchtimespanmonths', 'sec', 'second', 'seconds', 'secs', 'sed', 'segment', 'selfjoin', 'sendemail', 'sep', 'server', 'set', 'setsv', 'shape', 'showcount', 'showlabel', 'showperc', 'sichart', 'sid', 'singlefile', 'sirare', 'sistats', 'sitimechart', 'sitop', 'size', 'sleep', 'sma', 'sort', 'sortby', 'source', 'sources', 'sourcetype', 'sourcetypes', 'span', 'split', 'spool', 'sq', 'sqeuclidean', 'sqrt', 'ss', 'start', 'startdaysago', 'starthoursago', 'startminutesago', 'startmonthsago', 'startswith', 'starttime', 'starttimeu', 'stats', 'stdev', 'stdevp', 'str', 'strcat', 'streamstats', 'strftime', 'strptime', 'substr', 'sum', 'summary', 'sumsq', 'supcnt', 'supfreq', 'sync', 't', 'table', 'tail', 'termlist', 'termset', 'testmode', 'text', 'tf', 'threshold', 'time', 'timeafter', 'timebefore', 'timechart', 'timeconfig', 'timeformat', 'timeout', 'to', 'tokenizer', 'tol', 'top', 'tostring', 'totalstr', 'transaction', 'transform', 'trendline', 'trim', 'true', 'type', 'typeahead', 'typeof', 'typer', 'union', 'uniq', 'untable', 'upper', 'urldecode', 'us', 'uselower', 'usenull', 'useother', 'useraw', 'usetime', 'usetotal', 'usexml', 'validate', 'value', 'values', 'var', 'varp', 'where', 'window', 'with', 'wma', 'xmlkv', 'xmlunescape', 'xor', 'xpath', 'xyseries', 'yy'
])


def normalize(search):
    norm = search.strip() # lower()
    norm = re.sub("[ ]+", " ", norm)
    return norm



def regexify(macroDef):
    macroDef = fl.safeRegexLiteral(macroDef)
    macroDef = re.sub("[\\\\][$][a-zA-Z0-9_-]+[\\\\][$]", ".*", macroDef)
    #safeDef = "(?i)" + macroDef
    #print "MACRODEF: %s\nSAFEDEF: %s" % (macroDef, safeDef)
    return re.compile(macroDef)


def subsumedByMacro(search, knownMacros):
    for regex, macro in knownMacros:
        #print "MACRO: ", macro
        #print "SEARCH:", search
        if re.search(regex, search): ############!! changed from match.  shouldn't be necessary
            #print macro, "\n", search,"\n\n"
            return macro
    return None


def suggestMacros(user, sessionKey=None, namespace=None, maxsearches=1000, mincount=1):

    # get set of known DEFINITION values from macros.conf
    knownMacros = set()
    macrosStanzas = utils.getStanzas("macros", sessionKey, namespace)
    for name in macrosStanzas:
        for attr, val in macrosStanzas[name].items():
            if attr.startswith("definition"):
                knownMacros.add((regexify(val), val))

    learnedMacros = set()    
    # go over user entered searches and saved searches
    dummy, searches = next.getPastSearches(user, sessionKey, namespace)
    #print "%s searches" % len(searches)
    savedsearches = utils.getStanzas("savedsearches", sessionKey, namespace)
    searches.extend(savedsearches)
    nonmatchedSearches = set()
    searches.sort(lambda x, y: len(y) - len(x))
    # get list of searches that don't match exising macros
    for search in searches[:maxsearches]:
        matched = False
        if None == subsumedByMacro(search, learnedMacros):        
            nonmatchedSearches.add(normalize(search))
    nonmatchedSearches = list(nonmatchedSearches)
    sLen = len(nonmatchedSearches)
    macros = set()
    for i1 in range(0, sLen):
        s1 = nonmatchedSearches[i1]
        if None != subsumedByMacro(s1, learnedMacros):
            continue
        for i2 in range(i1+1, sLen):
            s2 = nonmatchedSearches[i2]
            #if None != subsumedByMacro(s2, learnedMacros):
            #     print "S2"
            #     continue            
            macro = getMacro(s1, s2)
            if macro != None and macro not in knownMacros:
                macros.add(macro)
                learnedMacros.add((regexify(macro), macro))
                break
    #print "done generating macros.  %s macros." % len(macros)
    #print "learned on the last %s searches." % maxsearches
    #print "searches count %s.  unique count %s" % (len(searches), len(set(searches)))
    macrocounts = {}
    #print len(macros), len(learnedMacros)
    #for m in macros:
    #    print m
    #for m in learnedMacros:
    #    print m
    for i, search in enumerate(searches):
        search = normalize(search)
        #print "search:", search,"\nnorm:  ", norm,"\n"

        for regex, macro in learnedMacros:
            if re.search(regex, search): 
                macrocounts[macro] = macrocounts.get(macro,0) + 1
                #print macro

    #print macrocounts
    macrosAndCounts = macrocounts.items()
    macrosAndCounts.sort(lambda x, y: y[1] - x[1])
    # return most common macros, that have a count >= mincount
    return [(macro,count) for macro, count in macrosAndCounts if count >= mincount]

def uneven(s):
    for ch in '"()[]{}':
        if s.count(ch) % 2 == 1:
            return True
    return False
    
def getMacro(s1, s2):
    MIN_COMMANDS = 2
    MIN_TOKENS = 10
    MIN_LEN = 140
    
    # ignore dups or not enough commands
    if s1 == s2 or s1[1:].count('|') < MIN_COMMANDS-1 or s2[1:].count('|') < MIN_COMMANDS-1:
        return None
    # simple case of one being a complete substring of the other
    if s2.startswith(s1):
        #print "s1"
        return s1 + " $suffix$"
    if s2.endswith(s1):
        #print "s2"
        return "$prefix$ " + s1
    if s1.startswith(s2):
        #print "s3"
        return s2 + " $suffix$"
    if s1.endswith(s2):
        #print "s4"
        return "$prefix$ " + s2
    if s1 in s2:
        return "$prefix$ " + s1 + " $suffix$"
    if s2 in s1:
        return "$prefix$ " + s2 + " $suffix$"

    c1 = s1.split('|')
    c2 = s2.split('|')
    #prefixLen = 0
    # if at least 2 commands at start are in common
    for i in range(len(c1)):
        if len(c2) == i:
            break
        #prefixLen += len(c1[i])
        if c2[i] != c1[i]:
            if i >= MIN_COMMANDS: # or prefixLen >= MIN_LEN:
                
                #print "s5", '|'.join(c1[:i]) + " $suffix$"
                return '|'.join(c1[:i]) + " $suffix$"
    # if at least 2 commands at end are in common
    #suffixLen = 0
    for i in range(1, len(c1)+1):
        if i > len(c2):
            break
        #suffixLen += len(c1[-1 * i])
        if c2[-1 * i] != c1[-1 * i]:
            if i > MIN_COMMANDS: # or suffixLen >= MIN_LEN:
                #print "s6", "$prefix$ " + '|'.join(c1[-1 * i+1:])            
                return "$prefix$ " + '|'.join(c1[-1 * i+1:])            
    
    t1 = set(s1.split())
    t2 = set(s2.split())
    if len(t1) < MIN_TOKENS or len(t2) < MIN_TOKENS:
        return None
    d1 = t1.difference(t2)
    d2 = t2.difference(t1)
    MAX_DIFF = len(t1) / 5
    #print MAX_DIFF
    #print len(d1), len(d2)

    
    if len(d1) == len(d2) and len(d1) <= MAX_DIFF:
        if len(d1) == 0:
            return None
            print "\t", s1
            print "\t", s2
            print "\t", d1
            print "\t", d2
            
        for i, d in enumerate(d1):
            # don't allow variables for common search language commands and args
            if d.lower() in knownSearchLanguageTerms:
                return None
            # don't allow uneven quotes/parens in variables
            if uneven(d):
                return None
            # if value that they differ by occurs more than once, too confusing, punt
            if s1.count(d) != 1:
                return None
            s1 = s1.replace(d, "$var%s$" % i)
            #print s1
        #print "s7", s1
        macro = s1
        # replace $var1$ $var2$  with $var1$
        while True:
            macro2 = re.sub('([$]var\d[$]) ([$]var\d[$])', '\\1', macro)
            if macro == macro2:
                break
            macro = macro2
        # remove unhelpful "| $var$"
        macro = re.sub('[|] ([$]var\d[$])$', '', macro)
        # make sure we still have a pipe.  don't allow macros with just one search command
        if '|' not in macro:
            return None
        if macro[1:].count('|') == 0:
            #print "GOT YOU!", macro
            return None
        return macro
    return None
            
        

    
        


    
    
if __name__ == '__main__':
    import sys
    import splunk.auth as sa
    argv = sys.argv
    if len(argv) < 2:
        print "Usage: <username>"
        exit(-1)
    username = sys.argv[1]
    sessionKey = sa.getSessionKey('admin', 'changeme')
    users = [username]
    for user in users:
        print "USER:", user
        macros = suggestMacros(user, sessionKey, 'search', 1000, 2)
        print "-+"*80
        for m,c in macros:
            print c,"\t", m
        print "-+"*80
        print len(macros), "macros"
