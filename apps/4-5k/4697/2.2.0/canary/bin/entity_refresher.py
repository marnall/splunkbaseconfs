# -*- coding: utf-8 -*-
import os
import json
import sys
import traceback
import logging
from random import choice
import splunk.entity


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

import splunk
from splunk.persistconn.application import PersistentServerConnectionApplication

APP = "canary"

try:
    import sideview_canary as sv
except ImportError:
    sys.path.insert(1,os.path.join(os.environ['SPLUNK_HOME'], "etc", "apps", APP, "bin"))
    import sideview_canary as sv
from canary_request import Request


logger = sv.setup_logging(logging.DEBUG)

def get_amrit():
    """
    one of these fish is not like the other.
    Spoiler: it's the shark.
    """
    fishies = ["""
      _///_
     /o    \\/
     > ))_./\\
        <
        """, """
         /  ;
     _.--\"\"\"-..   _.
    /F         `-'  [
   ]  ,    ,    ,    ;
    '--L__J_.-"" ',_;
        '-._J
        """, """
 .-=-.  ,
(     ><
 `-=-'  `
        """, """

    _.-=-._     .-,
 .'       "-.,' /
(          _.  <
 `=.____.="  `._\\
        """, """
       .   )\\
       \\`.-' `-oo
        ) _  __,0)
       /.' )/
       '
        """, """

    O           ,
             .</       ,
          ,aT&/t    ,</
     o   o:\\:::::95/b/
      ' >::7:::::U2\\P\\
          '*qf\\P    '<\\
             '<\\       '
                '""", """
                    _,;_;/-",_
                 ,")  (  ((O) "  .`,
               ,` (    )  ;  -.,/;`}
             ,"  o    (  ( (  . -_-.
            `.  ;      ;  ) ) \\`; \\;
              `., )   (  ( _-`   \\,'
                 "`'-,,`.jb""","""


       .. .,$DDNNMNNNDD8ND+.
       ..7NNNNMMMMMMMMMMMMMND?.
.      MMMMMMMMMMMMMMMMMMMMMMMM8,
..  .ZMNMDNNNDNNNMMMMMMMMMMMMMMMMD
...8MMMMMMMMMNDMMNDDDODNMMMMMMMMMMMM...
. DMMMNNN8$7777ZO7I???7$Z8NNMMMMMMMMI
.DMMMDZ$$7IIII?++++?III77$7Z8NMMMMMMN..
7MNMNZ$$77?I?++=====??I7I$$ZODMMMMMMN..
DDMMNZ$$7???+==~:::~=+?II77$8NMMMMMMM..
NMMMN$7I?+===~::,,,,:~+??I7$Z8DNMMMMM~..
MMMN8I??++=~~:::,,,,,:=++?I7$ZDNMMMMMD..
MMM8$I7I+=~:::,,,,,,:====+?II$8DNNMMMM:.
MMNZ$NNN87~:::,,,,,,~?II7?=+?7ZDMMMMMM8.
MMO87~~=IZ7+,,,....:Z8ZI=+7Z$7I$DNMMMM8.
ZM$$====~==?~,,..,~++=:,,::~I7?78NMNNO+.
7D7?++I?+=~==:,,,~=~~=~====~=I?78NM$I?I.
777?$O~,D8+?+I~:~?+?+=8D~87?++?IZN8?7I~.
~?7+?$~:8Z,==?=:+I++,,$8:IO7=~?I$8$==7~=
.7I=+?+==~~~~?~:+?=~+=~=+===~:+I7ZI~~?I.
.7?=~:=+++:~?+::~?=~:::~~::::~+77Z7?==$.
+??=::,:::=??~::~??+:,,,,,,:~~+7$ZI~~I:.
+II=:,,:::+?+~::~+++~:,,,,,:~=?7$$=~~+,.
III~:::::~?+~:,:~=+I~:,,,,,:~??7ZZ~~+...
 7?=::~++~?=:,.,~=~?~==~,,:~+?IIZ.......
 .+=~=+=+=++:,,:=+?+~~~==~=+++II8 ......
 .===:~+77OOO+=$OOZ$7$$I=+=+==I$,.......
  ,==:~~+I==???==+++??II=~=+++IO........
  .:==:=:==.........:==~~~+?+?Z.........
  ..~+===~II?:...,=?I+~~=+?+?I:.........
 ...==?===?I==,,:~=I+~~++I??I$..........
  ..,?++=+~=?=:::+?===~=+?III...........
  ...I??+I+=?Z$I7I+===~?II7:............
  ....7I?ZII?+==~~~=~+I7I$..............
  .....$I$$7I+~=~~~=?$777...............
  ......=7O8ZZOZ$$ZOZ$7.................
  ........~I$OD88ZZ$7...................
  .......... :+++:......................
  """
                ]
    return choice(fishies)


class CanaryFreshmakerHandler(PersistentServerConnectionApplication):
    """
    This endpoint just wraps splunk's debug/refresh in a slightly nicer way.
    plus ascii-art fish.
    """

    def __init__(self, command_line, command_arg):
        """oh hai"""
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:
            params = json.loads(in_string)
            request = Request(params)

            path = request.qs_dict.get("entityPath",False)
            if not path:
                return sv.build_response(200, " ")

            try:
                splunk.entity.refreshEntities(path, namespace='-', sessionKey = request.session_key, owner="nobody")
                message = "OK we just told Splunkd to refresh " + path + " from disk"
                #logger.info("no exception in the main try")

            except splunk.ResourceNotFound:
                message = "WARNING -- no _reload was found on this instance for %s.  (Perhaps its one of the windows-only entities and this isn't a windows instance?)" % path

            except Exception as e:
                logger.error(e)
                logger.error(traceback.format_exc(e))
                message = "Error occurred refreshing %s %s" %  (path, e)

            splunk_config = sv.get_splunk_server_config(request.session_key)
            root_endpoint = splunk_config["ROOT_ENDPOINT"]
            return sv.build_mako_response("freshmaker.html", {
                "message": "".join(message),
                "amrit": get_amrit(),
                "ui_theme": request.ui_theme,
                "canary_static_url_prefix": sv.get_static_url_prefix(request.session_key, "canary", request.locale, root_endpoint)
            })
        except Exception as e2:
            return sv.build_response(500, "bad things happened %s %s" % (path, e2))
