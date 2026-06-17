import splunk.searchhelp.next as next
import splunk.searchhelp.utils as utils
import splunk.search as se

def suggestTags(user, sessionKey=None, namespace=None):
    tags = {}
    tags['host']       = suggestTagsBySourcetype(user, 'host', sessionKey, namespace, '-1h')
    tags['eventtypes'] = suggestTagsBySourcetype(user, 'eventtype', sessionKey, namespace, '-1h')
    return tags

def suggestTagsBySourcetype(user, field, sessionKey, namespace, earliest):
    search = 'search %s="*" index=* | stats values(sourcetype) as sourcetypes by %s | slc field=sourcetypes labelonly=true | sort cluster_label | stats values(%s) as values by cluster_label' % (field, field, field)

    results = se.searchAll(search, sessionKey=sessionKey, status_buckets=1, earliest_time=earliest)
    if len(results) < 3:
        return {}

    taggedValues = {}
    for i,result in enumerate(results):
        vals = set([str(v) for v in result['values']])
        # don't try to tag single values
        if len(vals) < 2:
            continue
        tag = pickTag(vals)
        if tag in taggedValues:
            tag = '%s%s' % (tag, i)
        taggedValues[tag] = vals
    return taggedValues

def pickTag(values):
    """returns shortest value in values, when digits are removed.  that's the tag used."""
    import re
    vs = [ re.sub('(\d+)', 'N', v) for v in values ]
    m = vs[0]
    for v in vs:
        if len(v) < len(m):
            m = v
    return m
    
    
if __name__ == '__main__':
    import splunk.auth as sa
    #user = 'admin'
    #passwd = 'changeme'
    user = 'admin'
    passwd = 'changeme'
    namespace = 'search'
    
    sessionKey = sa.getSessionKey(user, passwd)
    typetags = suggestTags(user, sessionKey, namespace)
    for tagtype,tags in typetags.items():
        print tagtype
        for tag, vals in tags.items():
            print '\t %s \t:%s ...' % (tag, ', '.join(list(vals)[:5]))
