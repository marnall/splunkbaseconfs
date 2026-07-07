# Copyright (C) 2015 Consist Software Solutions GmbH. All Rights Reserved. Version 0.1, 2015-07-29.
# This work is licensed under the Creative Commons Attribution 3.0 Unported License. To view
# a copy of this license, visit http://creativecommons.org/licenses/by/3.0/ or send a letter to
# Creative Commons, 444 Castro Street, Suite 900, Mountain View, California, 94041, USA.
# 
# Generates props.conf, transforms.conf and regex_ids_rules.csv lookup files from JSON filter sets
# formatted like PHP IDS filter sets. This writes to default by default, run at your own risk!
import os, json, datetime
from pprint import pprint

base = os.path.dirname(os.path.realpath(__file__))

props = "# Regex IDS auto-generated file, modify with care.\n# Manual changes will be overwritten with the next converter.py run!\n# Generated at %s\n\n" % datetime.datetime.now()
transforms = props
tags = props
lookup = "rule,description,impact\n" # TODO tags
props += "[access_combined]\n"
tag_dict = {}

with open(os.path.join(base, "default_filter.json")) as file:
  filters = json.load(file)["filters"]["filter"] # dawg...
  
  for filter in filters:
    props += "REPORT-regex_ids_rule_%s = regex_ids_rule_%s\n" % (filter["id"], filter["id"])
    transforms += "[regex_ids_rule_%s]\nREGEX = (%s)\nFORMAT = regex_ids_rule::%s\n\n" % (filter["id"], filter["rule"], filter["id"])
    lookup += "%s,\"%s\",%s\n" % (filter["id"], filter["description"], filter["impact"])
    if (not isinstance(filter["tags"]["tag"], list)): filter["tags"]["tag"] = [filter["tags"]["tag"]]
    tag_dict[filter["id"]] = []
    for tag in filter["tags"]["tag"]:
      tag_dict[filter["id"]].append(tag)

  for id, list in tag_dict.items():
    tags += "[regex_ids_rule=%s]\n" % id
    for tag in list:
      tags += "%s = enabled\n" % tag
    tags += "\n"

  with open(os.path.join(os.path.dirname(base), "default", "props.conf"), "w") as file:
    file.write(props)
  with open(os.path.join(os.path.dirname(base), "default", "transforms.conf"), "w") as file:
    file.write(transforms)
  with open(os.path.join(os.path.dirname(base), "default", "tags.conf"), "w") as file:
    file.write(tags)
  with open(os.path.join(os.path.dirname(base), "lookups", "regex_ids_rules.csv"), "w") as file:
    file.write(lookup)

