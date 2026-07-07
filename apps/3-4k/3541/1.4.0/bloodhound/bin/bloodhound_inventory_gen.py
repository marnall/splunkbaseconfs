import sys
import json
import re
import xml.etree.ElementTree as xml
import getpass
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option
import bloodhound_utils
import splunk.Intersplunk


logging = bloodhound_utils.get_logger("bloodhound_inventory_gen")
print("_time,name,level_name,message")


def parseArgs():
    if len(sys.argv) == 3:
        if (sys.argv[1][:5].lower() == 'host=' and sys.argv[2][:5].lower() == 'port='):
            host = sys.argv[1][5:]
            port = sys.argv[2][5:]
        elif (sys.argv[1][:5].lower() == 'port=' and sys.argv[2][:5].lower() == 'host='):
            host = sys.argv[2][5:]
            port = sys.argv[1][5:]
        else:
            sys.exit('Error: Incorrect arguments')
    else:
        sys.exit('Error: Incorrect number of arguments')
    return (host, port)


def processSearch(s):
    if (s["type"] == "base"):
        m = re.search(r'earliest=(.*?)[\]\s\|]', s["query"])
        s["earliest"] = m.group(1) if m != None else s["earliest"]
        m = re.search(r'latest=(.*?)[\]\s\|]', s["query"])
        s["latest"] = m.group(1) if m != None else s["latest"]
    if (s["query"] != None):
        m = re.findall(r'\$(\w+)\$', s["query"])
        s["tokens"] = len(m)
    return s


def fixSearch(s):
    s = re.sub(r"^\s*", '', s)
    s = re.sub(r"(\s*\|\s*)", '|', s)
    return s


def processChild(e, level=0, v=None, s=None):
    for c in e:
        if (c.tag == "label"):
            if v["label"] == None:
                v["label"] = c.text
        if (c.tag == "row" or c.tag == "panel" or c.tag == "fieldset"):
            processChild(c, level + 1, v, s)
        if (c.tag == "chart" or c.tag == "table" or c.tag == "html" or c.tag == "event" or c.tag == "single" or c.tag == "map"):
            v["panels"] += 1
            processChild(c, level + 1, v, s)
        if (c.tag == "input"):
            v["inputs"] += 1
            processChild(c, level + 1, v, s)
        if (c.tag == "searchName"):
            search = {}
            v["searches"] += 1
            search["type"] = "saved"
            search["view"] = v["name"]
            search["app"] = v["app"]
            search["parent_tag"] = e.tag
            search["savedsearch_name"] = c.text
            s.append(search)
        if (c.tag == "searchTemplate" or c.tag == "searchString"):
            search = {}
            v["searches"] += 1
            search["type"] = "base"
            search["view"] = v["name"]
            search["app"] = v["app"]
            search["parent_tag"] = e.tag
            search["query"] = fixSearch(c.text)
            earliest = c.find("earliest")
            latest = c.find("latest")
            search["earliest"] = earliest.text if earliest != None else ""
            search["latest"] = latest.text if latest != None else ""
            search = processSearch(search)
            s.append(search)
        if (c.tag == "search"):
            search = {}
            v["searches"] += 1
            search["view"] = v["name"]
            search["app"] = v["app"]
            search["parent_tag"] = e.tag
            if c.get("base", None):
                search["parent"] = c.get("base", None)
                search["type"] = "postprocess"
            elif c.get("ref", None):
                search["type"] = "saved"
                search["savedsearch_name"] = c.get("ref", None)
                search["savedsearch_app"] = c.get("app", None)
            else:
                search["type"] = "base"
            query = c.find("query")
            earliest = c.find("earliest")
            latest = c.find("latest")
            search["query"] = fixSearch(query.text) if query != None else None
            search["earliest"] = earliest.text if earliest != None else None
            search["latest"] = latest.text if latest != None else None
            search = processSearch(search)
            s.append(search)


def processSummary(s, summaries):
    summary = {}
    summary["summary_index"] = s["summary_index_name"]
    summary["search_name"] = s["name"]
    query = fixSearch(s["query"])
    summary["index"] = re.findall(r"index\=\"?(.*?)\"?[\s\|]", query)
    summary["sourcetype"] = re.findall(r"sourcetype\=\"?(.*?)\"?[\s\|]", query)
    summary["fields"] = re.findall(
        r"(?:si)?(?:stats|chart|table|fields)\s(.*?)(?:by)|$", query)
    summary["source"] = re.findall(r"source\=\"?(.*?)\"?[\s\|]", query)
    summary["command"] = re.findall(
        r"((?:si)?(?:stats|chart|table|fields))", query)
    summaries.append(summary)


