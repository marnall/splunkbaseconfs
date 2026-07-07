#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals
from distutils.command.config import config
import os,sys
import urllib.request
from concurrent import futures
import json
import configparser

DEEPL_ENDPOINT_TRANSLATE = "https://api-free.deepl.com/v2/translate"
MAX_WORKERS = None

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA-deepl', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class TranslateCommand(StreamingCommand):

    outfield= Option(
        doc='''
        **Syntax:** **outfield=***<fieldname>*
        **Description:** Name of the field that will hold the translated text''',
        require = False,
        default = 'translated',
        validate = validators.Fieldname()
    )

    t_lang = Option(
        doc='''
        **Syntax:** **t_lang=***<target language>*
        **Description:** Language of the text to be translated. ''',
        require = False,
        default='JA',
        validate = validators.Fieldname()
    )

    def stream(self, records):

        try:
            target_field = self.fieldnames[0]
        except (IndexError, UnboundLocalError) as e:
            self.logger.exception(e)
            raise Exception("input field is not specified")
        
        try:
            config = configparser.ConfigParser()
            config.read(os.path.join(os.getcwd(), '../default/deepl.conf'))
            config.read(os.path.join(os.getcwd(), '../local/deepl.conf'))

            if config.has_section('api'):
                if config.has_option('api', 'key'):
                    if len(config.get('api', 'key')) > 0:
                        api_key = config.get('api', 'key')
                if config.has_option('api', 'domain'):
                    if len(config.get('api','domain')) > 0:
                        deepl_endpoint_translate = 'https://' + config.get('api', 'domain') + '/v2/translate'
                    else:
                        deepl_endpoint_translate = DEEPL_ENDPOINT_TRANSLATE

        except:
            raise Exception("Error reading configuration. Please check your local deepl.conf file.")

        future_list = []
        with futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for record in records:
                future = executor.submit(translate_record, record, target_field, self.outfield, api_key=api_key, t_lang=self.t_lang)
                future_list.append(future)
                yield record
            _ = futures.as_completed(fs=future_list)
            

def translate_record(record, target_field, out_field, api_key='', s_lang='', t_lang='JA'):

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; utf-8'
    }

    params = {
        'auth_key': api_key,
        'text': record[target_field],
        'target_lang': t_lang
    }

    if s_lang != '':
        params['source_lang'] = s_lang

    req = urllib.request.Request(
        DEEPL_ENDPOINT_TRANSLATE,
        method='POST',
        data=urllib.parse.urlencode(params).encode('utf-8'),
        headers=headers
    )

    try:
        with urllib.request.urlopen(req) as res:
            res_json = json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(e)
    
    record[out_field] = res_json["translations"][0]["text"]
    return record


dispatch(TranslateCommand, sys.argv, sys.stdin, sys.stdout, __name__)