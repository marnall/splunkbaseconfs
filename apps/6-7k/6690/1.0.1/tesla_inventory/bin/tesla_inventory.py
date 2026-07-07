import os,sys,xml.dom.minidom, xml.sax.saxutils,json,logging
from requests import Session
from re import search
from time import sleep

logging.root
logging.root.setLevel(logging.INFO)

SCHEME = """<scheme>
    <title>Tesla Inventory</title>
    <description>Grab the Telsa Inventory for a specific model and region</description>
    <use_external_validation>false</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <endpoint>
        <args>
            <arg name="market">
                <title>Market</title>
                <description>AE,AT,AU,BE,CA,CH,CN,CZ,DE,DK,ES,EU,FI,FR,GB,GR,HK,HR,HU,IE,IL,IS,IT,JO,JP,KR,LU,MO,MX,NL,NO,NZ,PL,PR,PT,RO,SE,SG,SI,TH,TW,US,ZA</description>
                <data_type>string</data_type>
                <validation>validate(match('market', '^AE|AT|AU|BE|CA|CH|CN|CZ|DE|DK|ES|EU|FI|FR|GB|GR|HK|HR|HU|IE|IL|IS|IT|JO|JP|KR|LU|MO|MX|NL|NO|NZ|PL|PR|PT|RO|SE|SG|SI|TH|TW|US|ZA$'), 'Invalid market')</<validation>
                <required_on_create>true</required_on_create>
                <required_on_edit>false</required_on_edit>
            </arg>
            <arg name="model">
                <title>Model</title>
                <description>ms,m3,mx,my</description>
                <data_type>string</data_type>
                <validation>validate(match('model', '^m[s3xy]$'), 'Invalid model')</validation>
                <required_on_create>true</required_on_create>
                <required_on_edit>false</required_on_edit>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def validate_conf(config, key):
    if key not in config:
        raise Exception("Invalid configuration received from Splunk: key '%s' is missing." % key)

def get_config():
    config = {}
    try:
        # read everything from stdin
        config_str = sys.stdin.read()
        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    config["name"] = stanza_name
                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data

        #checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        #if checkpnt_node and checkpnt_node.firstChild and \
        #   checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
        #    config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

        validate_conf(config, "market")
        validate_conf(config, "model")
    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))
    return config

def run():
    config = get_config()
    model = config['model'].lower()
    market = config['market'].upper()
    count = 50

    print("<stream>")
    with Session() as session:
        offset = 0
        while True:
            query = json.dumps({"query":{"model":model,"condition":"new","market":market},"offset":offset,"count":count,"outsideOffset":0,"outsideSearch":False}, separators=(',', ':'))
            logging.debug(query)
            data = session.get('https://www.tesla.com/inventory/api/v1/inventory-results?query='+query).json()
            
            for car in data['results']:
                car.pop('FeesDetails', None)
                car.pop('OptionCodeData', None)
                car.pop('OptionCodePricing', None)
                car.pop('OptionCodeSpecs', None)
                car.pop('WarrantyData', None)
                raw = json.dumps(car, separators=(',', ':'))
                print(f"<event><source>{market}:{model}</source><data>{raw}</data></event>")
            
            if int(data['total_matches_found']) <= (offset + len(data['results'])):
                break
            offset += count
    print("</stream>")
        
# Script must implement these args: scheme, validate-arguments
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            print(SCHEME)
        elif sys.argv[1] == "--validate-arguments":
            pass
        else:
            pass
    else:
        run()

    sys.exit(0)