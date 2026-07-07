#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Dominique Vocat, 13.01.2017
# wrap nltk features

#need to cheat to use the python for scientific blabla
import os,sys
#we just all known possible paths :-) sorry.
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_linux_x86_64','bin','linux_x86_64','lib','python2.7'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_linux_x86_64','bin','linux_x86_64','lib','python2.7','site-packages'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_linux_x86_64','bin','linux_x86_64','lib','python2.7','lib-dynload'))

sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_linux_x86','bin','linux_x86','lib','python2.7'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_linux_x86','bin','linux_x86','lib','python2.7','site-packages'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_linux_x86','bin','linux_x86','lib','python2.7','lib-dynload'))

sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_darwin_x86_64','lib','python2.7'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_darwin_x86_64','lib','python2.7','site-packages'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_darwin_x86_64','lib','python2.7','lib','python2.7','lib-dynload'))

sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_windows_x86_64','bin','windows_x86_64','lib','python2.7'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_windows_x86_64','bin','windows_x86_64','lib','python2.7','site-packages'))
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','Splunk_SA_Scientific_Python_windows_x86_64','bin','windows_x86_64','lib','python2.7','lib-dynload'))

import site
site.main()
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

os.environ["NLTK_DATA"] = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-NLTK','bin','nltk_data')

#@Configuration(local=True)
@Configuration()
class nltk(StreamingCommand):
    try:
        input = Option(require=False, default='_raw')
        output = Option(require=False, default='output')
        action = Option(require=True, default='passthrough')
        position = Option(require=False, default='')

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        sys.stderr.write(str(e)+"\n"+str(stack))
        exit(0)
        
    def stream(self, records):
        for record in records:
            for fieldname in record.keys():
                if fieldname == self.input:
                    try:
                        print >> sys.stderr, "data we got passed to work on " + record[self.input] #just dump some generic infor blurb
                        if self.action == 'passthrough':
                            record[self.output] = record[self.input]# test scaffold
                        elif self.action == 'sentence_tokenize':
                            from nltk.tokenize import sent_tokenize
                            record['sentences'] = sent_tokenize(record[self.input])
                        elif self.action == 'tokenize_and_tag':
                            from nltk import word_tokenize, pos_tag, ne_chunk 
                            tmp = ne_chunk(pos_tag(word_tokenize(record[self.input])))
                            import treetojson
                            tmp2 = treetojson.get_json(data=tmp)
                            record['pos_tag'] = tmp2 #['SENTENCE']
                        elif self.action == 'word_tokenize':
                            from nltk.tokenize import word_tokenize 
                            record['words'] = word_tokenize(record[self.input])
                        elif self.action == 'definitions':
                            from nltk.corpus import wordnet
                            syn = wordnet.synsets(record[self.input])
                            record['definition'] = syn[0].definition()
                            record['examples'] = syn[0].examples()
                        elif self.action == 'synonyms':
                            from nltk.corpus import wordnet
                            synonyms = [] 
                            for syn in wordnet.synsets(record[self.input]): 
                                for lemma in syn.lemmas(): 
                                    synonyms.append(lemma.name()) 
                            record['synonyms'] = synonyms                        
                        elif self.action == 'antonyms':
                            from nltk.corpus import wordnet
                            antonyms = [] 
                            for syn in wordnet.synsets(record[self.input]): 
                                for lemma in syn.lemmas(): 
                                    if lemma.antonyms():
                                        antonyms.append(lemma.antonyms()[0].name()) 
                            record['antonyms'] = antonyms
                        elif self.action == 'lemma':
                            from nltk.stem import WordNetLemmatizer 
                            lemmatizer = WordNetLemmatizer() 
                            if self.position == '':
                                record['lemma'] = lemmatizer.lemmatize(record[self.input])
                            else:
                                record['lemma'] = lemmatizer.lemmatize(record[self.input], pos=self.position)
                        elif self.action == 'language_detect':
                            import langdetect
                            record["language"]=langdetect.detect(record[self.input])
                        elif self.action == 'sentiment_analysis':
                            from nltk.sentiment.vader import SentimentIntensityAnalyzer
                            from nltk import tokenize
                            lines_list = tokenize.sent_tokenize(record[self.input])
                            sid = SentimentIntensityAnalyzer()
                            ss = sid.polarity_scores(record[self.input]) #one sentence each... erm.
                            for k in sorted(ss):
                                record[k]=ss[k]
                    except Exception, e:
                        sys.stderr.write(str(e))
                        record["returnvalue"] = str(e)
            yield record
        
dispatch(nltk, sys.argv, sys.stdin, sys.stdout, __name__)
