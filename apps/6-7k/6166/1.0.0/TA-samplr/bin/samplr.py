
#!/usr/bin/env python

import sys
import random
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class samplr(StreamingCommand):

    perc = Option(
        doc='''
        **Syntax:** **perc=***50*
        **Description:** Speficy in percentage how much of the total events will be returned''',
        require=False, default="50")

    def stream(self, events):

        perc = (float(self.perc) / 100)

        for e in events:
            if random.random() < perc:
                e['rand'] = round(random.random(), 5)
                e['perc'] = perc
                yield e

dispatch(samplr, sys.argv, sys.stdin, sys.stdout, __name__)