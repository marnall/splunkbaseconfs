#!/usr/bin/env python
# -*- coding: utf-8 -*-

#use the bigger python library
from exec_anaconda import exec_anaconda_or_die
exec_anaconda_or_die()
#use our local nltk data under the app
import os
import sys
os.environ["NLTK_DATA"] = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-NLTK','bin','nltk_data')

import nltk
from nltk.corpus import stopwords
stopwords.words('english')

print("sentence tokenize")
from nltk.tokenize import sent_tokenize
mytext = "Hello Adam, how are you? I hope everything is going well. Today is a good day, see you dude."
print(sent_tokenize(mytext))

print("tokenize and tag")
from nltk import word_tokenize, pos_tag, ne_chunk 
sentence = "Mark and John are working at Google." 
print ne_chunk(pos_tag(word_tokenize(sentence)))

print("word tokenize")
from nltk.tokenize import word_tokenize 
mytext = "Hello Mr. Adam, how are you? I hope everything is going well. Today is a good day, see you dude."
print(word_tokenize(mytext))

print("french sentence tokenize")
from nltk.tokenize import sent_tokenize
mytext = "Bonjour M. Adam, comment allez-vous? J'espère que tout va bien. Aujourd'hui est un bon jour."
print(sent_tokenize(mytext,"french"))

print("synonyms")
from nltk.corpus import wordnet 
syn = wordnet.synsets("pain") 
print(syn[0].definition()) 
print(syn[0].examples())

print("definitions")
from nltk.corpus import wordnet 
syn = wordnet.synsets("NLP") 
print(syn[0].definition()) 
syn = wordnet.synsets("Python") 
print(syn[0].definition())

print("synonyms part 2")
from nltk.corpus import wordnet 
synonyms = [] 
for syn in wordnet.synsets('Computer'): 
    for lemma in syn.lemmas(): 
        synonyms.append(lemma.name()) 
print(synonyms)

print("antonyms")
from nltk.corpus import wordnet
antonyms = [] 
for syn in wordnet.synsets("small"): 
    for l in syn.lemmas(): 
        if l.antonyms(): 
            antonyms.append(l.antonyms()[0].name()) 
print(antonyms)

print("stemmer languages available")
from nltk.stem import SnowballStemmer 
print(SnowballStemmer.languages)

print("lemma sample")
from nltk.stem import WordNetLemmatizer 
lemmatizer = WordNetLemmatizer() 
print(lemmatizer.lemmatize('increases'))

print("lemmer positon sample")
from nltk.stem import WordNetLemmatizer 
lemmatizer = WordNetLemmatizer() 
print(lemmatizer.lemmatize('playing', pos="v"))
#second one
from nltk.stem import WordNetLemmatizer 
lemmatizer = WordNetLemmatizer() 
print(lemmatizer.lemmatize('playing', pos="v")) 
print(lemmatizer.lemmatize('playing', pos="n")) 
print(lemmatizer.lemmatize('playing', pos="a")) 
print(lemmatizer.lemmatize('playing', pos="r"))
