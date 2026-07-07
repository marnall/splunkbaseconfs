import requests
import json
import time
import sys


def get_user_contact_methods(username, headers):
    t = time.clock()
    get_user_contact_methods_url = 'https://api.victorops.com/api-public/v1/user/' + \
        username + '/contact-methods'
    req = requests.get(get_user_contact_methods_url, headers=headers)

    # RATE LIMIT - wait,

    # retry
    while req.status_code == 403:
        # wait until minute has passed
        print("Waiting {} seconds".format(t + 60 - time.clock()))
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        print("Retrying getting user contact methods . . .")
        # retry
        req = requests.get(get_user_contact_methods_url, headers=headers)

    if req.status_code == 200:
        response = json.loads(req.text)
        phones = response['phones']['contactMethods']
        emails = response['emails']['contactMethods']
        push = response['devices']['contactMethods']
        contactMethods = []

        """create custom contactMethods return object so there isn't so much fluff
        # using the form:
        # [
        #     {
        #         "label":"label",
        #         "type":"type",
        #         "value":"value"
        #     },
        #     more of ^ as necessary.
        # ]"""


        # iterate through contactMethod types list
        for x in [phones, emails, push]:
            # for each method of contact type x
            # print x
            for y in x:
                # is it a mobile device, if yes, special
                if "deviceType" in y:
                    contactMethods.append({
                        "label": y['label'],
                        "type": y['deviceType']
                    }
                    )
                # otherwise it is a phone/email which have the same response
                else:
                    contactMethods.append({
                        "label": y['label'],
                        "type": y['contactType'],
                        "value": y['value']
                    }
                    )
                # print the most recent contact method
                # print contactMethods[-1]

        # print username + ':' + phone + email + push
        # print "\n\n CONTACT METHODS\n=========================\n" + str(contactMethods) + "\n\n"
        # [response['phones'].pop(, response['emails'], response['devices']]
        return contactMethods

    else:
        print(
            "Cannot get contact-methods for {}. Exiting . . . ".format(username))
        sys.exit()


def get_user_paging_policy(username, headers):
    t = time.clock()
    get_user_paging_policy_url = 'https://api.victorops.com/api-public/v1/profile/' + \
        username + '/policies'

    req = requests.get(get_user_paging_policy_url, headers=headers)

    # RATE LIMITS
    while req.status_code == 403:
        # wait until minute has passed
        print("Waiting {} seconds".format(t + 60 - time.clock()))
        time.sleep(t + 60 - time.clock())
        # reset timer to current time
        t = time.clock()
        print("Retrying getting user paging policies . . .")
        # retry
        req = requests.get(get_user_paging_policy_url, headers=headers)

    if req.status_code == 200:
        return json.loads(req.text)['steps']
    # NON-RATE LIMIT FAILURE
    else:
        print(
            "Cannot get paging-policy for {}. Skipping . . .".format(username))


url = "https://api.victorops.com/api-public/v1/user"

headers = {
    'Accept': "application/json",
    'X-VO-Api-Id': "<>",
    'X-VO-Api-Key': "<>"
}

response = requests.request("GET", url, headers=headers)

users = json.loads(response.text)

for u in users['users'][0]:
    userTmp = {
        'type': 'user',
        'info': u,
        'org': 'Splunk',
        'contactMethods': get_user_contact_methods(u['username'], headers),
        'pagingPolicy': get_user_paging_policy(u['username'], headers)
    }
    userTmp['info'].pop('_selfUrl')
    print(userTmp)
    print("****")
