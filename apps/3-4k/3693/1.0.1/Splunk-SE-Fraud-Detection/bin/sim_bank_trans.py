import time, datetime, os, sys, random

filename = "bank_trans.log"
debug = False
#debug = True
appname = "Splunk-SE-Fraud-Detection"

# Check for arguments
for arg in sys.argv:
    if (arg == "--debug"):
        debug = True

    if (arg.isdigit()):
        filename = str.replace(filename, ".log", "_" + str(arg) + ".log")

# Kill file if it exists.
if(debug == False):
    if os.environ["SPLUNK_HOME"].find('\\') == -1:
        theFile = open(os.environ["SPLUNK_HOME"] +  os.path.abspath('/etc/apps/' + appname + '/bin/output/' + filename), 'w')
    else:
        theFile = open(os.environ["SPLUNK_HOME"] +  ('\\etc\\apps\\' + appname + '\\bin\\output\\' + filename), 'w')

# Define lib path
libPath = os.path.join(os.environ["SPLUNK_HOME"], 'etc','apps', appname, 'bin', 'data')

# List of External IP addresses
clientipAddresses = open(os.path.join(libPath, 'external_ips.txt')).readlines()

# List of a goodly number of user agents - we pick one at random when we "login"
useragents = open(os.path.join(libPath, 'user_agents.txt')).readlines()

# Neverending Loop
loop = 1

while loop :

    # Append to file
    if os.environ["SPLUNK_HOME"].find('\\') == -1:
        theFile = open(os.environ["SPLUNK_HOME"] +  os.path.abspath('/etc/apps/' + appname + '/bin/output/' + filename), 'a')
    else:
        theFile = open(os.environ["SPLUNK_HOME"] +  ('\\etc\\apps\\' + appname + '\\bin\\output\\' + filename), 'a')

    # Define Data
    #############

    currentTime = datetime.datetime.utcnow()
    baseUrl = "http://www.globalbank.com"

    # Client IP Addresses
    clientipAddress = clientipAddresses[random.randint(0,len(clientipAddresses)-1)].replace("\n","")

    # Product Ids
    productIds = ["FI29734207","FI29848723", "FI39824856", "FI23940921", "FI09128374", "FI27938430", "RP09238428","RP92384903", "RP91839483", "RP90294839", "RP48923481", "RP780293904", "RP16232934", "RP82739813", "RP19232343", "FI72638402","AV27384934", "AV82748372","FL17283834","KC91284827","KC25373947","KC82737452","FL47264839", "FL30293483", "FL82836473", "FL82647293", "FL53628324", "FL18337364"]
    productId = productIds[random.randint(0, len(productIds) - 1)]

    # Item Ids
    itemIds = ["EST-19","EST-18","EST-14","EST-6","EST-26","EST-17","EST-16","EST-15","EST-27","EST-7","EST-21","EST-11","EST-12","EST-13","EST-20","EST-1"]
    itemId = itemIds[random.randint(0, len(itemIds) - 1)]

    # Category Ids
    catIds = ["CHECKING","CHECKING","SAVINGS","CMA"]
    catId = catIds[random.randint(0, len(catIds) - 1)]

    # JSESSION Ids
    jsessionId = "SD" + str(random.randint(1, 10)) + "SL" + str(random.randint(1, 10)) + "FF" + str(random.randint(1, 10)) + "ADFF" + str(random.randint(1, 10))

    # Actions
    actions = ["fund_transfer", "fund_add_info", "fund_delete_info", "get_acct_info", "fund_change_info"]
    action = actions[random.randint(0, len(actions) - 1)]

    # Status
    statuses = ["success","success","success","success","success","success","success","success","success","success","success", "error", "error", "unknown","failed","failed"]
    status = statuses[random.randint(0, len(statuses) - 1)]

    # Method
    methods = ["INTERNET", "INTERNET", "INTERNET", "INTERNET", "MOBILE"]
    method = methods[random.randint(0, len(methods) - 1)]

    # Bytes Transferred
    bytesXferred = str(random.randint(200,4000))

    # Time Taken
    timeTaken =  str(random.randint(100,1000))

    uris = [
    "TR_ACTION=" + action + " TR_ITEM_ID=" + itemId + " TR_TARGET_ACCT=" + productId,
    "TR_TARGET_ACCT=" + productId,
    "TR_CAT_ID=" + catId,
    "TR_ACTION=" + action + " TR_ITEM_ID=" + itemId + " TR_TARGET_ACCT=" + productId,
    "TR_TARGET_ACCT=" + productId,
    "TR_CAT_ID=" + catId,
    "TR_ACTION=" + action + " TR_ITEM_ID=" + itemId + " TR_TARGET_ACCT=" + productId,
    "TR_TARGET_ACCT=" + productId,
    "TR_CAT_ID=" + catId,
    "TR_ITEM_ID=" + itemId
    ]
    uri = uris[random.randint(0, len(uris) - 1)] + " TR_SESSION_ID=" + jsessionId
    referralUri = baseUrl + " " + uris[random.randint(0, len(uris) - 1)]

    useragents = [
    "Mozilla_4_0 TR_DEV_TYPE=compatible TR_BROWSER_TYPE=MSIE_6_0 TR_OS_TYPE=Windows_NT_5_1 TR_OS_REV=SV1",
    "Opera_9_01 TR_DEV_TYPE=Windows_NT_5_1 TR_BROWSER_TYPE=U en",
    "Mozilla_5_0 TR_DEV_TYPE=Macintosh TR_BROWSER_TYPE=U Intel Mac OS X 10_6_3",
    "Mozilla_4_0 TR_DEV_TYPE=compatible TR_BROWSER_TYPE=MSIE_6_0 Windows NT 5.1",
    "Googlebot_2_1 TR_DEV_TYPE=SearchBot http://www.googlebot.com/bot.html",
    "Mozilla_4_0 TR_DEV_TYPE=compatible TR_BROWSER_TYPE=MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322",
    "Mozilla_5_0 TR_DEV_TYPE=Windows TR_BROWSER_TYPE=U Windows NT 5.1; en-GB; rv:1.8.1.6",
    "Opera_9_20 TR_DEV_TYPE=Windows_NT_6_0 TR_BROWSER_TYPE=U en"
    ]

    #loggedInUsers[user_to_login]['userAgent'] = user_agents[random.randint(0,len(user_agents)-1)].replace("\n","")
    useragent = useragents[random.randint(0, len(useragents) - 1)]

    # Random Millisecond
    randMs = random.randint(1, 100) + 100

    if(clientipAddress == "10.2.1.44" and status == "503"):
        continue

    line = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S:') + str(randMs) + " TR_IP_ADDRESS=" + clientipAddress + " TR_SVC=" + method + " TR_STATUS=" + status + " " + uri + " TR_AMOUNT=" + bytesXferred + " TR_CHANNEL=" + referralUri + " TR_ACCESS_TYPE=" + useragent + " TR_SESSION_TIME=" + timeTaken + "\n"
    #line = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S:') + str(randMs) + " TR_IP_ADDRESS=" + clientipAddress + " TR_SVC=" + method + " TR_STATUS=" + status + " " + uri + " TR_AMOUNT=" + bytesXferred + " TR_CHANNEL=" + referralUri + " TR_ACCESS_TYPE=" + useragent + " TR_SESSION_TIME=" + timeTaken + "\n"

    if(debug):
        print(line)
    else:
        theFile.write(line)

    time.sleep(random.randint(0, 2))

    # This ensures proper line breaking for solid tailing
    theFile.close()
