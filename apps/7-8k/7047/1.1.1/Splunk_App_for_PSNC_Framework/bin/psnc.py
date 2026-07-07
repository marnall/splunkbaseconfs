import os
import sys

# prepend to system path the ../lib directory in order to ship modules with the app itself.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

# splunk libraries import 
import splunk.mining.dcutils as dcu
from splunk.clilib.cli_common import getConfKeyValue
from splunk.Intersplunk import getOrganizedResults

import logging
import argparse
import asyncio
import aiohttp
import requests
import time
import json
from stix2 import Filter, MemoryStore

# disable insecure HTTPS requests due to Verify=False setting
requests.packages.urllib3.disable_warnings()

psnc_map = {
    'initial-access': { 'id': 'ICP-C-1', 'category': 'initial-exploitation' },
    'execution':{'id':'ICP-C-2', 'category': 'execution'},
    'privilege-escalation':{ 'id': 'ICP-C-3', 'category': 'establish-persistence'},
    'persistence':{ 'id': 'ICP-C-4', 'category': 'establish-persistence'},
    'defense-evasion':{ 'id':'ICP-C-5', 'category': 'establish-persistence'},
    'evasion':{ 'id':'ICP-C-5', 'category': 'establish-persistence'},
    'command-and-control': {'id':'ICP-C-6', 'category': 'establish-persistence'},
    'discovery':{'id':'ICP-C-7', 'category': 'lateral-movement'},
    'credential-access':{'id':'ICP-C-8', 'category': 'lateral-movement'},
    'lateral-movement':{'id':'ICP-C-9', 'category': 'lateral-movement'},
    'collection':{ 'id':'ICP-C-10', 'category': 'action-on-objectives'},
    'exfiltration':{ 'id':'ICP-C-11', 'category': 'action-on-objectives'},
    'inhibit-response-function':{ 'id':'ICP-C-12', 'category': 'action-on-objectives'},
    'impair-process-control':{ 'id':'ICP-C-13', 'category': 'action-on-objectives'},
    'impact':{ 'id':'ICP-C-14', 'category': 'action-on-objectives'},
    'reconnaissance':{ 'id':'ICP-C-15', 'category': 'reconnaissance'},
    'resource-development':{ 'id':'ICP-C-15', 'category': 'reconnaissance'} #to use enterprise-attack
}

def get_data_from_branch(domain):
    """get the ATT&CK STIX data from MITRE/CTI. Domain should be 'enterprise-attack', 'mobile-attack' or 'ics-attack'. Branch should typically be master."""
    try:
        logger.info(f'msg="Fetching MITRE ATT&CK matrix: domain=\'{domain}\'"')
        stix_json = requests.get(f"https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/{domain}/{domain}.json", timeout=20).json()
        logger.info(f'msg="Done fetching MITRE ATT&CK matrix: domain=\'{domain}\'"')
    except Exception as e:
        logger.critical(f'msg="Failed fetching MITRE ATT&CK matrix for domain\'{domain}\', details=\'{e}\'"')

    return MemoryStore(stix_data=stix_json["objects"])

def get_tactic_techniques(thesrc, matrix):
    if matrix == 'enterprise-attack':
        return thesrc.query([
            Filter('type', '=', 'attack-pattern'),
            Filter('kill_chain_phases.kill_chain_name', '=', 'mitre-attack'), #mitre-ics-attack
        ])
    elif matrix == 'ics-attack':
                return thesrc.query([
            Filter('type', '=', 'attack-pattern'),
            Filter('kill_chain_phases.kill_chain_name', '=', 'mitre-ics-attack'),
        ])
    else:
         return None

def remove_revoked_deprecated(stix_objects):
    """Remove any revoked or deprecated objects from queries made to the data source"""
    return list(
        filter(
            lambda x: x.get("x_mitre_deprecated", False) is False and x.get("revoked", False) is False,
            stix_objects
        )
    )

# wraps gather implementing a semaphore in order to avoid killing Splunk Instance with too many requests to process.
async def gather_with_concurrency(n, *coros):
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro

    return await asyncio.gather(*(sem_coro(c) for c in coros),return_exceptions=True)

