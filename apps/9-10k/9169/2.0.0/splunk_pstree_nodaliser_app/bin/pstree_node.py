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

#Ps tree logic copied from Giampaolo Rodola's gitub
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#https://github.com/giampaolo
#https://github.com/giampaolo/psutil/blob/master/scripts/pstree.py

# Nodalised fork: instead of rendering an indented ASCII-art tree into a
# single multivalue "tree" field, this emits one row per parent/child edge
# with the full ancestor lineage attached, so results can be fed straight
# into node/link visualisations (force-directed graphs, dendrograms via
# d3.stratify, etc.) without reshaping in SPL first.

from __future__ import absolute_import, division, print_function, unicode_literals
import sys, collections, os
splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'splunk_pstree_nodaliser_app', 'lib'))
from splunklib.searchcommands import dispatch, EventingCommand, Configuration, Option, validators

@Configuration()
class PSTreeCommand(EventingCommand):
        """ Reconstructs a process tree from a parent and child field and emits it as one row
        per parent/child edge, annotated with the full ancestor lineage. Intended for sysmon
        EventCode=1 events but can be used for anything. Designed for feeding node/link
        visualisations (force-directed graphs, dendrograms) rather than printing an ASCII tree.

        ##Syntax

        .. code-block::
        pstree_node parent=<field> child=<field> detail=<field> method=<r|i>

        ##Description

        Returns one row per parent/child edge in the reconstructed tree(s). Each row carries the
        edge (parent, child), the root of the tree the edge belongs to, the node's depth, and its
        full lineage (the ordered chain of ancestors from the root down to the node, inclusive).
        Logs must be received in chronological order for accurate results. Details should be
        associated with the child field.

        ##Example

        Display tree of sysmon process ids.

        .. code-block::
        index=sysmon EventCode=1 | pstree_node parent=ParentProcessID child=ProcessID

        """

        parent = Option(
        doc='''
        **Syntax:** **parent=***<fieldname>*
        **Description:** Name of the field that holds the parent value''',
        require=True, validate=validators.Fieldname())

        child = Option(
        doc='''
        **Syntax:** **child=***<fieldname>*
        **Description:** Name of the field that holds the child value''',
        require=True, validate=validators.Fieldname())

        detail = Option(
        doc='''
        **Syntax:** **detail=***<fieldname>*
        **Description:** Name of the field that holds detail value for child field''',
        require=False, validate=validators.Fieldname())

        method = Option(
        doc='''
        **Syntax:** **method=***str*
        **Description:** Algorithm to use for pstree generation; r for Recursive, i for Iterative (default)''',
        require=False, validate=validators.Set("r","i"))

        def make_row(self, node, parent, root, lineage, depth, tree):
            # detail for a node is stored under tree[<its parent>][<node>]
            row = {
                "root": root,
                "parent": parent,
                "child": node,
                "depth": depth,
                "lineage": list(lineage),
                "lineage_path": " -> ".join(lineage),
            }
            if self.detail:
                row["detail"] = tree[parent][node] if parent != "" else ""
            return row

        def walk_recursive(self, node, parent, root, lineage, depth, tree, rows):
            rows.append(self.make_row(node, parent, root, lineage, depth, tree))
            # Check to see if current process had any children
            if node not in tree:
                return
            # For every child process recursively build tree
            for child in tree[node].keys():
                self.walk_recursive(child, node, root, lineage + [child], depth + 1, tree, rows)

        def walk_iterative(self, root, tree):
            stack = collections.deque([root])
            preorder = [root]
            yield self.make_row(root, "", root, [root], 0, tree)
            while len(stack) > 0:
                flag = False
                top = stack[-1]
                if top not in tree:
                    stack.pop()
                    continue
                for child in tree[top].keys():
                    if child not in preorder:
                        flag = True
                        stack.append(child)
                        preorder.append(child)
                        lineage = list(stack)
                        yield self.make_row(child, top, root, lineage, len(lineage) - 1, tree)
                        break
                if not flag:
                    stack.pop()

        def transform(self, records):
                self.logger.debug('PSTreeCommand: %s', self)
                #initialize tree structure as dictionary of dictionaries (dict of dict to allow passing of details)
                tree=collections.defaultdict(lambda: collections.defaultdict(str))
                #initialize array to keep track of children processes
                children=[]
                method="i"
                if self.method:
                    method=self.method
                # For every event add parent as key in outer dict and child as key in nested dict
                for record in records:
                    # If detail exists for the event set as value for inner dict other wise set as empty
                    if self.detail:
                        tree[record[self.parent]][record[self.child]]=record[self.detail]
                    else:
                        tree[record[self.parent]][record[self.child]]=""
                    #Add child to array to be able find root of pstree - every process associated with an EventCode 1 will be in this array
                    children.append(record[self.child])

                for root in list(tree.keys()):
                    #For every parent check if in children array - only Parent Processes with no Process Creation event(Event Code 1) will match this criteria
                    if root in children:
                        continue
                    if method=="r":
                        rows=[]
                        #Recursively build tree for every root process
                        self.walk_recursive(root, "", root, [root], 0, tree, rows)
                        for row in rows:
                            yield row
                    else:
                        for row in self.walk_iterative(root, tree):
                            yield row

dispatch(PSTreeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
