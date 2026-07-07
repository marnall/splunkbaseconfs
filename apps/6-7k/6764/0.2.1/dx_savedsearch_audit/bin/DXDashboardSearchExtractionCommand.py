import os, sys, re, json, hashlib

# TODO: There's likely a better library than xml.dom.minidom.  Functional first, cleanup later...
from xml.dom.minidom import parseString, Document, Element

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.binding import HTTPError

@Configuration(local=True)
class DXDashboardSearchExtractionCommand(StreamingCommand):
   """ 
   This command isn't documented in srarchbnf at this time.  It's too...let's just not do it
   
   All of the custom commands in this app should/will be moved to custom rest endpoints

   Code was copy/pasted from DXSearchExpansionCommand.py...should/will build classes for code reuse.
   """

   input = Option(require=False, default="eai:data")
   output = Option(require=False, default="dashboard_searches")
   app = Option(require=False, default=None)
   owner = Option(require=False, default=None)

   # BEFORE CACHE: This search has completed and has returned 14,930 results by scanning 0 events in 134.987 seconds
   # AFTER CACHE: This search has completed and has returned 14,930 results by scanning 0 events in 81.353 seconds

   ## Still not sure if this should be enabled or disabled by default.  It makes more sense to have this as an option here than it does for the other commands.
   expandSplCache = {}
   #expandSplCache = None

   def stream(self, events):
      for event in events:
         try:
            doc = parseString(event[self.input])
         except Exception as ex: # Maybe ParseEscape?        
            self.add_field(event, self.output, {"exception": str(ex)})
            yield event
            continue
         
         # TODO: How to handle field specified and not in event?  Defaulting to None...?
         if self.app is None or str(self.app).strip() == "": # or self.app not in event:
            app = None
         else:
            app = event[self.app]

         if self.owner is None or str(self.owner).strip() == "": # or self.owner not in event:
            owner = None
         else:
            owner = event[self.owner]

         searches = getSearches(doc)
         for search in searches:
            try:
               # TODO: This logic could be simplified (and should be double checked).  Something's off and I can't put my finger on it yet.  Another rush job...
               if "base_id" in search:
                  base = [b for b in searches if "id" in b and b["id"] == search["base_id"]]
                  if len(base) == 1:
                     if "query" not in base[0] and "ref" not in base[0]:
                        search["error"] = "Base search does not have 'query' or 'ref' elements"
                     else:
                        if "query" in base[0]:
                           spl = ""
                           base_spl = str(base[0]["query"]).replace("\t", " ").strip()
                           if re.compile("^\s*[^\|]").match(base_spl):
                              base_spl = "| search " + base_spl

                           if "query" in search:
                              spl = str(search["query"]).replace("\t", " ").strip()

                           if spl != "" and spl != "|":
                              if re.compile("^\s*[^\|]").match(spl):
                                 spl = "| " + spl

                           search["search"] = f"{base_spl}{spl}"
                           search["search_expanded"] = self.expandSpl(spl=f"{base_spl}{spl}", app=app, owner=owner)

                        if "ref" in base[0]: #TODO: Try to get ref search definition
                           search["base_ref"] = base[0]["ref"]
                  elif len(base) == 0:
                     search["error"] = f"Base search with id '{search['base_id']}' does not exist"
                  elif len(base) > 1:
                     search["error"] = f"More than one base search with id '{search['base']}' found"
               elif "query" in search:
                  spl = str(search["query"]).replace("\t", " ").strip()
                  if re.compile("^\s*[^\|]").match(spl):
                     spl = "| search " + spl

                  search["search"] = spl
                  search["search_expanded"] = self.expandSpl(spl=spl, app=app, owner=owner)
            except Exception as ex:
               search["exception"] = str(ex)
         
         self.add_field(event, self.output, searches)
         yield event

   def expandSpl(self, spl: str, app: str, owner: str):
      retVal = None # Will never be None

      # I'm not overly concerned about hash collisions or ram usage but...we'll see how this holds up.
      # This isn't thread safe but I don't think we should have multiple threads calling the rest endpoint.  Don't want to hammer splunkd...

      if self.expandSplCache is not None:
         uid = hashlib.md5(f"{app}{owner}{spl}".encode("utf-8")).hexdigest()
         if uid in self.expandSplCache:
            return self.expandSplCache[uid]

      try:
         sp_obj = json.loads(
            str(
               self.service.get(
                  path_segment="search/parser", app=app, owner=owner, **{"output_mode": "json", "parse_only": "true", "reload_macros": "false", "q": spl}).body))
         spl_expanded = ""
         if "commands" in sp_obj:
            for cmd in sp_obj["commands"]:
               spl_expanded = "{}| {} {}\n".format(spl_expanded, cmd["command"], cmd["rawargs"])
            
            retVal = spl_expanded.strip()
      except HTTPError as ex:
         retVal = ex.body.decode("utf-8")

      if self.expandSplCache is not None:
         self.expandSplCache[uid] = retVal
         
      return retVal

def getSearches(doc: Document) -> list:
   searches = []
   i = 0
   
   searchElements = doc.getElementsByTagName("search")
   searchElement: Element
   for searchElement in searchElements:
      i = i + 1
      search = {}
      search["parent"] = searchElement.parentNode.nodeName

      try:
         for attr in ["id", "base", "ref"]:
            if searchElement.hasAttribute(attr):
               if attr == "base":
                  search[f"{attr}_id"] = searchElement.getAttribute(attr)
               else:
                  search[attr] = searchElement.getAttribute(attr)

         for el_name in ["query", "earliest", "latest"]:
            exists, el = getElementByTagName(searchElement, el_name)
            if exists:
               if el.firstChild is not None:
                  search[el_name] = el.firstChild.wholeText
               else:
                  search[el_name] = ""
      except Exception as ex:
         search["exception_getSearches"] = str(ex)

      if not "id" in search:
         search["id"] = f"undefined_{i}"

      searches.append(search)
   
   return searches

def getElementByTagName(el: Element, name: str, first = True):
   elements = el.getElementsByTagName(name)
   if len(elements) == 0:
      return False, None

   retVal = elements[0] if first else elements
   return len(el.getElementsByTagName(name)) > 0, retVal

# Incomplete and unused at this time.  Was considering replacing token values with defaults where available
"""
def getInputs(doc: Document) -> list:
   inputs = []
   inputsElements = doc.getElementsByTagName("input")
   inputsElement: Element
   for inputsElement in inputsElements:
      input = {}
      input["parent"] = inputsElement.parentNode.nodeName

      for attr in ["type", "token"]:
         if inputsElement.hasAttribute(attr):
            input[attr] = inputsElement.getAttribute(attr)

         # type and token aren't required.  How to handle...?
         if "type" not in input:
            raise Exception("Oops...")

         if input["type"] == "time":
            default_exists, defaultElement = getElementByTagName(inputsElement, "default")
            if default_exists:
               defaults = {}
               for def_el_name in ["earliest", "latest"]:
                  exists, el = getElementByTagName(defaultElement, def_el_name)
                  if exists:
                     defaults[def_el_name] = el.firstChild.wholeText
                
               input["default"] = defaults
         else:
            for el_name in ["default", "initialValue"]:
               exists, el = getElementByTagName(inputsElement, el_name)
               if exists:
                  input[el_name] = el.firstChild.wholeText

         inputs.append(input)
    
      return inputs
"""

dispatch(DXDashboardSearchExtractionCommand, sys.argv, sys.stdin, sys.stdout, __name__)