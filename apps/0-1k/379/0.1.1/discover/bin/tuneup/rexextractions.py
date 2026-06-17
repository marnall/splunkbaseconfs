import re,time
import splunk.searchhelp.next as next
import splunk.searchhelp.utils as utils

def normalize(search):
    return search.lower().strip().replace('"', '')


def getRexArgs(arg):
    # takes from intersplunk that deals with sys.args
    kvs = {}

    # handle case where arg is surrounded by quotes
    # remove outer quotes and accept attr=<anything>
    if arg.startswith('"') and arg.endswith('"'):
        arg = arg[1:-1]
        matches = re.findall('(?:^|\s+)([a-zA-Z0-9_-]+)\\s*(::|==|=)\\s*(.*)', arg)
    else:
        matches = re.findall('(?:^|\s+)([a-zA-Z0-9_-]+)\\s*(::|==|=)\\s*((?:[^"\\s]+)|(?:"[^"]*"))', arg)

    arg = re.sub('(?:^|\s+)([a-zA-Z0-9_-]+)\\s*(::|==|=)\\s*((?:[^"\\s]+)|(?:"[^"]*"))', "", arg)
    arg = re.sub('(?:^|\s+)([a-zA-Z0-9_-]+)\\s*(::|==|=)\\s*(.*)', "", arg)
    keywords = arg.strip() #arg.split()
    # for each k=v match
    for match in matches:
        attr, eq, val = match
        # put arg in a match
        kvs[attr] = val
    return keywords, kvs

def suggestExtractions(user, sessionKey=None, namespace=None, mincount=1):

    # get set of known EXTRACT values from props
    knownExtractions = set(['*'])
    propsStanzas = utils.getStanzas("props", sessionKey, namespace)
    for name in propsStanzas:
        for attr, val in propsStanzas[name].items():
            if attr.startswith("EXTRACT"):
                # slightly wrong. doesn't get IN fieldname
                knownExtractions.add(normalize(val))
    
    # go over user entered searches and saved searches
    dummy, searches = next.getPastSearches(user, sessionKey, namespace)
    savedsearches = utils.getStanzas("savedsearches", sessionKey, namespace)
    searches.extend(savedsearches)
    # keep count of all args to 'rex' command
    extractions = {}
    for search in searches:
        commandPipelines = utils.getCommands(search, None)
        for commands in commandPipelines:
            for command, arg in commands:
                if command == "rex":
                    regex, options = getRexArgs(arg)
                    #print regex, options
                    # ignore sed formats
                    if 'mode' in options and options['mode'].lower() == "sed":
                        continue
                    # ignore if not exactly one regex
                    if len(regex) == 0:
                        continue
                    field = options.get('field', '_raw')
                    norm = normalize(arg)
                    # ignore rex that are already in known extractions
                    if norm in knownExtractions:
                        continue
                    if norm in extractions:
                        extractions[norm] = (extractions[norm][0] + 1, (regex, field))
                    else:
                        extractions[norm] = (1, (regex, field))

    searchesAndCounts = extractions.items()
    searchesAndCounts.sort(lambda x, y: y[1][0] - x[1][0])
    # return most common searches, that have a count >= mincount
    return [sc[1] for norm, sc in searchesAndCounts if sc[0] >= mincount]
    

    
if __name__ == '__main__':
    import splunk.auth as sa
    sessionKey = sa.getSessionKey('admin', 'changeme')
    print suggestExtractions("admin", sessionKey, 'search', 2)
