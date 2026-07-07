# import sys, os
# import json
# import requests
# import splunk.entity as entity
# import logging
# import logging.handlers
# import time
# import threading
#
#
# def setup_logger(level):
#     logger = logging.getLogger('strike_ready')
#     logger.propagate = False
#     logger.setLevel(level)
#     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/strikeready.log',
#                                                         maxBytes=25000000, backupCount=5)
#     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#     file_handler.setFormatter(formatter)
#     logger.addHandler(file_handler)
#     return logger
#
#
# logger = setup_logger(logging.INFO)
# session = requests.session()
# thread = []
# output = {
#     'output_mode': 'json',
#     'count': 0
# }
# outputmode = {
#     'output_mode': 'json',
# }
#
#
# def iocchunking(ioc, ioc_count):
#     """Creates chunks of list based on ioc count"""
#     return [ioc[i:i + ioc_count] for i in range(0, len(ioc), ioc_count)]
#
#
# def getCredentials(sessionKey):
#     myapp = 'Strikereadyapp'
#     logger.info(myapp)
#     try:
#         entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody', sessionKey=sessionKey)
#         # logger.info(entities)
#     except Exception as e:
#         raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))
#     for i, c in entities.items():
#
#         data = {
#             'user': c['username'],
#             'pass': c['clear_password'],
#             'url': c['realm']
#         }
#         return data
#
#
# def get_result(url, sid, callback, cbuser, cbpass):
#     url = url + sid
#     searchjob = session.get(url=url, verify=False, data=outputmode)
#     res = searchjob.json()
#     while not res['entry'][0]['content']['isDone']:
#         time.sleep(5)
#         searchjob = session.get(url=url, verify=False, data=outputmode)
#         res = searchjob.json()
#
#     else:
#         url1 = url + '/results/'
#         searchjob = session.get(url=url1, verify=False, params=output)
#         res = searchjob.json()
#         res = res['results'][0]
#         ioc = []
#         for a in res:
#             if res[a] != '0':
#                 ioc.append(a)
#         payload = {
#             'ioc': ioc,
#         }
#         requests.post(url=callback, verify=False, json=payload)
#
# def init_search(baseurl, sid, callback, cbuser, cbpass):
#     tg = threading.Thread(target=get_result, args=[baseurl, sid, callback, cbuser, cbpass])
#     thread.append(tg)
#     tg.start()
#
# def main():
#     iocs = []
#
#     sessionKey = sys.stdin.readline().strip()
#     dat = getCredentials(sessionKey)
#     session.auth = (dat['user'], dat['pass'])
#     search = 'search index = "strikeready" earliest=0 | spath output=ioc path=_source.value | table "ioc" '
#     data = {
#         'max_count': '500000',
#         'status_buckets': '30000',
#         'search': search,
#         'output_mode': 'json'
#     }
#     url = dat['url']
#     u = url + '/servicesNS/nobody/Strikereadyapp/storage/collections/data/Callback'
#     r = session.get(url=u, verify=False, data={'output_mode': 'json'})
#     r = r.json()
#     callback = r[0]['callback']['callback']
#     cbuser = r[0]['callback']['cbuser']
#     cbpass = r[0]['callback']['cbpassw']
#
#     baseurl = url + '/servicesNS/-/Strikereadyapp/search/jobs/'
#     searchjob = session.post(url=baseurl, verify=False, data=data)
#     searchjob = searchjob.json()
#     url = baseurl + searchjob['sid']
#     searchjob = session.get(url=url, verify=False, data=outputmode)
#     res = searchjob.json()
#     while not res['entry'][0]['content']['isDone']:
#         time.sleep(2)
#         searchjob = session.get(url=url, verify=False, data=outputmode)
#         res = searchjob.json()
#     url = url + '/results?output_mode=json&count=0'
#     searchjob = session.get(url=url, verify=False)
#     res = searchjob.json()
#     res = res['results']
#
#     for x in res:
#         iocs.append(x['ioc'])
#
#     url = dat['url'] + '/servicesNS/nobody/Strikereadyapp/storage/collections/data/Index'
#     i = session.get(url=url, verify=False, json=outputmode)
#     i = i.json()
#     index = []
#     for n in i:
#         index.append(n['index'])
#     iocs = iocchunking(iocs, 10000)
#     for i in iocs:
#         i = iocchunking(i, 500)
#         thread.clear()
#         for a in i:
#             search = 'search index={} earliest=0 '
#             inde = ""
#             for g in index:
#                 ind = ' "{}" OR'
#                 ind = ind.format(g)
#                 inde = inde + ind
#             inde = inde.rstrip('OR')
#             search = search.format(inde)
#             search2 = ' | stats '
#             s = '({})'
#             s1 = ""
#             for x in a:
#                 search1 = '"{}" OR '
#                 search1 = search1.format(x)
#                 s1 = s1 + search1
#                 search3 = 'count(eval(searchmatch("{}"))) as {} ,'
#                 search3 = search3.format(x, x)
#                 search2 = search2 + search3
#             s1 = s1.rstrip("OR ")
#             s = s.format(s1)
#             search2 = search2.rstrip(" ,")
#             search = search + s + search2
#             data = {
#                 'max_count': '50000',
#                 'status_buckets': '300',
#                 'search': search,
#                 'output_mode': 'json'
#             }
#             searchjob = session.post(url=baseurl, verify=False, data=data)
#             searchjob = searchjob.json()
#             init_search(baseurl, searchjob['sid'], callback, cbuser, cbpass)
#         for t in thread:
#             t.join()
#
#
# if __name__ == "__main__":
#     main()
