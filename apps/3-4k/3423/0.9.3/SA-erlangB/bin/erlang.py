import sys
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration(local=True)
class ErlangCommand(StreamingCommand):

    blocking_factor = Option(require=False, default=0.0001,doc='''
    **Syntax:** **blocking_factor=***<blocking_factor>*
        **Description:** define blocking factor to calculate number of lines needed''')
    field = Option(require=True, validate=validators.Fieldname(),doc='''
    **Syntax:** **field=***<field>*
        **Description:** define column which contain current usage''')
    result = Option(require=False, validate=validators.Fieldname(),default="trunks",doc='''
    **Syntax:** **result=***<result>*
        **Description:** define column name of result column''')

    def stream(self, events):
       trunks = 0
       res = None
       for event in events:
          trunks = self.erlangb(float(event[self.field]), float(self.blocking_factor))
          event[self.result] = trunks
          yield event

    def erlangb(self, usage, blocking):
        trunks = 0
        bounce_rate = 1
        if usage <= 0:
            return 0
        while bounce_rate > blocking:
            trunks += 1
            bounce_rate = self.elf(trunks,usage)
        return trunks

    def elf(self, n, a):
        b = 1
        i = 0
        a = float(a)
        while i <= n:
            b = b*a/(i+b*a)
            i += 1
        return b

dispatch(ErlangCommand, sys.argv, sys.stdin, sys.stdout, __name__)
