#!/usr/bin/env python
"""
This script runs provides the Python for the mvdiff command.
"""

import os
import sys

splunkhome = os.environ["SPLUNK_HOME"]
sys.path.append(os.path.join(splunkhome, "etc", "apps", "TA-mvdiff", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option  # noqa: E402
import splunk.mining.dcutils as dcu  # noqa: E402

logger = dcu.getLogger()


@Configuration()
class mvdiffCommand(StreamingCommand):  # pylint: disable=invalid-name
    """Command for comparing two multivalue fields

    ##Syntax

    ... | mvdiff left=<field name> right=<field name>

    ##Description

    Outputs three fields: mv_left, mv_right, mv_intersection
        * mv_left: Values ONLY present in left MV field
        * mv_right: Values ONLY present in right MV field
        * mv_intersection: Values present in both MV fields

    """

    left = Option(
        doc="""**Syntax:** **left=***<field name>*
        **Description:** First MV field to inspect""",
        name="left",
        require=True,
    )

    right = Option(
        doc="""**Syntax:** **right=***<field name>*
        **Description:** Second MV field to inspect""",
        name="right",
        require=True,
    )

    def stream(self, records):  # pylint: disable=arguments-differ
        left_field = self.left
        right_field = self.right

        # Put your event transformation code here
        for record in records:
            if left_field not in record:
                raise ValueError("Missing field: %s" % left_field)
            if right_field not in record:
                raise ValueError("Missing field: %s" % right_field)
            left = record[left_field]
            right = record[right_field]
            if isinstance(left, str):
                left = [left]
            if isinstance(right, str):
                right = [right]

            record["mv_left"] = list(set(left) - set(right))
            record["mv_right"] = list(set(right) - set(left))
            record["mv_intersection"] = list(set(left) & set(right))
            yield record


dispatch(mvdiffCommand, sys.argv, sys.stdin, sys.stdout, __name__)
