import requests
import json
import csv
import os
import sys
import hmac
import hashlib
import time
from urllib.parse import urlparse


def generate_signature(method, url, timestamp):
    """
    Genera la signature HMAC-SHA256 usando el algoritmo descifrado de Accredible
    """
    secret_key = "chtM@CyP_.7iF.kuQXBv"
    
    # Extraer ruta relativa de la URL completa
    parsed = urlparse(url)
    relative_path = parsed.path
    
    # Payload: "METHOD relative_path HTTP/1.1 timestamp"
    payload = f"{method} {relative_path} HTTP/1.1 {timestamp}"
    
    signature = hmac.new(
        secret_key.encode('utf-8'), 
        payload.encode('utf-8'), 
        hashlib.sha256
    ).hexdigest()
    
    return signature


def get_badges(user):
    try:
        url = 'https://api.accredible.com/v1/credential-net/users/{user}/user_wallet'.format(user=user.get('userid'))
        method = "GET"
        
        # Generar timestamp actual (Unix timestamp en segundos)
        timestamp = str(int(time.time()))
        
        # Generar signature con autenticación HMAC
        signature = generate_signature(method, url, timestamp)
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'es-419,es;q=0.9,es-ES;q=0.8,en;q=0.7',
            'Origin': 'https://www.credential.net',
            'Referer': 'https://www.credential.net/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'X-Signature': signature,
            'X-Timestamp': timestamp,
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'credentials' in data['data']:
                badgets = data['data']['credentials']
                for e in badgets:
                    e["user"] = user.get('user')
                    print(json.dumps(e))
            else:
                print(f'No credentials found for {user.get("userid")}', file=sys.stderr)
        else:
            print(f'Error for {user}: {response.status_code} - {response.text}', file=sys.stderr)
    except requests.RequestException as e:
        print(f'Error for {user}: {e}', file=sys.stderr)


if __name__ == "__main__":
    dir_script = os.path.dirname(os.path.abspath(__file__))
    dir_prev = os.path.abspath(os.path.join(dir_script, os.pardir))
    lookup = os.path.join(dir_prev, 'lookups', 'wallets.csv')
    with open(lookup, 'r') as f:
        csv.register_dialect('MyDialect', skipinitialspace=True, lineterminator='\n', strict=True)
        users = csv.DictReader(f, dialect='MyDialect')
        for user in users:
            if  user.get('platform').lower() == 'accredible':
                #print(dict(user))
                get_badges(user)