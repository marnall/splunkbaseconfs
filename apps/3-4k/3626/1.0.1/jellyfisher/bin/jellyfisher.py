#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys
import re

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", "jellyfisher", "lib"))
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)
from splunklib import six
import jellyfish


@Configuration()
class JellyfisherCommand(StreamingCommand):
    # distances, 2 words
    _distance_algorithms = [
        "levenshtein_distance",
        "damerau_levenshtein_distance",
        "jaro_distance",
        "jaro_winkler",
        "match_rating_comparison",
        "hamming_distance",
    ]

    # phonetic, 1 word
    _phonetic_algorithms = [
        "soundex",
        "nysiis",
        "match_rating_codex",
        "metaphone",
        "porter_stem",
    ]

    preg_t = re.compile("([^(]+)\(([^)]+)")
    req_fields = []
    _uses_lookup = False

    def parse_args(self, strarg):
        ret = self.preg_t.search(strarg)
        self._algorithm = ret.group(1)  # pouet
        self._arguments = [
            x.strip() for x in ret.group(2).split(",")
        ]  # [u'yolo', u'lookup:bheh']
        self._n_arguments = len(self._arguments)
        self.logger.debug("JellyfisherCommand: %s", self._arguments)  # logs command line
        
        if self._algorithm in self._phonetic_algorithms and self._n_arguments != 1:
            raise ValueError("phonetic algorithms takes one argument as input")

        if self._algorithm in self._distance_algorithms and self._n_arguments != 2:
            raise ValueError("distance algorithms takes two arguments as input")

        if (
            self._algorithm not in self._distance_algorithms
            and self._algorithm not in self._phonetic_algorithms
        ):
            raise ValueError("%s is not a valid algorithm" % self._algorithm)

        for a in self._arguments:
            if a.startswith("lookup:"):
                self._uses_lookup = True
                continue
            self.req_fields.append(a)

        if self._algorithm in self._phonetic_algorithms and self._uses_lookup:
            raise ValueError(
                "unsupported branching: lookups cannot be used with phonetic algorithms"
            )

    def stream(self, records):
        self.logger.debug("JellyfisherCommand: %s", self)  # logs command line
        self.parse_args(",".join(self.fieldnames))

        if self._n_arguments == 1:
            f = self.req_fields[0]

            for record in records:
                word = record[f]
                r = getattr(jellyfish, self._algorithm)(word)
                record.update({self._algorithm: r})
                yield record

        else:
            if self._uses_lookup:
                raise ValueError("unsupported yet")
            else:
                f1 = self.req_fields[0]
                f2 = self.req_fields[1]

                for record in records:
                    w1 = record[f1]
                    w2 = record[f2]

                    r = getattr(jellyfish, self._algorithm)(w1, w2)
                    record.update({self._algorithm: r})
                    yield record



dispatch(JellyfisherCommand, sys.argv, sys.stdin, sys.stdout, __name__)
