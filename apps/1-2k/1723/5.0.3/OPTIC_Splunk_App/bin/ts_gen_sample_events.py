import os, time, csv, datetime
from random import randint
from logger import setup_logger
import util.splunk_access
import util.kvs_manager
import settings

logger = setup_logger('ts_gen_sample_events')
logger.debug('starting ts_gen_sample_events ...')
splunka = util.splunk_access.Splunk_access(logger)
kvsm = splunka.get_kvsm()
event_count = 10

event_fields = ['_time', 
          'file_name', 
          'http_refer',
          'http_user_agent',
          'user',
          'src',
          'action',
          'dest',
          'url',
          'file_hash',
          'src_port',
          'recipient',
          'src_user'
          ]

iocs_ip = kvsm.get_kvs('ts_iocs_ip')
iocs_domain = kvsm.get_kvs('ts_iocs_domain')
iocs_email = kvsm.get_kvs('ts_iocs_email')
iocs_url = kvsm.get_kvs('ts_iocs_url')
iocs_md5 =  kvsm.get_kvs('ts_iocs_md5')

logger.debug('iocs_ip: %s: ' % len(iocs_ip))   
logger.debug('iocs_domain: %s: ' % len(iocs_domain))   
logger.debug('iocs_email: %s: ' % len(iocs_email))   
logger.debug('iocs_url: %s: ' % len(iocs_url))   
logger.debug('iocs_md5: %s: ' % len(iocs_md5))   

def gen_events(ioc_type, events):
    for i in range(0, event_count):
        event = {}
        time.sleep(0.05)
        time_value = datetime.datetime.fromtimestamp(time.time())
        event['_time'] = time_value
        if ioc_type == 'ip':
            event['src'] = iocs_ip[randint(0, len(iocs_ip)) - 1]['lookup_key_value']
            event['dest'] = iocs_ip[randint(0, len(iocs_ip)) - 1]['lookup_key_value']
        elif ioc_type == 'domain':
            event['src'] = iocs_domain[randint(0, len(iocs_domain)) - 1]['lookup_key_value']
            event['dest'] = iocs_domain[randint(0, len(iocs_domain)) - 1]['lookup_key_value']
        elif ioc_type == 'email':
            event['src_user'] = iocs_email[randint(0, len(iocs_email)) - 1]['lookup_key_value']
            event['recipient'] = iocs_email[randint(0, len(iocs_email)) - 1]['lookup_key_value']
        elif ioc_type == 'url':
            event['url'] = iocs_email[randint(0, len(iocs_email)) - 1]['lookup_key_value']          
        elif ioc_type == 'md5':
            event['file_hash'] = iocs_md5[randint(0, len(iocs_md5)) - 1]['lookup_key_value']
            if iocs_ip:
                event['dest'] = iocs_ip[randint(0, len(iocs_ip)) - 1]['lookup_key_value']   
            elif iocs_domain:
                event['dest'] = iocs_domain[randint(0, len(iocs_domain)) - 1]['lookup_key_value']          
        events.append(event)

def run():
    events = []
    if iocs_ip:
        gen_events('ip', events)
    if iocs_domain:
        gen_events('domain', events)        
    if iocs_email:
        gen_events('email', events)        
    if iocs_url:
        gen_events('url', events)        
    if iocs_md5:
        gen_events('md5', events)        
    
    sample_file = os.path.join(settings.get_samples_dir(), 'ts_sample_events.csv')
    print('Generating sample event data...')
    with open(sample_file, 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(event_fields)
        for event in events:
            event_row = [event.get(f) for f in event_fields]
            writer.writerow(event_row) 
    print('%s events written to the file: %s' % (len(events), sample_file))   
    logger.debug('Events saved to file %s: ' % sample_file)          

if __name__ == "__main__":
    try:
        run()
    except BaseException as e:
        print('Error: %s' % e)
        logger.exception(e)
        raise