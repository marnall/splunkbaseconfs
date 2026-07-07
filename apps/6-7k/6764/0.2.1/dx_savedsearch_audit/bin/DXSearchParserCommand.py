import os, sys, re, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib.binding import HTTPError

@Configuration(local=True)
class DXSearchParserCommand(StreamingCommand):
   """ %(synopsis)

   ##Syntax

   %(syntax)

   ##Description

   %(description)
   """

   input = Option(require=False, default="search")
   output = Option(require=False, default="search_expanded")
   app = Option(require=False, default=None)
   owner = Option(require=False, default=None)

   def stream(self, events):
         for event in events:
            # TODO: How to handle field not in event?
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

               try:
                  sp_obj = json.loads(
                     str(
                        self.service.get(
                           path_segment="search/parser", app=app, owner=owner, **{"output_mode": "json", "parse_only": "true", "reload_macros": "false", "q": spl}).body))

                  self.add_field(event, self.output, sp_obj)
               except HTTPError as ex:
                  self.add_field(event, self.output, json.loads(ex.body))

            yield event

dispatch(DXSearchParserCommand, sys.argv, sys.stdin, sys.stdout, __name__)