def runInventory():
    settings = dict()
    splunk.Intersplunk.readResults(
        settings=settings, has_header=True)
    sessionKey = settings['sessionKey']
    APP = "bloodhound"

    logging.info("Script Information Logging")
    HOST, PORT = parseArgs()

    logging.info("Connecting to Splunk Server")
    service = client.connect(
        host=HOST,
        port=PORT,
        token=sessionKey,
        owner="-",
        app="-")

    x = 0
    views = []
    views_searches = []
    apps = []
    logging.info("Loading and Parsing Views from REST API")
    logging.info(
        "Loading and Parsing Views from REST API")

    for app in service.apps:
        application = {}
        application["name"] = app.name
        application["label"] = app.content.get("label", None)
        application["version"] = app.content.get("version", None)
        application["is_visible"] = app.content.get("is_visible", None)
        apps.append(application)
        if (app.state.content.disabled != '1'):
            response = service.get(
                "data/ui/views", app=app.name, output_mode="json", sharing="user").body.read(None)
            while True:
                parsed_response = json.loads(response)
                for entry in parsed_response["entry"]:
                    if (entry["acl"]["app"] == app.name):
                        x = x + 1
                        if (not(entry["author"] == "nobody" or entry["author"] == None) or not(entry["acl"]["app"] == "search" or entry["acl"]["app"] == "system")):
                            view = {}
                            view["author"] = entry["author"]
                            view["name"] = entry["name"]
                            view["id"] = entry["id"]
                            view["app"] = entry["acl"]["app"]
                            view["panels"] = 0
                            view["inputs"] = 0
                            view["searches"] = 0
                            viewxml = entry["content"]["eai:data"]
                            try:
                                parsed_view = xml.fromstring(
                                    viewxml.encode('utf-8'))
                                view["type"] = parsed_view.tag
                                view["label"] = None
                                processChild(parsed_view, 1,
                                             view, views_searches)
                            except Exception:
                                view["malformed"] = True
                            views.append(view)
                if parsed_response["paging"]["total"] > (parsed_response["paging"]["offset"] + parsed_response["paging"]["perPage"]):
                    response = service.get("data/ui/views", sharing=None, app=app.name, output_mode="json",
                                           offset=parsed_response["paging"]["offset"] + parsed_response["paging"]["perPage"]).body.read(None)
                else:
                    break

    saved_searches = []
    saved_search_summaries = []
    logging.info("Loading and Parsing Saved Searches from REST API")
    logging.info(
        "Loading and Parsing Views from REST API")
    for saved_search in service.saved_searches:
        s = {}
        s["app"] = saved_search.access["app"]
        s["owner"] = saved_search.access["owner"]
        s["name"] = saved_search.name
        s["query"] = fixSearch(saved_search.content["search"])
        s["earliest"] = saved_search.content["dispatch.earliest_time"]
        s["latest"] = saved_search.content["dispatch.latest_time"]
        s["type"] = "base"
        s["schedule"] = saved_search.content["cron_schedule"]
        s["is_scheduled"] = saved_search.content["is_scheduled"]
        s["disabled"] = saved_search.content["disabled"]
        s["summary_index"] = saved_search.content["action.summary_index"]
        if saved_search.content["action.summary_index"] == "1":
            s["summary_index_name"] = saved_search.content["action.summary_index._name"] if "action.summary_index._name" in saved_search.content else "summary"
            processSummary(s, saved_search_summaries)
        s = processSearch(s)
        saved_searches.append(s)

    response = service.delete(
        'storage/collections/data/inventory_apps', owner='nobody', app=APP)
    response = service.delete(
        'storage/collections/data/inventory_views', owner='nobody', app=APP)
    response = service.delete(
        'storage/collections/data/inventory_view_searches', owner='nobody', app=APP)
    response = service.delete(
        'storage/collections/data/inventory_saved_searches', owner='nobody', app=APP)
    response = service.delete(
        'storage/collections/data/inventory_saved_search_summaries', owner='nobody', app=APP)

    logging.info("Adding %d App Information to KV Store" % (len(apps)))
    logging.info(
        "Adding View Information to KV Store")
    for app in apps:
        service.request('storage/collections/data/inventory_apps', owner='nobody', app=APP,
                        method='POST', headers=[('Content-Type', 'application/json')], body=json.dumps(app))
    logging.info("Adding %d View Information to KV Store" % (len(views)))
    logging.info(
        "Adding View Information to KV Store")
    for view in views:
        service.request('storage/collections/data/inventory_views', owner='nobody', app=APP,
                        method='POST', headers=[('Content-Type', 'application/json')], body=json.dumps(view))
    logging.info("Adding %d View Search Information to KV Store" %
                 (len(views_searches)))
    logging.info(
        "Adding View Search Information to KV Store")
    for search in views_searches:
        service.request('storage/collections/data/inventory_view_searches', owner='nobody', app=APP,
                        method='POST', headers=[('Content-Type', 'application/json')], body=json.dumps(search))
    logging.info("Adding %d Saved Search Information to KV Store" %
                 (len(saved_searches)))
    logging.info(
        "Adding Saved Search Information to KV Store")
    for search in saved_searches:
        service.request('storage/collections/data/inventory_saved_searches', owner='nobody', app=APP,
                        method='POST', headers=[('Content-Type', 'application/json')], body=json.dumps(search))
    logging.info("Adding %d Summary Information to KV Store" %
                 (len(saved_search_summaries)))
    logging.info(
        "Adding Summary Information to KV Store")
    for summary in saved_search_summaries:
        service.request('storage/collections/data/inventory_saved_search_summaries', owner='nobody', app=APP,
                        method='POST', headers=[('Content-Type', 'application/json')], body=json.dumps(summary))

    logging.info(
        'Script ran successfully and inventory collections were updated')
    logging.info("Script has run successfully")


try:
    runInventory()
except SystemExit as Argument:
    logging.info(Argument)
    logging.error('' + str(Argument))
except Exception as Argument:
    logging.info(Argument)
    logging.error("" + str(Argument))