# Get saved searches using requests 
def get_saved_searches(base_url=None, session_key=None, disabled=None):
    if base_url is None or session_key is None:
        raise Exception(f"Either base_url or session_key were set to None: got base_url={base_url}, session_key={session_key}")
    try:
        with requests.Session() as s:
            s.headers={f'Authorization': f'Splunk {session_key}'}
            s.verify = False
            savedsearchedreq = s.get(url=f"{base_url}/services/configs/conf-savedsearches", params={'count':"-1"}, data={"output_mode": "json"}, timeout=20)
            if savedsearchedreq.status_code == 200:
                if disabled is not None:
                    savedsearch = [ x for x in savedsearchedreq.json()['entry'] if x['content']['disabled'] == disabled ]
                else:
                    savedsearch = savedsearchedreq.json()['entry']
                return savedsearch
            else:
                raise Exception("Failed fetching saved searches.")
    except Exception as e:
        logger.critical(f'"Failed fetching savedsearches from splunkd=\'{base_url}\', details=\'{e}\'"')

# mapping to PSNC framework    
async def map_psnc(session, savedsearch, annotations, removed=None, action='reset'):
    startTime = time.time()
    name = savedsearch['name']
    global counter
    async with  session.post(f"{savedsearch['id']}", data={"output_mode": "json","action.correlationsearch.annotations": json.dumps(annotations)}) as response:
        results = await response.json()
        executionTime = (time.time() - startTime)
        counter += 1
        if response.status == 200:
            new_ann = json.loads(results['entry'][0]['content']['action.correlationsearch.annotations'])
        else:
            logger.debug(f"counter={counter}, search={name}, status=error, psnc_ids={annotations['PSNC']}, action={action}, elapsed={executionTime:.2f}")
            return annotations
        
        if action == 'reset':
            if 'PSNC' in new_ann:
                raise Exception("ERROR: PSNC framework still available.")
            else:
                logger.debug(f"counter={counter}, search={name}, status=success, psnc_ids={removed}, action={action}, elapsed={executionTime:.2f}")
        elif action == 'map':
            if 'PSNC' not in new_ann:
                raise Exception("ERROR: PSNC framework has not been added.")
            else:
                logger.debug(f"counter={counter}, search={name}, status=success, psnc_ids={annotations['PSNC']}, action={action}, elapsed={executionTime:.2f}")
        else:
            raise Exception(f"Unsupported value for action: '{action}'")            
    return counter, annotations
    
# create tasks list to be executed concurrently
async def create_tasklist(base_url=None, session_key=None, action=None, disabled=None, mitre_to_psnc_id={}):
    if base_url is None or session_key is None or action is None:
        msg = f'msg="Either base_url, session_key or action were set to None: got base_url=\'{base_url}\', session_key=\'{session_key}\', action=\'{action}\'"'
        logger.error(msg)
        raise Exception(msg)
    
    tasks = []

    #session_timeout = aiohttp.ClientTimeout(total=3600)  
    logger.info(f'msg="Fetching savedsearches from splunkd=\'{base_url}\'.') 
    savedsearches = get_saved_searches(base_url=base_url, session_key=session_key, disabled=disabled)
    logger.info(f'msg="Done fetching len=\'{len(savedsearches)}\' savedsearches from splunkd=\'{base_url}\'"') 
    headers = {f'Authorization': f'Splunk {session_key}'}
    async with aiohttp.ClientSession(headers=headers, connector=aiohttp.TCPConnector(ssl=False)) as session:
        for savedsearch in savedsearches:
            annotations = savedsearch['content'].get('action.correlationsearch.annotations', None)
            # Check if the search has the MITRE ID annotation
            if annotations:
            # Existing annotations
                try:
                    existing_annotations = json.loads(annotations)
                except Exception as e:
                    logger.error(f'msg="Error on annotation=\'{annotations}\', for savedsearch={savedsearch["name"]}"')
                    continue
                if action == 'reset':
                    if 'PSNC' in existing_annotations:
                        removed = existing_annotations.pop('PSNC')
                        task = map_psnc(session, savedsearch, existing_annotations, removed=removed, action='reset')
                        tasks.append(task)
                if action =='map':
                    # Check if MITRE ID exists in the annotations
                    if existing_annotations.get('mitre_attack', None):
                        mitre_ids = existing_annotations["mitre_attack"]
                        update = False
                        # Check if any of the MITRE IDs exist in the mapping
                        for mitre_id in mitre_ids:
                            # Get the corresponding "psnc_id" from the mapping
                            psnc_ids = mitre_to_psnc_id.get(mitre_id, None)
                            if psnc_ids:
                                # we do have a PSNC mapping already 
                                psnc_map = existing_annotations.get('PSNC', None)
                                if psnc_map:
                                    # Rule is not mapped with the same psnc_id (adding it).
                                    # We do not remove the old one
                                    for psnc_id in psnc_ids:
                                        if psnc_id not in psnc_map:
                                            existing_annotations['PSNC'].append(psnc_id)
                                            update = True
                                        else:
                                            #mapping is already available
                                            pass
            
                                # no mapping was found. Map with the corresponding psnc_id
                                else:
                                    existing_annotations['PSNC'] = []
                                    existing_annotations['PSNC'].extend(psnc_ids)
                                    update = True
                        if update:
                            task = map_psnc(session, savedsearch, existing_annotations, removed=None, action='map')
                            tasks.append(task)

        logger.info(f'msg="Number of tasks to be processed asyncronously: task=\'{len(tasks)}\'"')
        
        _ = await gather_with_concurrency(8, *tasks)

