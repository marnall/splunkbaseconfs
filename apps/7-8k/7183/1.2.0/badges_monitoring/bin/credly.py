import requests
import json
import csv
import os


def get_badges(user):
    try:
        url = 'https://www.credly.com/users/{user}/badges'.format(user=user.get('userid'))
        response = requests.get(url, headers={'Accept': 'application/json',})
        if response.status_code == 200:
            badgets = response.json().get('data')
            for e in badgets:
                e["user"] = user.get('user')
                print(json.dumps(e))
        else:
            print(f'Error for {user}: {response.status_code} - {response.text}')
    except requests.RequestException as e:
        print(f'Error for {user}: {e}')


if __name__ == "__main__":
    dir_script = os.path.dirname(os.path.abspath(__file__))
    dir_prev = os.path.abspath(os.path.join(dir_script, os.pardir))
    lookup = os.path.join(dir_prev, 'lookups', 'wallets.csv')
    with open(lookup, 'r') as f:
        csv.register_dialect('MyDialect', skipinitialspace=True, lineterminator='\n', strict=True)
        users = csv.DictReader(f, dialect='MyDialect')
        for user in users:
            if user.get('platform').lower() == 'credly':
                #print(dict(user))
                get_badges(user)