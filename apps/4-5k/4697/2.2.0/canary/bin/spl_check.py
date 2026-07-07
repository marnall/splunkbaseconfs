# Copyright (C) 2022-2026 Sideview LLC.  All Rights Reserved.

# there is an extensive set of unit tests covering the functionality of this command.
# however these unit tests do not ship with the public Canary app.

import json
import re
import sys
import splunk
import splunk.rest as rest

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration #, Option, validators

APP = "canary"

MACRO_REPLACER = re.compile(r"^([^(]+)\(([^(]+)\)$")
INDEX_TERM_FINDER = re.compile(r".+?index=([^\*]+)")


# Neat in principle, but so slow in practice that it's unusable.
# so we use our own SPL parser code.
#
#PARSER_URI = "/servicesNS/%s/%s/search/v2/parser"
#def parse_spl_syntax(session_key, spl, app):
#    if app is None:
#        app = APP
#    _response, content = rest.simpleRequest(
#        PARSER_URI % ("-", app),
#        postargs={
#            "q": spl,
#            "output_mode": "json"
#        },
#        sessionKey=session_key,
#        method='POST',
#        raiseAllErrors=True
#    )
#    return json.loads(content)


def is_distributable_streaming(clause):
    """ Given a clause beginning with a particular SPL command, will return boolean to indicate
    whether the command is "distributable streaming".  ie whether splunkd will allow this command
    to either run out at the indexers,  or send a "precommand" of itself out to the indexer tier.
    """
    command = clause.split(" ")[0]
    if command in ["addinfo", "addtotals", "convert", "eval", "extract", "fieldformat", "fields", "fillnull", "highlight", "iconify", "iplocation", "makemv", "multikv", "mvexpand", "nomv", "rangemap", "regex", "reltime", "rename", "replace", "rex", "search", "spath", "strcat", "tags", "typer", "where", "untable", "xmlkv", "xpath"]:
        return True

    # not really a true distributable streaming command, as per docs etc.  but it needs to return true.
    if command=="makeresults":
        return True


    #bin     Streaming if specified with the span argument. Otherwise a dataset processing command.
    if command in ["bin", "bucket"]:
        #TODO this is very crude
        return clause.find("bins=") == -1

    #dedup   Streaming by default. Using the sortby argument or specifying keepevents=true makes the dedup command a dataset processing command.
    if command == "dedup":
        if clause.find("sortby") != -1 or clause.find("keepevents=true"):
            return False
        return True

    #lookup  Distributable streaming when specified with local=false, which is the default. An orchestrating command when local=true.
    if command == "lookup":
        if clause.find("local=true") != -1:
            return False
        return True

    #xyseries    Distributable streaming if the argument grouped=false is specified, which is the default. Otherwise a transforming command.
    if command == "xyseries":
        if clause.find("grouped=true") != -1:
            return False
        return True

    # TODO this needs to make a lazy loaded REST call to get commands.conf
    # but... in practical terms, what's written here will at least filter out the app's
    # own searches
    if command in ["auditextractor", "splcheck", "checkxml"]:
        return True;
    # the AXL app's commands are actually generating and therefore nonstreaming. ["ciscoaxl", "ciscoaxlquery", "ciscoris"]:

    return False
    #cluster     Streaming in some modes.


# not used yet.  I'll have to see if we can make just one call to this or... "a small number" of calls to it.
# returns a dict whose keys are the commands, and whose values as of this writing are just "streaming": <boolean>
def get_available_commands(session_key):
    uri = "/services/data/commands"
    args = {
        "output_mode": "json",
        "f": ["streaming"]
    }
    _unused, response = splunk.rest.simpleRequest(uri,
                   sessionKey=session_key,
                   getargs=args,
                   method='GET',
                   raiseAllErrors=True)

    response = json.loads(response).get("entry")


    output = {}
    for command_dict in response:
        name = command_dict["name"]
        streaming = command_dict["content"]["streaming"]
        output[name] = {"streaming": streaming}
    return output