def gen_mitre_to_psnc_id(matrices=None):
    if matrices is None:
        raise Exception("Matrix cannot be None.")

    mitre_to_psnc_id = {}
    
    for matrix in matrices:
        src = get_data_from_branch(matrix)
        tech_for_tach = get_tactic_techniques(src,matrix)
        tech_for_tach = remove_revoked_deprecated(tech_for_tach)
        for tech in tech_for_tach:
            technique = [ x['external_id'] for x in tech['external_references'] if x['source_name'] == 'mitre-attack' ][0]
            technique_name = tech['name']
            for tac in tech['kill_chain_phases']:
                tactic = tac['phase_name']
                psnc_id = psnc_map[tactic]['id']
                if  mitre_to_psnc_id.get(technique,None) is None:
                    mitre_to_psnc_id[technique] = []
                mitre_to_psnc_id[technique].append(psnc_id)
    return mitre_to_psnc_id

def main():
    # parsing command line arguments 
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix", help="matrix to downalod", nargs='?', choices=['ics','enterprise','all'], default='all')
    parser.add_argument("action", help="action to perform", nargs='?', choices=['map','reset'], default='map')
    parser.add_argument("rules", help="rules to map", nargs='?', choices=['enabled','disabled','all'], default='enabled')
    args = parser.parse_args()

    # configuraion parameters
    # validation is performed by ArgumentParser
    # matrices: which ATT&CK matrix to pull and map with PSNC framework. It could be just 'enterprise-attack' just 'ics-attack' or both.
    # reset: set to True if you want to remove mapping with PSNC 
    # domap set to True  if you want to map ATT&CK mapped rules to PSNC
    # disabled: set to False to map just enbaled rules, set to True to map just disabled rule, set to None to map all rules.

    if args.matrix == 'all':
        matrices = ['enterprise-attack','ics-attack']
    elif args.matrix ==  'ics':
        matrices = ['ics-attack']
    elif args.matrix == 'enterprise':
        matrices = ['enterprise-attack']

    action = args.action

    if args.rules == 'all':
        disabled = None
    elif args.rules ==  'enabled':
        disabled = False
    elif args.rules == 'disabled':
        disabled = True

    mitre_to_psnc_id = gen_mitre_to_psnc_id(matrices=matrices)
    
    overallStart = time.time()

    _, _, settings = getOrganizedResults()
    session_key = settings['sessionKey']
    base_host = getConfKeyValue('web','settings','mgmtHostPort')
    base_url = f'https://{base_host}'

    # real main code that kickoff async execution.
    asyncio.run(create_tasklist(base_url=base_url, session_key=session_key, action=action, disabled=disabled, mitre_to_psnc_id=mitre_to_psnc_id))

    overallExecutionTime = (time.time() - overallStart)
    if counter != 0:
        logger.info(f'msg="Processing done: action=\'{action}\' - time=\'{overallExecutionTime:.2f} s\', searches=\'{counter}\'. average=\'{overallExecutionTime/counter:.2f}s\'"')
    else:
        logger.info(f'msg="Processing done: action=\'{action}\' - time=\'{overallExecutionTime:.2f} s\', searches=\'{counter}\'. average=\'N/As\'"')

# Global variable, useful just to log how many rules we are processing. 
# It can be probably avoided, but it would require more coding.
counter = 0

if __name__ == '__main__':
    # getting default logger to log to index=_internal sourcetype=splunk_python
    logger = dcu.getLogger()
    logger.setLevel(logging.INFO)
    main()
