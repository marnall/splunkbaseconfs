import splunk.mining.FieldLearning as ifl
import re,time

def log(txt):
    return
    f = open("/tmp/tune", "a")
    f.write("%s\n" % txt)
    f.close()
    
g_ignored_terms = set(["sun", "mon", "tue", "tues", "wed", "thu", "thurs", "fri", "sat", "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "2003", "2004", "2005", "2006", "am", "pm", "ut", "utc", "gmt", "cet", "cest", "cetdst", "met", "mest", "metdst", "mez", "mesz", "eet", "eest", "eetdst", "wet", "west", "wetdst", "msk", "msd", "ist", "jst", "kst", "hkt", "ast", "adt", "est", "edt", "cst", "cdt", "mst", "mdt", "pst", "pdt", "cast", "cadt", "east", "eadt", "wast", "wadt", "about", "after", "again", "against", "all", "almost", "already", "also", "although", "always", "among", "an", "and", "any", "anyone", "are", "as", "at", "away", "be", "became", "because", "become", "becomes", "been", "before", "being", "between", "both", "but", "by", "came", "could", "does", "during", "each", "either", "else", "ever", "every", "following", "for", "from", "further", "gave", "gets", "give", "given", "giving", "gone", "got", "had", "has", "have", "having", "here", "how", "however", "if", "in", "into", "is", "it", "itself", "just", "keep", "kept", "like", "made", "make", "many", "might", "more", "most", "much", "must", "neither", "nor", "noted", "not", "no", "now", "of", "often", "on", "only", "or", "other", "our", "out", "owing", "perhaps", "please", "quite", "rather", "really", "regarding", "said", "same", "seem", "seen", "several", "shall", "should", "show", "showed", "shown", "shows", "similar", "since", "so", "some", "sometime", "somewhat", "soon", "such", "than", "that", "the", "their", "theirs", "them", "then", "there", "therefore", "these", "they", "this", "those", "though", "through", "throughout", "to", "too", "toward", "under", "unless", "until", "upon", "use", "used", "usefulness", "using", "various", "very", "was", "we", "were", "what", "when", "where", "whether", "which", "while", "who", "whose", "why", "will", "with", "within", "without", "would", "yet", "net", "org", "com", "edu", "co", "he", "she", "you", "your", "yours", "him", "her", "it", "its", "they", "their"])

MAJOR_TOKENIZER = re.compile("[][<>(){}|!;,'\"*\n\r\s\t&?=]+")           # added = to prevent foo=bar as a value
MINOR_TOKENIZER = re.compile("[][<>(){}|!;,'\"*\n\r\s\t&?/:=@.$#%\\\\]+") #removed  _ and - to prevent max_size or max-size from breaking to max and size
#"

def isTime(token):
    return re.match("^\\d\\d?:\\d\\d:\\d\\d$", token) != None

def getBestTerms(results, max_trainers, max_terms=50, min_popularity=2):
    terms = {}
    fieldValues = set()
    floatRE = re.compile("(-?(?<![.0-9:])[0-9]+\.[0-9]+)(?![.0-9:])")
    for result in results[:max_trainers]:
        raw = result.get('_raw', None)      
        if raw == None:
            continue
        for attr in result:
            fieldValues.add(result[attr])

        # prevent floats (e.g. -3.1415) from being broken into 3 and 1415.
        # but ignoring ip addresses or subseconds (colon or period before or after) float
        # extract out floats and then remove from raw
        floats = re.findall(floatRE, raw)
        raw    = re.sub(floatRE, " ", raw)
        
        raw = re.sub("[a-z_0-9]+=(-?[0-9]+\.[0-9]+[^.])", " ", raw)
        majortokens = re.split(MAJOR_TOKENIZER, raw)
        minortokens = re.split(MINOR_TOKENIZER, raw)
        tokens = set(majortokens).union(set(minortokens)).union(set(floats))
        for tok in tokens:
            terms[tok] = terms.get(tok,0) + 1
    tokensAndCounts = terms.items()
    tokensAndCounts.sort(lambda x, y: y[1] - x[1])
    bestTerms = set()
    for token,count in tokensAndCounts:
        if token in fieldValues:
            continue
        if count < min_popularity or len(bestTerms) >= max_terms:
            break
        if token.lower() not in g_ignored_terms and len(token) > 1 and not isTime(token):
            bestTerms.add(token)
    return bestTerms

def getType(values):
    seenFloat = False
    seenInt = False
    seenText = False
    seenLongText = False
    minVal = None
    maxVal = None
    for v in values:
        try:
            val = float(v)
            if minVal == None or val < minVal:
                minVal = val
            if maxVal == None or val < maxVal:
                maxVal = val
            if int(val) != val:
                seenFloat = True
            else:
                seenInt = True
        except:
            seenText = True
            if len(v) > 20:
                seenLongText = True
    valtype = "field"
    if not seenText:
        if minVal >= 0 and maxVal <= 100:
            if seenFloat:
                valtype = "small_float"
            else:
                valtype = "small_int"
        else:
            if seenFloat:
                valtype = "float"
            else:
                valtype = "int"            
    else:
        if seenLongText:
            valtype = "text"
    return valtype



def consistentTypes(values):
    seenFloat = False
    seenText = False
    for v in values:
        try:
            val = float(v)
            seenFloat = True
        except:
            seenText = True
    return not (seenFloat and seenText)


def suggestFields(results, messages, max_trainers=100, makeSummary=True):
    try:
        _suggestFields(results, messages, max_trainers, makeSummary)
    except Exception, e:
        log(e)
        import traceback
        log(traceback.format_exc())
        
def _suggestFields(results, messages, max_trainers, makeSummary):

    terms = getBestTerms(results, max_trainers)
    log("TERMS: %s" % terms)
    raws = []
    fieldExtractions = {}
    fieldsSeen = set()
    # for each result
    for result in results[:max_trainers]:
        # make list of raw values
        raw = result.get('_raw', None)
        if raw != None:
            raws.append(raw)
        # for each attribute
        for attr in result:
            fieldsSeen.add(attr)
            # add it's values to a set for that attribute
            if attr not in fieldExtractions:
                fieldExtractions[attr] = set()
            fieldExtractions[attr].add(result[attr])

    # remove fieldnames as keys
    terms.difference_update(fieldsSeen)

    allExtractions = fieldExtractions.values()
    regexCount = 0
    compiledRegexes = []
    fieldInfo = {}
    # for each popular term
    for term in terms:
        # learn extractions
        regexes, extractions = ifl.learn(raws, [term], [])
        if len(regexes) == 0 or len(extractions) < 2:
            continue
        looksBogus = False
        # if a single extraction has an "=", it's most likely crap (e.g. 504, foo=402, baz=23)
        for extraction in extractions:
            if '=' in extraction:
                looksBogus = True
                break
        if looksBogus:
            continue
        alreadySeen = False
        # see if the values extracted are already on see (either extracted or on a field)
        for knownExtractions in allExtractions:
            newex = set(extractions)
            oldex = set(knownExtractions)
            sim   = len(newex.intersection(oldex)) / len(newex.union(oldex))
            if sim > 0:
                log("%s NEW: %s\nOLD: %s\nSIM: %s\n\n" % (term, newex, oldex, sim))
            if sim > 0.5:
                alreadySeen = True
                break
        if not alreadySeen:
            log("%s EXTRACTIONS: %s" % (term, extractions))
            extractType = getType(extractions) 
            name = "field_%s" % regexCount
            rex = regexes[0].replace("?P<FIELDNAME>", "?P<%s>" % name)
            regexCount += 1
            compiledRegexes.append(re.compile(rex))
            allExtractions.append(extractions)
            if makeSummary:
                isnumeric = 'float' in extractType or 'int' in extractType
                fieldInfo[name] = { 'type': extractType, 'regex': rex, 'extractions': {}, 'numeric': isnumeric, 'min': float('inf'), 'max': float('-inf'), 'sum': 0.0, 'count':0, 'overlapcount':0 }
                    
    # for each result
    for result in results:
            raw = result.get('_raw', None)
            timestart = result.get('timestartpos',None)
            timeend   = result.get('timeendpos',None)
            # for each regex
            for rex in compiledRegexes:
                # match regex and put values in
                match = re.search(rex, raw)
                if match:
                    start = match.start(1)
                    end   = match.end(1)
                    
                    if timestart != None and timeend != None and start >= timestart and end <= timeend:
                        log("%s-%s\t%s-%s" % (start, end, timestart, timeend))
                        log("IGNORING MATCH INSIDE OF TIME: %s" % raw[start:end])
                        continue
                    extractions = match.groupdict()
                    #log(  "%s, %s, %s, %s, %s" % ( raw, rex.pattern, match, extractions, makeSummary ))
                    
                    for k,v in extractions.items():
                        if makeSummary:
                            updateStats(result, fieldInfo, k, v)
                        result[k] = v

    if makeSummary:
        generateSummary(fieldInfo, results)

def updateStats(result, fieldInfo, field, value):

    if field in fieldInfo:
        info = fieldInfo[field]
        if info['numeric']:
            try:
                v = float(value)
                info['min'] = min(v, info['min'])
                info['max'] = max(v, info['max'])
                info['sum'] = v + info['sum']
            except:
                info['numeric'] = False

        if 'snippet' not in info:
            raw = result.get('_raw', '')
            # if value only occurs once on this event so it's not ambiguous
            if raw.count(value) == 1:
                window = 10
                start = raw.find(value)
                end = start + len(value) + window
                start =  max(0, start - window)
                snippet = ("...%s..." % raw[start:end]).replace(value, "[[[%s]]]" % value)
                info['snippet'] = snippet
                
        info['count'] += 1
        valueCounts = info['extractions']
        # keep count of number of times each extraction occurred
        if value not in valueCounts:
            valueCounts[value] = 1
        else:
            valueCounts[value] += 1
        # if value already extracted on event, increase redundancy count
        if value in result.values():
            info['overlapcount'] += 1
            #log("VALUE: %s VALUES: %s" % (value, result.values))

def generateSummary(fieldInfo, results):
   """Nick: the fact that it works like eventstats, decorating the events, instead of stats count by fieldname seems difficult to work with 
      The foundation I'd like to get to with tune + stats,  or maybe just with tune, looks like: 
      
      Type      |  top N values  |  % coverage   |  % extracted   |  regex
      Text         ems              100              0            |  ...
                   emsmail  
                   tw189171
                   ...
      Small_int |  7             |  5            |   0            |  ...
                   4
                   ...
      """

   totalCount = len(results)
   # empty out results
   del results[:]

   # sort fields by count of matches
   fieldInfoPairs = fieldInfo.items()
   fieldInfoPairs.sort(lambda x, y: (y[1]['count'] - x[1]['count']))

   for field, info in fieldInfoPairs:

       log(info)
       # now that we have all the extractions, let's double check the extraction types
       values = info['extractions'].keys()
       if not consistentTypes(values):
           log("IGNORing INCONSISTENT EXTRACTIONS: %s" % values)
           continue

       # get top 10 terms
       valueAndCounts = info['extractions'].items()
       valueAndCounts.sort(lambda x, y: y[1] - x[1])
       topTerms = [term for term,value in valueAndCounts[:10]]
       info['top_extractions'] = topTerms
       info['coverage_percent']   = "%.2f" % (100.0 * info['count'] / float(totalCount))
       info['redundancy_percent'] = "%.2f" % (100.0 * info['overlapcount'] / float(info['count']))
       
       if info['numeric'] == False:
           del info['min']
           del info['max']
           del info['sum']
       else:
           info['avg'] = info['sum'] / float(info['count'])
           del info['sum']
           
       del info['extractions']
       del info['count']
       del info['overlapcount']

       # in regex, change field_23 -> field  
       info['regex'] = re.sub('\?P<field_\\d{1,3}>', "?P<field>", info['regex'])
       

       
       info['_time'] = time.time()
       info['_raw'] = str(info)
       results.append(info)