########################################################################
""" just some tinkering, to poke at how much of an ocean-boiling problem this is.
    but if we can cover a decent proportion of the space,  and have the same logic on the
    input fields side, then you can have a tool
    to tell users "hey your SPL is broken. this clause requires this field which can't
    possibly be there"
    AND... if you can imagine a world where we have code that can do that,  then
    implementing a conversion/suggestor/fixer  tot ake folks from append SPL to
    Eval+stats SPL seems a little more possible.
     """
class CommandParser(object):
    def __init__(self, clause):
        self.clause = clause

    def get_input_fields(self):
        raise NotImplementedError

    def get_output_fields(self):
        raise NotImplementedError

    ######
    # it's unclear whether these little worker functions make sense as methods.
    # if they weren't here, this would be a clean little abstract class.
    # they probably dont but leaving them like this for now.
    def get_function_fields(self, spl, which="output"):
        function_fields = []

        #special 'count' token is special'
        if which=="output" and (spl + " ").find(' count ', ) != -1:
            function_fields.append("count")

        function_set = r"(\w+\(\w+\))(\s+as\s+(\w+))?"
        for m in re.findall(function_set, spl):
            if which=="output":
                if len(m)==3 and m[2]!="":
                    function_fields.append(m[2])
                elif m[0]!="":
                    function_fields.append(m[0])
            else:
                function_fields.append(m[1])
        return function_fields

    def make_tokens(self, spl):
        tokens = re.split(r'\s|,', spl.strip())
        things_to_kill = [""," "]
        for thing in things_to_kill:
            while thing in tokens:
                tokens.remove(thing)
        return tokens

    def get_group_by_fields(self, spl):
            group_by_fields = []
            tokens = self.make_tokens(spl)
            for i, token in enumerate(tokens):
                group_by_fields.append(token)
            return group_by_fields

class StatsParser(CommandParser):

    def get_input_fields(self):
        halves = self.clause.split(" by ")
        function_fields = self.get_function_fields(halves[0], which="input")
        group_by_fields = []
        if len(halves)>1:
            group_by_fields = self.get_group_by_fields(halves[1])
        return function_fields + group_by_fields

    def get_output_fields(self):
        halves = self.clause.split(" by ")
        function_fields = self.get_function_fields(halves[0])
        group_by_fields = []
        if len(halves)>1:
            group_by_fields = self.get_group_by_fields(halves[1])
        return function_fields + group_by_fields

class ChartParser(CommandParser):

    def get_input_fields(self):
        parts = re.split(r'\sby\s|\sover\s', self.clause.strip())
        function_fields = []
        if len(parts)<3:
            function_fields = self.get_function_fields(parts[0], which="input")
        group_by_fields = []
        if len(parts)>1:
            group_by_fields = self.get_group_by_fields(parts[1])
        split_by_fields = []
        if len(parts)>2:
            split_by_fields = self.get_group_by_fields(parts[2])
        return function_fields + group_by_fields + split_by_fields

    def get_output_fields(self):
        parts = re.split(r'\sby\s|\sover\s', self.clause.strip())
        function_fields = []
        if len(parts)<3:
            # if there is a split-by clause, then the function
            # fields as named wont be created.
            function_fields = self.get_function_fields(parts[0])
        group_by_fields = []
        if len(parts)>1:
            tokens = self.make_tokens(parts[1])
            group_by_fields = self.get_group_by_fields(tokens[0])
            if len(tokens)>1:
                group_by_fields.append("__UNKNOWN__")
        return function_fields + group_by_fields


class TimechartParser(CommandParser):

    def get_input_fields(self):
        parts = re.split(r'\sby\s', self.clause.strip())
        function_fields = []
        if len(parts)<2:
            function_fields = self.get_function_fields(parts[0], which="input")

        #always _time
        group_by_fields = ["_time"]
        split_by_fields = []
        if len(parts)>1:
            split_by_fields = self.get_group_by_fields(parts[1])
        return function_fields + group_by_fields + split_by_fields

    def get_output_fields(self):
        raise "unimplemented"

