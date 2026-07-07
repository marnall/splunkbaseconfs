import os, sys
import traceback
import collections
import math
import splunk.appserver.mrsparkle.lib.util as util

import joblib
import sklearn
import numpy as np
pwd_tldextract = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin', 'ta_skylight_for_splunk', 'aob_py3', 'tldextract')
sys.path.append(pwd_tldextract)
import tldextract

# Okay for this model we need the 2LD and nothing else
def domain_extract(url):
    ext = tldextract.extract(url)
    return ext.domain

def subdomain_extract(url):
    ext = tldextract.extract(url).subdomain.split(".")
    if ext[0] == "www":
        del ext[0]
    if len(ext) == 0 or ext[0] == "":
        return True
    return False

# Entropy calc (this must match model_gen)
def entropy(s):
    p, lns = collections.Counter(s), float(len(s))
    return -sum( count/lns * math.log(count/lns, 2) for count in list(p.values()))

# Evaluate the incoming domain
def evaluate_url(model, url):
    domain = domain_extract(url)
    alexa_match = model['alexa_counts'] * model['alexa_vc'].transform([url]).T
    dict_match = model['dict_counts'] * model['dict_vc'].transform([url]).T

    # Assemble feature matrix (for just one domain)
    X = [[len(domain), entropy(domain), alexa_match, dict_match]]
    y_pred = model['clf'].predict(X)[0]
    return y_pred

def load_model_from_disk(name, model_dir=os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin', 'models')):
    # Model directory is relative to this file
    model_path = os.path.join(model_dir, name+'.model')

    # Put a try/except around the model load in case it fails
    try:
        model = joblib.load(model_path)
    except Exception as error:
        print("cant load model ", model_path, error)

    return model

def ml_predict(query):
    try:
        clf = load_model_from_disk('dga_model_random_forest')
        alexa_vc = load_model_from_disk('dga_model_alexa_vectorizor')
        alexa_counts = load_model_from_disk('dga_model_alexa_counts')
        dict_vc = load_model_from_disk('dga_model_dict_vectorizor')
        dict_counts = load_model_from_disk('dga_model_dict_counts')
        model = {'clf':clf, 'alexa_vc':alexa_vc, 'alexa_counts':alexa_counts,
                'dict_vc':dict_vc, 'dict_counts':dict_counts}

        print(evaluate_url(model, query)) #www.domain.com
        sys.exit(1)
    except Exception as error:
        traceback.print_exc()
        sys.exit(1)

query = sys.argv[1]
if subdomain_extract(query):
    ml_predict(query)
