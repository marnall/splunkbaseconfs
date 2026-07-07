import requests
import json
import time
import hashlib


def get_teams(headers):
    t = time.clock()
    req = requests.get(
        'https://api.victorops.com/api-public/v1/team', headers=headers)
    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print("waiting {} seconds".format(t + 60 - time.clock()))
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        # retry
        req = requests.get(
            'https://api.victorops.com/api-public/v1/team', headers=headers)
    if req.status_code == 200:
        return json.loads(req.text)
    # NON-RATE LIMIT FAILURE
    else:
        print("Failed to get usernames . . .")


def get_team_policies(teamSlug, headers):
    t = time.clock()
    url = "https://api.victorops.com/api-public/v1/team/" + teamSlug + "/policies"
    req = requests.get(url, headers=headers)
    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print("waiting {} seconds".format(t + 60 - time.clock()))
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        # retry
        req = requests.get(url, headers=headers)
    if req.status_code == 200:
        return json.loads(req.text)['policies']
    # NON-RATE LIMIT FAILURE
    else:
        print(
            "Cannot get team escalation policies for {}. Skipping . . . ".format(teamSlug))


def get_routing_keys(headers):
    t = time.clock()
    req = requests.get(
        'https://api.victorops.com/api-public/v1/org/routing-keys', headers=headers)
    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print("waiting {} seconds".format(t + 60 - time.clock()))
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        # retry
        req = requests.get(
            'https://api.victorops.com/api-public/v1/org/routing-keys', headers=headers)
    if req.status_code == 200:
        return json.loads(req.text)['routingKeys']
    # NON-RATE LIMIT FAILURE
    else:
        print("Failed to get routing keys . . .")


def get_team_members(team, headers):
    t = time.clock()
    url = 'https://api.victorops.com/api-public/v1/team/' + team + '/members'
    req = requests.get(url, headers=headers)
    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print("waiting {} seconds".format(t + 60 - time.clock()))
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        # retry
        req = requests.get(url, headers=headers)
    # return the members
    if req.status_code == 200:
        members = json.loads(req.text)['members']
        return members
    # NON-RATE LIMIT FAILURE
    else:
        print("Failed to get team members . . .")


organization_id = 'utd'

headers = {
    'Accept': "application/json",
    'X-VO-Api-Id': "<>",
    'X-VO-Api-Key': "<>"
}

org = {
    "Teams": [],
    "routingKeys": []
}

teams = get_teams(headers)
for t in teams:
    teamSlugTmp = t['slug']
    teamTmp = {
        'type': 'team',
        'org': organization_id,
        'info': t,
        'policies': get_team_policies(teamSlugTmp, headers),
        'members': get_team_members(teamSlugTmp, headers),
    }
    # cleanup
    teamTmp['info'].pop('_selfUrl')
    teamTmp['info'].pop('_membersUrl')
    teamTmp['info'].pop('_adminsUrl')
    teamTmp['info'].pop('_policiesUrl')
    teamTmp['info'].pop('isDefaultTeam')
    teamTmp['info'].pop('version')
    # count verified users
    verifiedMembers = 0
    for u in teamTmp['members']:
        if u['verified'] == True:
            verifiedMembers = verifiedMembers + 1
    teamTmp['info']['verifiedMembers'] = verifiedMembers
    org['Teams'].append(teamTmp)

org["routingKeys"] = get_routing_keys(headers)
for r in org['routingKeys']:
    r['type'] = 'routingKey'
    r['org'] = organization_id
    for t in r['targets']:
        t['teamSlug'] = t['_teamUrl'].replace('/api-public/v1/team/', '')
        t.pop('_teamUrl')
        for team in org['Teams']:
            if team['info']['slug'] == t['teamSlug']:
                t['teamName'] = team['info']['name']
                break

print("Teams Info")
for t in org['Teams']:
    print("Team Slug : {}".format(t['info']['slug']))
    print(json.dumps(t, indent=2))
    print("*******************")

print("--------------------------------")
print("Routing Info")
for t in org['routingKeys']:
    print(json.dumps(t, indent=2))
    print("Hash : {}".format(hashlib.md5(json.dumps(t).encode()).hexdigest()))
    print("*******************")