class EvalParser(CommandParser):

    def get_output_fields(self):
        clause = self.clause.replace("eval ","")
        function_fields = []
        expressions = r"\s?(\w+)\s?=\s?([^,]+)"
        for m in re.findall(expressions, clause):
            function_fields.append(m[0])
        return function_fields

def get_parser(clause):
    if len(get_commands(clause))>1:
        raise ValueError("get_output_fields takes only single clauses")
    tokens = clause.split(" ")
    command = tokens[0]
    parser = None
    if command == "stats":
        parser = StatsParser(clause)
    if command == "chart":
        parser = ChartParser(clause)
    if command == "eval":
        parser = EvalParser(clause)
    return parser

def get_output_fields(clause):
    parser = get_parser(clause)
    return parser.get_output_fields()

def get_input_fields(clause):
    parser = get_parser(clause)
    return parser.get_input_fields()

########################################################################


def distill(entries, type="macros"):
    system_things = {}
    global_things = {}
    app_things = {}
    for entry in entries:
        # Note that if a macro is in etc/system/local the eai:appName is "system".
        app = entry.get("content").get("eai:appName")
        name = entry.get("name")
        sharing = entry.get("acl").get("sharing")

        value_key = "definition"
        if type=="eventtypes":
            value_key = "search"
        value = entry.get("content").get(value_key)

        if sharing == "system":
            system_things[name] = value
        elif sharing == "global":
            global_things[name] = value
        elif sharing == "user":
            # we... dont do anything with these. Sorry.  They're uncommon? omg look over there!
            pass
        else:
            if app not in app_things:
                app_things[app] = {}
            app_things[app][name] = value

    return system_things, global_things, app_things

def merge_layers(system_things, global_things, app_things):
    # now to actually merge in system-level and globally-shared macros
    app_names = app_things.keys()
    for app in app_names:
        for name, definition in global_things.items():
            #global only applies if there isn't an app-level macro overriding it.
            if name not in app_things[app]:
                app_things[app][name] = definition

        for name, definition in system_things.items():
            # system level definitions always win so we fold these in last.
            app_things[app][name] = definition
    return app_things

def get_macros(session_key):
    """ Top level keys are app names.
    Within a particular app, the namespace of macros has ALREADY had the global and the system
    macros merged into the dict.   So this is basically the list of "effective" macros defined
    at the app-level for each app.
    """

    getargs = {"output_mode":"json", "count":"0"}
    uri = "/servicesNS/nobody/-/data/macros"
    _response, content = rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                            raiseAllErrors=True, getargs=getargs)
    content = json.loads(content)
    #print(json.dumps(content, indent=4))

    system_macros, global_macros, app_macros = distill(content.get("entry"))
    # we... dont care about these atm
    #user_macros = {}

    return merge_layers(system_macros, global_macros, app_macros)


def get_eventtypes(session_key):
    """ David's the best """
    getargs = {"output_mode":"json", "count":"0"}
    uri = "/servicesNS/nobody/-/saved/eventtypes"
    _response, content = rest.simpleRequest(uri, sessionKey=session_key, method="GET",
                                            raiseAllErrors=True, getargs=getargs)
    content = json.loads(content)

    system_eventtypes, global_eventtypes, app_eventtypes = distill(content.get("entry"), "eventtypes")

    return merge_layers(system_eventtypes, global_eventtypes, app_eventtypes)


