import os, sys, re, json, hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.binding import HTTPError

@Configuration(local=True)
class DXSearchExpansionCommand(StreamingCommand):
   input = Option(require=False, default="search")
   output = Option(require=False, default="search_expanded")
   app = Option(require=False, default=None)
   owner = Option(require=False, default=None)

   # See DXDashboardSearchExtractionCommand.py for perf details
   expandSplCache = None

   def stream(self, events):
      for event in events:
         # TODO: How to handle field specified and not in event?  Defaulting to None...?
         if self.app is None or str(self.app).strip() == "": # or self.app not in event:
            app = None
         else:
            app = event[self.app]

         if self.owner is None or str(self.owner).strip() == "": # or self.owner not in event:
            owner = None
         else:
            owner = event[self.owner]

         if self.input in event:
            spl = event[self.input]
            if re.compile("^\s*[^\|]").match(spl):
               spl = "| search " + spl

            self.add_field(event, self.output, self.expandSpl(spl, app, owner))   

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
         retVal = json.loads(ex.body)

      if self.expandSplCache is not None:
         self.expandSplCache[uid] = retVal

      return retVal

dispatch(DXSearchExpansionCommand, sys.argv, sys.stdin, sys.stdout, __name__)