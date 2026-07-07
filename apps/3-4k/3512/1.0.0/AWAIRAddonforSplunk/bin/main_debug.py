import requests
import datetime
#Get current Time Minus 15 Minutes
time=datetime.datetime.now() - datetime.timedelta(minutes=15)
time=time.strftime('%Y-%m-%dT%H:%M:%S%Z')
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiNjkxNiJ9.Iijdoo8oORm7r3VOvFhaWYHhbDilS9GoZ05gtsLjtxQ"
headers = {
    "Authorization": "Bearer %s" % token,
}

#Make a request to get the most recent 15-min avg from AWAIR
info = requests.get('https://beta-api.awair.is/v1/users/self/devices', headers=headers, stream=True, verify=False)
response = requests.get('https://beta-api.awair.is/v1/devices/10823/events/15min-avg?limit=1&from='+str(time), headers=headers, verify=False)

events = response.json()
device = info.json()

def getDeviceinfo(access_tokern):
    for info in device["data"]:
        lines = str(info)
        print("Device ID: " + str(info["device_id"]))
        print("Location: " + str(info["location_name"]))
        print("Device Name: " + str(info["device_name"]))
        print("Longitude: " + str(info["longitude"]))
        print("Latitude: " + str(info["latitude"]))
        print("Room Type: " + str(info["room_type"]))
        print("Owner Type: " + str(info["owner_type"]))
        print("\n")

def get15minData(access_token):
    for data in events["data"]:
        lines = str(data)
        sensor = (data["sensor"])
        timestamp = (data["timestamp"])
        score = (data["score"])
        #print("Timestamp: " + str(timestamp))
        #print("Score: " + str(score))
        #print("Sensor Data")
        print(str(timestamp)[:-5] + " " + "score=" + str(score) + " " + "CO2=" + str(sensor["co2"]) + " " + "dust=" + str(sensor["dust"]) + " " + "temperature=" + str(sensor["temp"]) + " "  + "humidity="  + str(sensor["humid"]) + " " + "VOC=" + str(sensor["voc"]))
        #index = (data["index"])
        #print("Index Data")
        #print("CO2=" + str(index["co2"]) + " " + "dust=" + str(index["dust"]) + " " + "temperature=" + str(index["temp"]) + " " + "humidity=" + str(index["humid"]) + " " + "VOC=" + str(index["voc"]) + "\n")

getDeviceinfo(token)
get15minData(token)
