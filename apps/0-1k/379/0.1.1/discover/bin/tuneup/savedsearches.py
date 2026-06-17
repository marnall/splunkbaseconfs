import splunk.searchhelp.next as next
import splunk.searchhelp.utils as utils

def normalize(search):
    return search.lower().strip().replace('"', '')

def suggestSavedSearches(user, sessionKey=None, namespace=None, mincount=1):

    # get set of known eventtypes
    knownSavedSearches = set(['*', '| metadata type=hosts', '| metadata type=sourcetypes', '| metadata type=sources'])
    savedSearchestanzas = utils.getStanzas("savedsearches", sessionKey, namespace)
    for name in savedSearchestanzas:
        knownSavedSearches.add(normalize(savedSearchestanzas[name].get('search', '')))
    
    # go over user entered searches and saved searches
    dummy, searches = next.getPastSearches(user, sessionKey, namespace)
    savedSearches = {}
    for search in searches:
        if search.startswith("search "):
            search = search[7:]
        norm = normalize(search)
        # ignore searches that are already in known savedSearches
        if norm in knownSavedSearches:
            continue
        if norm in savedSearches:
            savedSearches[norm] = (savedSearches[norm][0] + 1, search)
        else:
            savedSearches[norm] = (1, search)

    searchesAndCounts = savedSearches.items()
    searchesAndCounts.sort(lambda x, y: y[1][0] - x[1][0])
    # return most common searches, that have a count >= mincount
    return [sc[1] for norm, sc in searchesAndCounts if sc[0] >= mincount]
    

    
if __name__ == '__main__':
    import splunk.auth as sa
    sessionKey = sa.getSessionKey('admin', 'changeme', 'localhost:8089')
    print suggestSavedSearches("admin", sessionKey, 'search', 2)