def replace_macros(macros, spl):
    """ Given a flat dictionary of macros, and an spl expression, this function will return
    the SPL expression with all macros recursively replaced.
    NOTE - It assumes that the macros dictionary has already been correctly layered with
    globally shared macros, app-level macros, and system level macros.
    It currently ignores private macros that the user might have, or ones that they might
    have overridden with a private definition.
    """

    if not macros:
        return spl
    output = []
    macro_name = ""
    i = 0
    in_backticks = False

    while i < len(spl):
        c = spl[i]

        if c == "`":
            if i+2 < len(spl) and spl[i:i+3] == "```":
                closing_comment_index = spl[i+3:].find("```")
                if closing_comment_index != -1:
                    new_i = i + 3 + closing_comment_index + 3
                    output += spl[i:new_i]
                    i = new_i
                    continue

            in_backticks = not in_backticks
            #the very beginning of the macro name
            if in_backticks:
                macro_name = ""
            #the very end of the macro name
            else:

                macro_value = macros.get(macro_name, None)
                # this gets hit when it's like `my_macro(some_arg)`
                if macro_value is None:

                    ## Note - this logic is broken.
                    ## it ends up replacing the definition for the foo(1) macros,  but not replacing teh argument into the $foo$ token
                    ## so if you have a definition like mymacro(1)    something($myarg$)
                    ## and your SPL has  mymacro(foo)
                    ## you end up with   something($myarg$)foo
                    #solution...
                    # 1) make the get_macros preserve the args in the struct.
                    # 2) make replace_macros use those args and map the arguments to the right $foo$ tokens
                    try:


                        matches = re.match(MACRO_REPLACER, macro_name)
                        macro_expression = matches[0]
                        macro_name = matches[1]
                        macro_args = matches[2].split(",")
                        # TODO - we still don't actually replace the args into the $arg$ spots.
                        macro_value = macros.get("%s(%s)" % (macro_name, len(macro_args)), None)
                        if macro_value is None:
                            raise ValueError("macro \"%s\" was not found. Possibly it is a private user-level macro which we dont yet support" % macro_name)
                        if i+len(macro_expression) < len(spl):
                            i += len(macro_expression)

                    except Exception as e:
                        output += "`%s`" % macro_name
                        if i+len(macro_name) < len(spl):
                            i += len(macro_name) + 5
                        continue
                macro_value = replace_macros(macros, macro_value)
                output += macro_value
        elif in_backticks:
            macro_name += c
        else:
            output += c

        i += 1
    return "".join(output)

def get_commands(spl):
    """
    Copied over from sideview_canary.py in the Canary App.
    which was in turn ported from the equivalent function in Canary's Javascript.

    given an SPL expression, this will parse it and return an array of the clauses
    Note that it treats entire subsearch expressions just as big weird tokens, ignoring all
    the commands within.
    So in other words it gets the "top level" commands only.
    """

    #first, we never care about comments so let's strip all well-formed comments first.
    spl = re.sub(r"```.*?```", "", spl)

    commands = []
    if not spl:
        return []
    i = 0
    inside_quotes = False
    bracket_depth = 0

    spl = spl.strip()
    if spl[0] != "|":
        spl = "search " + spl

    while i < len(spl):
        c = spl[i]
        if c == "\\":
            i += 2
            continue

        if c == "`":
            if i+2 < len(spl) and spl[i:i+3] == "```":
                closing_comment_index = spl[i+3:].find("```")
                if closing_comment_index != -1:
                    i = i + 3 + closing_comment_index + 3
                    continue

        elif inside_quotes:
            if c == "\"":
                inside_quotes = False
        elif c == "\"":
            inside_quotes = True
        elif c == "[":
            bracket_depth += 1
        elif c == "]":
            # malformed
            if bracket_depth <= 0:
                return []
            bracket_depth = bracket_depth - 1
        elif c == "|" and bracket_depth == 0:
            if i > 0:
                commands.append(spl[:i].strip())
            spl = spl[i+1: len(spl)]
            i = 0
            continue
        i += 1
    if inside_quotes:
        #raise ValueError("unbalanced quotes on search expression.")
        return []
    if bracket_depth != 0:
        #raise ValueError("unbalanced brackets on search expression.")
        return []

    commands.append(spl.strip())
    return commands

