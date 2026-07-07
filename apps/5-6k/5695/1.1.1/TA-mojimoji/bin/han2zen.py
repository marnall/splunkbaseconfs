#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals
import os,sys

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA-mojimoji', 'lib'))
import mojimoji
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class Han2ZenCommand(StreamingCommand):

    exclude = Option(
        doc='''
        **Syntax:** **exclude=***[kana|digit|ascii]*
        **Description:** Which type of charactor is excuded from conversion''',
        require=False,
        validate=validators.Fieldname())

    outfield= Option(
        doc='''
        **Syntax:** **outfield=***<fieldname>*
        **Description:** Name of the field that will hold the converted string''',
        require=False,
        default='zenkaku',
        validate=validators.Fieldname())

    def stream(self, records):
        options = {'kana': True, 'digit': True, 'ascii': True}

        try:
            target_field = self.fieldnames[0]
        except (IndexError, UnboundLocalError) as e:
            self.logger.exception(e)
            raise Exception("input field is not specified")

        for record in records:
            if self.exclude != None:
                options[self.exclude] = False
                try:
                    record[self.outfield]= mojimoji.han_to_zen(record[target_field], kana=options['kana'], digit=options['digit'], ascii=options['ascii'])
                except KeyError:
                    continue
            else:
                try:
                    record[self.outfield]= mojimoji.han_to_zen(record[target_field]) 
                except KeyError:
                    continue

            yield record

dispatch(Han2ZenCommand, sys.argv, sys.stdin, sys.stdout, __name__)

