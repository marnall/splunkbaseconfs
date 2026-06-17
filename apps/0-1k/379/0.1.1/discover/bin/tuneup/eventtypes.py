import splunk.searchhelp.next as next
import splunk.searchhelp.utils as utils
import re

def normalize(search):
    return search.lower().strip().replace('"', '')

def redundant(search):
  """ returns true if search consists of just an eventtype (e.g. 'eventtype=foo' or 'eventtype="foo bar") """
  return re.match('^eventtype=(?:"[^"]*")|(?:[^"][^ ]*)$', search) != None

def suggestEventtypes(user, sessionKey=None, namespace=None, mincount=1):

    # get set of known eventtypes
    knownEventtypes = set(['*'])
    eventtypeStanzas = utils.getStanzas("eventtypes", sessionKey, namespace)
    for name in eventtypeStanzas:
        knownEventtypes.add(normalize(eventtypeStanzas[name].get('search', '')))
    
    # go over user entered searches and saved searches
    dummy, searches = next.getPastSearches(user, sessionKey, namespace)
    savedsearches = utils.getStanzas("savedsearches", sessionKey, namespace)
    searches.extend(savedsearches)
    # keep count of all args 'search' command
    eventtypes = {}
    for search in searches:
        commandPipelines = utils.getCommands(search, None)
        for commands in commandPipelines:
            for command, arg in commands:
                if command == "search":
                    arg = arg.strip()
                    norm = normalize(arg)
                    # ignore searches that are already in known eventtypes.
                    # and ignore searches that contain macros.
                    if norm in knownEventtypes or '`' in arg:
                        continue
                    if norm in eventtypes:
                        eventtypes[norm] = (eventtypes[norm][0] + 1, arg)
                    else:
                        eventtypes[norm] = (1, arg)

    searchesAndCounts = eventtypes.items()
    searchesAndCounts.sort(lambda x, y: y[1][0] - x[1][0])
    # return most common searches, that have a count >= mincount
    return [sc[1] for norm, sc in searchesAndCounts if sc[0] >= mincount and not redundant(sc[1])]
    

    
if __name__ == '__main__':
    import splunk.auth as sa
    sessionKey = sa.getSessionKey('admin', 'changeme')
    print suggestEventtypes("admin", sessionKey, 'search', 2)