# | makeresults | eval search="search index=foo | stats count by type" | splcheck


@Configuration()
class SplCheckCommand(StreamingCommand):

    def stream(self, records):
        """ It seems perfectly happy as a streaming command although yes it feels a little strange"""

        #header = self.input_header
        session_key = self._metadata.searchinfo.session_key

        macros = get_macros(session_key)

        for record in records:

            spl = record.get("search", None)
            app = record.get("app", "global")

            if spl is None:
                continue

            #with auditextractor these problems should now be gone
            assert isinstance(app, str), "the app field must be single-valued not multivalue"
            assert isinstance(spl, str), "the search field must be single-valued not multivalue "  + ("<br><br>\n\n".join(spl))

            spl = spl.strip()

            spl = replace_macros(macros.get(app, {}), spl)
            record["expanded_search"] = spl

            # streaming commands are weird.   All the rows have to have the same fields.
            record["has_index_term"] = ""
            record["first_transforming"] = ""
            record["has_precommand"] = ""

            # TODO -
            # earlier I thought that ITSI had some creepy ability to dispatch mcatalog searches
            # such that they appeared in audit log without their initial pipe.
            # looking again now,   I see these searches have mcatalog are trying to have mcatalog
            # as their first command, but they then  have append commands....
            # so I think ITSI just had a stupid facepalm mistake in these searches, and
            # "mcatalog" and all the args there were just being searched for in the default index
            # finding zero results, and the ITSI developers just never found the bug.
            # so I am now (11/2/2023 ) commenting out this silliness and changing the corresponding tests.
            #if len(spl)>0:
            #    first_command_name = spl.split(" ")[0]
            #    if first_command_name in ["summarize", "mcatalog", "rest"]:
            #        spl = "| " + spl

            clauses = get_commands(spl)



            for index, clause in enumerate(clauses):
                command = clause.split(" ")[0]
                if index == 0:
                    record["first_command"] = command
                    if command=="search":
                        if re.match(INDEX_TERM_FINDER, clause):
                            record["has_index_term"] = "yes"
                        else:
                            record["has_index_term"] = "no"

                if is_distributable_streaming(command):
                    continue
                record["first_transforming"] = command
                if command in ["stats", "chart", "timechart", "top"]:
                    record["has_precommand"] = "yes"
                else:
                    record["has_precommand"] = "no"
                break

            record["raw_commands"] = clauses


            """
# old and crazy version that hit the parser.
# A) this is dog slow, and can only be done for ~100 at a time.
# B) the parser sucks. It does weird things that are unlike the actual parser's
#    behavior in the search API.  for instance it'll take commands where the
#    first command is makeresults and it will happily put all the "pre*" flags on
#    subsequent transforming commands.... But Why?
            try:
                parser_output = parse_spl_syntax(session_key, spl, record.get("app",None))

                if "commands" in parser_output:

                    for command in parser_output["commands"]:
                        if "firstCommand" not in record:
                            record["firstCommand"] = command["command"]
                        if record["firstCommand"] != "search":
                            break

                        pipeline = command["pipeline"]
                        if pipeline == "streaming":
                            continue
                        if pipeline == "report" and "preStreamingOp" in command:
                            pre_streaming_op = command["preStreamingOp"]
                            if pre_streaming_op:
                                record["preCommand"] = pre_streaming_op

            except splunk.BadRequest as e:
                parser_output = {}
                try:
                    record["spltest"] = e.extendedMessages[0]["text"]
                except Exception as e2:
                    record["spltest"] = traceback.format_exc(e2)


            for key in parser_output:
                record["output." + key] = parser_output[key]
            """
            #for key in header:
            #    record[key] = header[key]
            yield record


dispatch(SplCheckCommand, sys.argv, sys.stdin, sys.stdout, __name__)
